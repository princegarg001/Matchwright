"""Skill extraction: Phi-3 (JSON-schema constrained) per chunk, merged; keyword/SkillNER as cross-check & fallback."""
import logging
import re

from app.core.config import settings
from app.core.models import LLMExtraction, Profile, SkillEntry
from app.data.chunk import chunk_document
from app.llm.prompts import EXTRACT_SYSTEM, EXTRACT_USER
from app.llm.provider import LLMUnavailable, chat_json
from app.taxonomy.normalizer import get_normalizer

log = logging.getLogger(__name__)

YEARS = re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", re.I)
EDU = [("phd", r"\bph\.?d|doctorate"), ("master", r"\bmaster|\bm\.?s\.?\b|\bmba\b|m\.?tech"),
       ("bachelor", r"\bbachelor|\bb\.?s\.?\b|\bb\.?a\.?\b|b\.?tech|b\.?e\.?\b|degree"),
       ("diploma", r"\bdiploma|associate"), ("high_school", r"high school|ged\b")]


def aliases_of(norm, canon: str) -> list[str]:
    return [a for a, c in norm.alias_to_canon.items() if c == canon]


def guess_years(text: str) -> float | None:
    vals = [float(v) for v in YEARS.findall(text) if 0 < float(v) <= 45]
    return max(vals) if vals else None


def guess_education(text: str) -> str:
    low = text.lower()
    for level, rx in EDU:
        if re.search(rx, low):
            return level
    return "unknown"


def is_mandatory(text: str, names: list[str]) -> bool:
    """True only when 'must/mandatory/essential' precedes the skill in the same sentence (within 60 chars).
    Checking a wide evidence window instead flags neighbouring skills and causes false knockouts."""
    for n in names:
        pat = r"\b(must|mandatory|essential)\b[^.\n;]{0,60}?(?<![\w+#])" + re.escape(n.lower()) + r"(?![\w+#])"
        if re.search(pat, text.lower()):
            return True
    return False


def keyword_profile(text: str, doc_type: str) -> Profile:
    """No-LLM extraction used in offline mode, as fallback, and as the cross-check."""
    norm = get_normalizer()
    found = norm.keyword_scan(text)
    preferred_zone = _preferred_zone(text) if doc_type == "jd" else ""
    skills = {}
    for canon, ev in found.items():
        skills[canon] = SkillEntry(canonical=canon, raw=[canon], evidence=ev, sources=["keyword"],
                                   required=not (preferred_zone and canon in norm.keyword_scan(preferred_zone)),
                                   mandatory=doc_type == "jd" and is_mandatory(text, aliases_of(norm, canon)))
    if settings.use_skillner:
        _add_skillner(text, skills)
    return Profile(doc_type=doc_type, skills=skills, years_experience=guess_years(text),
                   education_level=guess_education(text), text=text, extraction_mode="keyword")


def _preferred_zone(text: str) -> str:
    m = re.search(r"(preferred|nice to have|bonus|pluses?)[\s\S]{0,800}", text, re.I)
    return m.group(0) if m else ""


def _add_skillner(text: str, skills: dict) -> None:
    try:
        from app.taxonomy.skillner_ext import skillner_skills
        for name in skillner_skills(text):
            key = name.lower()
            skills.setdefault(key, SkillEntry(canonical=key, raw=[name], sources=[]))
            skills[key].sources.append("skillner")
    except Exception as e:
        log.warning("SkillNER unavailable: %s", e)


def extract_profile(text: str, doc_type: str) -> Profile:
    """LLM extraction over the most useful chunks, merged; falls back to keywords if the LLM fails."""
    kw = keyword_profile(text, doc_type)
    if settings.offline_mode:
        return kw
    chunks = chunk_document("tmp", text, doc_type)[: settings.max_chunks_per_doc]
    kind = "resume" if doc_type == "resume" else "job description"
    merged: dict[str, SkillEntry] = {}
    soft, years, edu, sen, ok = set(), [], "unknown", "unknown", 0
    for ch in chunks:
        try:
            out = chat_json(EXTRACT_SYSTEM.format(doc_kind=kind),
                            EXTRACT_USER.format(section=ch["section"], text=ch["text"]), LLMExtraction)
        except LLMUnavailable as e:
            log.warning("chunk %s extraction failed: %s", ch["chunk_idx"], e)
            continue
        ok += 1
        for s in out.skills:
            key = s.name.lower().strip()
            if not key or len(key) > 60:
                continue
            req = s.required and ch["section"] != "preferred"
            if key in merged:
                merged[key].raw.append(s.name)
                merged[key].required = merged[key].required or req
            else:
                merged[key] = SkillEntry(canonical=key, raw=[s.name], evidence=s.evidence[:200], required=req,
                                         mandatory=doc_type == "jd" and is_mandatory(text, [s.name]),
                                         sources=["llm"])
        soft.update(x.lower() for x in out.soft_skills)
        if out.years_experience:
            years.append(out.years_experience)
        edu = out.education_level if out.education_level != "unknown" else edu
        sen = out.seniority if out.seniority != "unknown" else sen
    if ok == 0:
        return kw  # degraded mode, reported as extraction_mode="keyword"

    # Grounding check: drop LLM skills whose name never appears in the text (hallucinations).
    low = text.lower()
    merged = {k: v for k, v in merged.items() if k in low or any(r.lower() in low for r in v.raw)}
    # Add keyword hits the LLM missed, and record agreement.
    for k, v in kw.skills.items():
        merged.setdefault(k, v)
    llm_keys = {k for k, v in merged.items() if "llm" in v.sources}
    agreement = len(llm_keys & set(kw.skills)) / max(1, len(kw.skills)) if kw.skills else None
    return Profile(doc_type=doc_type, skills=merged, soft_skills=sorted(soft),
                   years_experience=max(years) if years else kw.years_experience,
                   education_level=edu if edu != "unknown" else kw.education_level, seniority=sen,
                   text=text, extraction_mode="llm", agreement=agreement)


def normalize_profile(p: Profile) -> Profile:
    """Canonicalise skill names and merge duplicates ('sklearn' + 'scikit-learn' -> one entry)."""
    if p.normalized:
        return p
    norm = get_normalizer()
    out: dict[str, SkillEntry] = {}
    for entry in p.skills.values():
        c = norm.canon(entry.canonical)
        if c in out:
            e = out[c]
            e.raw += entry.raw
            e.required = e.required or entry.required
            e.mandatory = e.mandatory or entry.mandatory
            e.sources = sorted(set(e.sources + entry.sources))
        else:
            out[c] = entry.model_copy(update={"canonical": c})
    return p.model_copy(update={"skills": out, "normalized": True})
