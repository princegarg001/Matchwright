"""Deterministic match score. No LLM. Fully unit-tested.

Score = 100 * sum(w_k * S_k) / sum(w_k)  over k in {required, preferred, semantic, experience, education}
- semantic is dropped and weights renormalised when embeddings are unavailable
- experience and education are multiplied by a relevance gate (0.5 + 0.5 * S_required)
- a missing must-have skill caps the score at 60
"""
from collections.abc import Callable

from app.core.models import Profile, ScoreBreakdown, SkillMatch
from app.taxonomy.normalizer import Normalizer

DEFAULT_WEIGHTS = {"required": 0.45, "preferred": 0.15, "semantic": 0.15, "experience": 0.15, "education": 0.10}
CREDIT = {"exact": 1.0, "related": 0.7, "semantic": 0.5, "missing": 0.0}
SEMANTIC_SKILL_THRESHOLD = 0.80
KNOCKOUT_CAP = 60
EDU_RANK = {"none": 0, "high_school": 1, "diploma": 2, "bachelor": 3, "master": 4, "phd": 5}
SEN_RANK = {"intern": 0, "junior": 1, "mid": 2, "senior": 3, "lead": 4}

SimFn = Callable[[str, str], float]


def clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def band_for(score: int) -> str:
    return "strong" if score >= 80 else "good" if score >= 60 else "partial" if score >= 40 else "weak"


def best_match(jd_skill: str, resume_skills: set[str], norm: Normalizer, sim_fn: SimFn | None):
    if jd_skill in resume_skills:
        return jd_skill, "exact"
    related = [(s, r) for r in sorted(resume_skills) if (s := norm.related_strength(jd_skill, r)) is not None]
    if related:
        return min(related)[1], "related"  # closest relation wins: tensorflow beats statistics for pytorch
    if sim_fn and resume_skills:
        cand, s = max(((r, sim_fn(jd_skill, r)) for r in resume_skills), key=lambda t: t[1])
        if s >= SEMANTIC_SKILL_THRESHOLD:
            return cand, "semantic"
    return None, "missing"


def coverage(ms: list[SkillMatch]) -> float | None:
    return sum(m.credit for m in ms) / len(ms) if ms else None


def experience_score(resume: Profile, jd: Profile) -> float:
    if not jd.years_experience:
        s = 1.0
    elif resume.years_experience is None:
        s = 0.5
    else:
        s = clip(resume.years_experience / jd.years_experience)
    if resume.seniority != "unknown" and jd.seniority != "unknown":
        if SEN_RANK[jd.seniority] - SEN_RANK[resume.seniority] >= 2:
            s -= 0.2
    return clip(s)


def education_score(resume: Profile, jd: Profile) -> float:
    if jd.education_level in ("unknown", "none"):
        return 1.0
    if resume.education_level == "unknown":
        return 0.75
    gap = EDU_RANK[jd.education_level] - EDU_RANK[resume.education_level]
    return 1.0 if gap <= 0 else 0.5 if gap == 1 else 0.0


def confidence(resume: Profile, jd: Profile) -> str:
    if "keyword" in (resume.extraction_mode, jd.extraction_mode) or len(jd.skills) < 3:
        return "low"
    agree = [a for a in (resume.agreement, jd.agreement) if a is not None]
    return "high" if agree and min(agree) >= 0.7 else "medium"


def score_match(resume: Profile, jd: Profile, norm: Normalizer, sim_fn: SimFn | None = None,
                text_sim: float | None = None, weights: dict[str, float] | None = None) -> ScoreBreakdown:
    w = dict(weights or DEFAULT_WEIGHTS)
    rskills = set(resume.skills)
    matches: list[SkillMatch] = []
    for name, entry in sorted(jd.skills.items()):
        hit, kind = best_match(name, rskills, norm, sim_fn)
        matches.append(SkillMatch(jd_skill=name, matched_with=hit, credit=CREDIT[kind], kind=kind,
                                  required=entry.required, mandatory=entry.mandatory))
    req = [m for m in matches if m.required]
    pref = [m for m in matches if not m.required]

    s_req = coverage(req) if req else (coverage(pref) or 0.5)
    # Relevance gate: years and degrees in an unrelated field count at most half.
    # Without it, a chef with 6 years scores ~47 ("partial") against an ML job.
    relevance = 0.5 + 0.5 * s_req
    subs: dict[str, float] = {
        "required": s_req,
        "preferred": coverage(pref) if pref else s_req,
        "experience": experience_score(resume, jd) * relevance,
        "education": education_score(resume, jd) * relevance,
    }
    if text_sim is None:
        w.pop("semantic", None)
    else:
        subs["semantic"] = clip((text_sim - 0.3) / 0.6)
    total_w = sum(w[k] for k in subs)
    raw = 100 * sum(w[k] * subs[k] for k in subs) / total_w

    knockouts = [m.jd_skill for m in req if m.mandatory and m.kind == "missing"]
    if knockouts:
        raw = min(raw, KNOCKOUT_CAP)
    score = int(round(raw))
    return ScoreBreakdown(
        score=score, band=band_for(score), sub_scores={k: round(v, 3) for k, v in subs.items()},
        weights={k: round(w[k] / total_w, 3) for k in subs}, matches=matches,
        matched_skills=[m.jd_skill for m in matches if m.kind == "exact"],
        missing_skills=[m.jd_skill for m in req if m.kind == "missing"],
        transferable_skills=[f"{m.matched_with} -> {m.jd_skill}" for m in matches if m.kind in ("related", "semantic")],
        required_total=len(req), required_matched=sum(1 for m in req if m.kind != "missing"),
        required_exact=sum(1 for m in req if m.kind == "exact"),
        education_met=education_score(resume, jd) >= 1.0,
        knockout_applied=bool(knockouts), knockout_skills=knockouts,
        candidate_years=resume.years_experience, required_years=jd.years_experience,
        confidence=confidence(resume, jd),
    )
