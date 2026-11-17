"""LangChain tools. Single string input each, because text ReAct passes the Action Input as a string."""
from langchain_core.tools import tool

from app.agent.state import CURRENT
from app.agent.steps import StepOrderError, step_explain, step_extract, step_normalize, step_score


def _clean(x: str) -> str:
    return (x or "").strip().strip("'\"`").lower()


@tool
def extract_skills(target: str) -> str:
    """Extract skills, years of experience and education. Input must be exactly: resume  OR  jd"""
    t = _clean(target)
    if t not in ("resume", "jd", "job", "job description"):
        return "Invalid input. Use exactly: resume  or  jd"
    return step_extract(CURRENT.get(), t, "agent")


@tool
def normalize_skills(target: str) -> str:
    """Canonicalise skill names of both profiles. Input: both"""
    try:
        return step_normalize(CURRENT.get(), "agent")
    except StepOrderError as e:
        return str(e)


@tool
def score_match(target: str) -> str:
    """Compute the 0-100 match score from the normalized profiles. Input: run"""
    try:
        return step_score(CURRENT.get(), "agent")
    except StepOrderError as e:
        return str(e)


@tool
def explain_match(target: str) -> str:
    """Write exactly 3 justifications for the score. Input: run"""
    try:
        return step_explain(CURRENT.get(), "agent")
    except StepOrderError as e:
        return str(e)


TOOLS = [extract_skills, normalize_skills, score_match, explain_match]
