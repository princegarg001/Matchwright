"""Three justifications. LLM writes them from facts only; a validator rejects ungrounded bullets;
deterministic templates fill any gap, so the API always returns exactly 3 grounded bullets."""
import json
import re

from pydantic import BaseModel, Field

from app.core.models import ScoreBreakdown
from app.llm.prompts import EXPLAIN_SYSTEM
from app.llm.provider import LLMUnavailable, chat_json


class Explanation(BaseModel):
    bullets: list[str] = Field(min_length=3, max_length=3)


def _fmt(x: float | None) -> str:
    return "not stated" if x is None else f"{x:g}"


def facts(b: ScoreBreakdown) -> dict:
    return {
        "score": b.score, "band": b.band,
        "required_skills_matched_directly": f"{b.required_exact} of {b.required_total}",
        "required_skills_matched_via_related": b.required_matched - b.required_exact,
        "education_requirement_met": b.education_met,
        "matched_skills": b.matched_skills[:8], "missing_required_skills": b.missing_skills[:6],
        "transferable_skills": b.transferable_skills[:4],
        "candidate_years": _fmt(b.candidate_years), "required_years": _fmt(b.required_years),
        "knockout_cap_applied": b.knockout_applied, "knockout_skills": b.knockout_skills,
    }


def template_bullets(b: ScoreBreakdown) -> list[str]:
    top = ", ".join([m.jd_skill for m in b.matches if m.required and m.kind == "exact"][:3])
    related = b.required_matched - b.required_exact
    b1 = (f"Directly matches {b.required_exact} of {b.required_total} required skills"
          + (f" ({top})" if top else "")
          + (f", plus {related} through related skills." if related else "."))
    if b.candidate_years is not None and b.required_years:
        verdict = "meets" if b.candidate_years >= b.required_years else "falls short of"
        b2 = f"{_fmt(b.candidate_years)} years of experience {verdict} the {_fmt(b.required_years)}-year requirement."
    elif b.candidate_years is not None:
        b2 = f"{_fmt(b.candidate_years)} years of experience; the job states no minimum."
    else:
        b2 = "Years of experience could not be determined from the resume."
    b2 += " Education meets the requirement." if b.education_met else " Education is below the stated requirement."
    if b.knockout_applied:
        b3 = f"Missing must-have skill(s) {', '.join(b.knockout_skills[:3])}, so the score is capped at 60."
    elif b.missing_skills:
        b3 = f"Missing required skills: {', '.join(b.missing_skills[:3])}."
    else:
        rel: dict[str, list[str]] = {}
        for m in b.matches:
            if m.kind in ("related", "semantic") and m.matched_with:
                rel.setdefault(m.matched_with, []).append(m.jd_skill)
        phrase = "; ".join(f"{k} is related to {', '.join(v[:3])}" for k, v in list(rel.items())[:2])
        b3 = "No required skill is missing" + (f"; {phrase}." if phrase else ".")
    return [b1, b2, b3]


def grounded(bullet: str, f: dict) -> bool:
    """A bullet must mention a known skill or a number from the facts, and no digits that aren't in the facts."""
    low = bullet.lower()
    known = [s.lower() for s in f["matched_skills"] + f["missing_required_skills"]]
    known += [t.split(" -> ")[-1].lower() for t in f["transferable_skills"]]
    fact_text = json.dumps(f).lower()
    numbers = re.findall(r"\d+(?:\.\d+)?", low)
    mentions = any(k and k in low for k in known) or bool(numbers)
    return mentions and all(n in fact_text for n in numbers) and len(bullet.split()) <= 40


def explain(b: ScoreBreakdown, use_llm: bool = True) -> tuple[list[str], str]:
    tmpl = template_bullets(b)
    if not use_llm:
        return tmpl, "template"
    f = facts(b)
    try:
        out = chat_json(EXPLAIN_SYSTEM, "Facts:\n" + json.dumps(f, indent=1), Explanation)
    except LLMUnavailable:
        return tmpl, "template"
    final, replaced = [], 0
    for i, bullet in enumerate(out.bullets):
        bullet = bullet.strip().lstrip("-•* ").strip()
        if grounded(bullet, f):
            final.append(bullet)
        else:
            final.append(tmpl[i])
            replaced += 1
    return final, "llm" if replaced == 0 else f"llm+template({replaced})"
