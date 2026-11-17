"""The four steps as plain functions. Used by the agent's tools AND by the fallback orchestrator."""
import time

from app.agent.state import MatchState
from app.core.config import settings
from app.taxonomy.embedder import get_embedder
from app.taxonomy.normalizer import get_normalizer
from app.tools.explain import explain
from app.tools.extract import extract_profile, normalize_profile
from app.tools.scoring import score_match


class StepOrderError(RuntimeError):
    pass


def step_extract(st: MatchState, target: str, by: str) -> str:
    t0 = time.time()
    doc_type = "jd" if target in ("jd", "job", "job description") else "resume"
    text = st.jd_text if doc_type == "jd" else st.resume_text
    p = extract_profile(text, doc_type)
    setattr(st, doc_type, p)
    req = sum(1 for s in p.skills.values() if s.required)
    yrs = "unknown" if p.years_experience is None else f"{p.years_experience:g}"
    out = (f"{doc_type} profile stored: {len(p.skills)} skills"
           + (f" ({req} required), {yrs} years required" if doc_type == "jd" else f", {yrs} years")
           + f", mode={p.extraction_mode}")
    st.log("extract_skills", doc_type, out, t0, by)
    return out


def step_normalize(st: MatchState, by: str) -> str:
    if st.resume is None or st.jd is None:
        missing = "resume" if st.resume is None else "jd"
        raise StepOrderError(f"Run extract_skills with input {missing} first.")
    t0 = time.time()
    st.resume, st.jd = normalize_profile(st.resume), normalize_profile(st.jd)
    emb = get_embedder()
    if emb:
        st.text_sim = emb.sim(st.resume.text, st.jd.text)
    out = f"normalized: resume {len(st.resume.skills)} skills, jd {len(st.jd.skills)} skills"
    st.log("normalize_skills", "both", out, t0, by)
    return out


def step_score(st: MatchState, by: str) -> str:
    if not (st.resume and st.jd and st.resume.normalized and st.jd.normalized):
        raise StepOrderError("Run normalize_skills with input both first.")
    t0 = time.time()
    emb = get_embedder()
    st.breakdown = score_match(st.resume, st.jd, get_normalizer(), sim_fn=emb.sim if emb else None,
                               text_sim=st.text_sim)
    b = st.breakdown
    out = f"score={b.score} band={b.band} required {b.required_matched}/{b.required_total}"
    st.log("score_match", "run", out, t0, by)
    return out


def step_explain(st: MatchState, by: str) -> str:
    if st.breakdown is None:
        raise StepOrderError("Run score_match with input run first.")
    t0 = time.time()
    st.bullets, st.explain_mode = explain(st.breakdown, use_llm=not settings.offline_mode)
    out = "3 justifications written"
    st.log("explain_match", "run", out, t0, by)
    return out


def complete_missing_steps(st: MatchState) -> bool:
    """Deterministic orchestrator. Returns True if it had to do anything."""
    did = False
    if st.resume is None:
        step_extract(st, "resume", "fallback"); did = True
    if st.jd is None:
        step_extract(st, "jd", "fallback"); did = True
    if not (st.resume.normalized and st.jd.normalized):
        step_normalize(st, "fallback"); did = True
    if st.breakdown is None:
        step_score(st, "fallback"); did = True
    if not st.bullets:
        step_explain(st, "fallback"); did = True
    return did
