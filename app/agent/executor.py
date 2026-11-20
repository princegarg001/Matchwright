"""run_match(): guard -> ReAct AgentExecutor -> fallback orchestrator -> MatchResult."""
import logging
import re
import time
import uuid
from functools import lru_cache

from app.agent.kg import build_full_graph
from app.agent.state import CURRENT, MatchState
from app.agent.steps import complete_missing_steps
from app.agent.tools import TOOLS
from app.core.config import settings
from app.core.models import MatchResult, RequirementOut
from app.llm.prompts import REACT_PROMPT

log = logging.getLogger(__name__)
MIN_WORDS = 40
MIN_SKILLS = 2


@lru_cache
def get_executor():
    from langchain_classic.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import PromptTemplate

    from app.llm.provider import get_agent_llm
    agent = create_react_agent(get_agent_llm(), TOOLS, PromptTemplate.from_template(REACT_PROMPT))
    return AgentExecutor(agent=agent, tools=TOOLS, max_iterations=8, early_stopping_method="force",
                         handle_parsing_errors=True, return_intermediate_steps=True, verbose=True)


@lru_cache
def _langfuse_client():
    """Registers the Langfuse client once with our own settings. langfuse.langchain.CallbackHandler
    itself takes no credentials — it looks up an already-registered client via get_client(), which
    falls back to reading LANGFUSE_* from os.environ if none was registered. Our .env is loaded by
    pydantic-settings into this Settings object, not into os.environ, so without this explicit,
    cached instantiation the handler would silently trace nothing."""
    from langfuse import Langfuse
    return Langfuse(public_key=settings.langfuse_public_key or None,
                    secret_key=settings.langfuse_secret_key or None,
                    host=settings.langfuse_host)


def _callbacks() -> list:
    if not settings.langfuse_enabled:
        return []
    try:
        from langfuse.langchain import CallbackHandler
        _langfuse_client()
        return [CallbackHandler(public_key=settings.langfuse_public_key or None)]
    except Exception as e:
        log.warning("langfuse disabled: %s", e)
        return []


def _insufficient(match_id: str, reason: str, t0: float, steps: list) -> MatchResult:
    return MatchResult(
        match_id=match_id, status="insufficient_information", score=None,
        message=f"I don't have enough information to score this match: {reason}.",
        hint="Paste the full resume and job description (text-based PDF/DOCX), including Skills or Requirements.",
        mode="guard", model=settings.llm_model, latency_ms=int((time.time() - t0) * 1000), trace=steps)


def _non_english(text: str) -> bool:
    letters = re.findall(r"[^\W\d_]", text)
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) < 0.7


def run_match(resume_text: str, jd_text: str, use_agent: bool | None = None,
              return_trace: bool = False) -> MatchResult:
    t0, match_id = time.time(), "m_" + uuid.uuid4().hex[:12]
    use_agent = settings.use_agent and not settings.offline_mode if use_agent is None else use_agent

    # --- input guard (before spending any LLM time) ---
    for name, txt in (("resume", resume_text), ("job description", jd_text)):
        if len((txt or "").split()) < MIN_WORDS:
            return _insufficient(match_id, f"the {name} has fewer than {MIN_WORDS} words", t0, [])
        if _non_english(txt):
            return _insufficient(match_id, f"the {name} does not appear to be in English", t0, [])

    st = MatchState(resume_text=resume_text, jd_text=jd_text)
    token = CURRENT.set(st)
    mode = "agent"
    try:
        if use_agent:
            try:
                out = get_executor().invoke({"input": "Match the resume to the job description."},
                                            config={"callbacks": _callbacks()})
                st.steps.append({"agent_intermediate_steps": len(out.get("intermediate_steps", []))})
            except Exception as e:
                log.warning("agent failed, falling back: %s", e)
                mode = "fallback_orchestrator"
        else:
            mode = "orchestrator"

        # post-extraction guard: stop before scoring garbage
        if st.resume is None:
            from app.agent.steps import step_extract
            step_extract(st, "resume", "fallback")
        if len(st.resume.skills) < MIN_SKILLS:
            return _insufficient(match_id, f"the resume contains fewer than {MIN_SKILLS} identifiable skills",
                                 t0, st.steps)
        if complete_missing_steps(st) and mode == "agent":
            mode = "agent+fallback"
        if st.jd and len(st.jd.skills) < MIN_SKILLS:
            return _insufficient(match_id, f"the job description lists fewer than {MIN_SKILLS} identifiable skills",
                                 t0, st.steps)

        b = st.breakdown
        if settings.offline_mode:
            mode = "offline"
        evidence = {k: v.evidence[:160] for k, v in st.resume.skills.items()}
        requirements = [RequirementOut(**m.model_dump(), evidence=evidence.get(m.matched_with or "", ""))
                        for m in b.matches]
        return MatchResult(
            match_id=match_id, score=b.score, band=b.band, confidence=b.confidence, sub_scores=b.sub_scores,
            matched_skills=b.matched_skills, missing_skills=b.missing_skills,
            transferable_skills=b.transferable_skills, requirements=requirements,
            justifications=st.bullets, mode=mode,
            explain_mode=st.explain_mode, model="offline" if settings.offline_mode else settings.llm_model,
            latency_ms=int((time.time() - t0) * 1000), trace=st.steps if return_trace else [],
            knowledge_graph=build_full_graph(st),
        )
    finally:
        CURRENT.reset(token)
