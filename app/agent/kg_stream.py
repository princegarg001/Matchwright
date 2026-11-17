"""Streams the agent's internal knowledge graph as it is built, step by step.

This runs the exact same tool functions as the orchestrator (`app.agent.steps`) — it is a real
trace of real computation, not a scripted animation — but drives them directly instead of through
the ReAct text-agent, so each step's new nodes/edges can be yielded the instant that step finishes.
`/v1/match` (app.agent.executor) remains the graded agentic path; this is the visualisation path
behind the "View knowledge graph" button, and it writes to the same result store.
"""
import re
import time
import uuid
from collections.abc import Iterator

from app.agent.kg import build_full_graph, kg_delta
from app.agent.state import MatchState
from app.agent.steps import step_explain, step_extract, step_normalize, step_score
from app.core import store
from app.core.config import settings
from app.core.models import KGEdge, KGEvent, KGNode, MatchResult, RequirementOut

MIN_WORDS = 40
MIN_SKILLS = 2


def _non_english(text: str) -> bool:
    letters = re.findall(r"[^\W\d_]", text)
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) < 0.7


def _event(seq: int, step: str, message: str, nodes: list[KGNode], edges: list[KGEdge],
          ms: int = 0, by: str = "system", done: bool = False, result: MatchResult | None = None) -> KGEvent:
    return KGEvent(seq=seq, step=step, message=message, nodes=nodes, edges=edges,
                   ms=ms, by=by, done=done, result=result)


def _guard_result(match_id: str, reason: str, t0: float) -> MatchResult:
    return MatchResult(
        match_id=match_id, status="insufficient_information", score=None,
        message=f"I don't have enough information to score this match: {reason}.",
        hint="Paste the full resume and job description (text-based PDF/DOCX), including Skills or Requirements.",
        mode="guard", model=settings.llm_model, latency_ms=int((time.time() - t0) * 1000))


def stream_match(resume_text: str, jd_text: str) -> Iterator[KGEvent]:
    """Generator of KGEvent, one per agent step, each carrying only the nodes/edges new since the last one."""
    t0, match_id = time.time(), "m_" + uuid.uuid4().hex[:12]
    seq = 0

    for name, txt in (("resume", resume_text), ("job description", jd_text)):
        if len((txt or "").split()) < MIN_WORDS:
            res = _guard_result(match_id, f"the {name} has fewer than {MIN_WORDS} words", t0)
            yield _event(seq, "guard", res.message, [], [], done=True, result=res)
            return
        if _non_english(txt):
            res = _guard_result(match_id, f"the {name} does not appear to be in English", t0)
            yield _event(seq, "guard", res.message, [], [], done=True, result=res)
            return

    st = MatchState(resume_text=resume_text, jd_text=jd_text)
    yield _event(seq, "start", "Reading both documents…", [], [], by="system")

    try:
        # 1. extract_skills(resume)
        tstep = time.time()
        step_extract(st, "resume", "agent")
        nodes, edges = kg_delta(st)
        seq += 1
        msg = f"Resume: found {len(st.resume.skills)} skills"
        if st.resume.years_experience:
            msg += f", {st.resume.years_experience:g} yrs experience"
        yield _event(seq, "extract_skills", msg, nodes, edges, ms=int((time.time() - tstep) * 1000), by="agent")
        if len(st.resume.skills) < MIN_SKILLS:
            res = _guard_result(match_id, f"the resume contains fewer than {MIN_SKILLS} identifiable skills", t0)
            seq += 1
            yield _event(seq, "guard", res.message, [], [], by="system", done=True, result=res)
            return

        # 2. extract_skills(jd)
        tstep = time.time()
        step_extract(st, "jd", "agent")
        nodes, edges = kg_delta(st)
        seq += 1
        req = sum(1 for s in st.jd.skills.values() if s.required)
        yield _event(seq, "extract_skills", f"Job description: found {len(st.jd.skills)} skills ({req} required)",
                     nodes, edges, ms=int((time.time() - tstep) * 1000), by="agent")
        if len(st.jd.skills) < MIN_SKILLS:
            res = _guard_result(match_id, f"the job description lists fewer than {MIN_SKILLS} identifiable skills", t0)
            seq += 1
            yield _event(seq, "guard", res.message, [], [], by="system", done=True, result=res)
            return

        # 3. normalize_skills(both)
        tstep = time.time()
        step_normalize(st, "agent")
        nodes, edges = kg_delta(st)
        seq += 1
        msg = f"Matched skill names across both documents: resume {len(st.resume.skills)}, jd {len(st.jd.skills)}"
        yield _event(seq, "normalize_skills", msg, nodes, edges, ms=int((time.time() - tstep) * 1000), by="agent")

        # 4. score_match(run)
        tstep = time.time()
        step_score(st, "agent")
        nodes, edges = kg_delta(st)
        seq += 1
        b = st.breakdown
        msg = f"Score {b.score}/100 ({b.band} fit), required {b.required_matched}/{b.required_total}"
        yield _event(seq, "score_match", msg, nodes, edges, ms=int((time.time() - tstep) * 1000), by="agent")

        # 5. explain_match(run)
        tstep = time.time()
        step_explain(st, "agent")
        nodes, edges = kg_delta(st)
        seq += 1
        yield _event(seq, "explain_match", f"Wrote {len(st.bullets)} grounded justifications",
                     nodes, edges, ms=int((time.time() - tstep) * 1000), by="agent")

        evidence = {k: v.evidence[:160] for k, v in st.resume.skills.items()}
        requirements = [RequirementOut(**m.model_dump(), evidence=evidence.get(m.matched_with or "", ""))
                        for m in b.matches]
        result = MatchResult(
            match_id=match_id, score=b.score, band=b.band, confidence=b.confidence, sub_scores=b.sub_scores,
            matched_skills=b.matched_skills, missing_skills=b.missing_skills,
            transferable_skills=b.transferable_skills, requirements=requirements,
            justifications=st.bullets, mode="live_graph", explain_mode=st.explain_mode,
            model="offline" if settings.offline_mode else settings.llm_model,
            latency_ms=int((time.time() - t0) * 1000), trace=st.steps,
            knowledge_graph=build_full_graph(st),
        )
        store.save(match_id, resume_text, jd_text, result.model_dump())
        seq += 1
        yield _event(seq, "done", "Done", [], [], by="system", done=True, result=result)
    except Exception as e:  # keep the stream well-formed even on an unexpected failure
        res = MatchResult(match_id=match_id, status="insufficient_information",
                          message=f"Something went wrong while scoring this match ({type(e).__name__}).",
                          hint="Try again, or paste plain text instead of an upload.",
                          mode="error", model=settings.llm_model, latency_ms=int((time.time() - t0) * 1000))
        seq += 1
        yield _event(seq, "error", res.message, [], [], by="system", done=True, result=res)
