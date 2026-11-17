"""Pydantic models shared by tools, agent and API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EduLevel = Literal["none", "high_school", "diploma", "bachelor", "master", "phd", "unknown"]
Seniority = Literal["intern", "junior", "mid", "senior", "lead", "unknown"]


# ---- what Phi-3 must return (kept small: small models follow small schemas better) ----
class ExtractedSkill(BaseModel):
    name: str = Field(description="skill, tool, technology, method or certification; 1-4 words")
    evidence: str = Field(description="short exact phrase copied from the text showing the skill")
    required: bool = Field(default=True, description="job description only: false if preferred/nice to have")


class LLMExtraction(BaseModel):
    skills: list[ExtractedSkill] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    years_experience: float | None = Field(default=None, description="years of experience stated or required")
    education_level: EduLevel = "unknown"
    seniority: Seniority = "unknown"


# ---- internal profile after merging chunks ----
class SkillEntry(BaseModel):
    canonical: str
    raw: list[str] = Field(default_factory=list)
    evidence: str = ""
    required: bool = True
    mandatory: bool = False
    sources: list[str] = Field(default_factory=list)  # llm | keyword | skillner


class Profile(BaseModel):
    doc_type: Literal["resume", "jd"]
    skills: dict[str, SkillEntry] = Field(default_factory=dict)
    soft_skills: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    education_level: EduLevel = "unknown"
    seniority: Seniority = "unknown"
    text: str = ""
    extraction_mode: Literal["llm", "keyword"] = "llm"
    agreement: float | None = None  # overlap between LLM and keyword/SkillNER extraction
    normalized: bool = False


class SkillMatch(BaseModel):
    jd_skill: str
    matched_with: str | None
    credit: float
    kind: Literal["exact", "related", "semantic", "missing"]
    required: bool
    mandatory: bool = False


class ScoreBreakdown(BaseModel):
    score: int
    band: Literal["strong", "good", "partial", "weak"]
    sub_scores: dict[str, float]
    weights: dict[str, float]
    matches: list[SkillMatch]
    matched_skills: list[str]
    missing_skills: list[str]
    transferable_skills: list[str]
    required_total: int
    required_matched: int
    required_exact: int
    education_met: bool
    knockout_applied: bool
    knockout_skills: list[str] = Field(default_factory=list)
    candidate_years: float | None
    required_years: float | None
    confidence: Literal["high", "medium", "low"]


class RequirementOut(SkillMatch):
    """One JD requirement joined to the resume evidence behind it (drives the UI's requirement ledger)."""
    evidence: str = ""


# ---- Knowledge graph (new): a structural view of everything the agent built internally ----
KGNodeKind = Literal[
    "resume_doc", "jd_doc", "resume_skill", "jd_skill", "canonical_skill",
    "soft_skill", "experience", "education", "score", "sub_score", "explanation",
]
KGEdgeKind = Literal[
    "contains", "normalizes_to", "exact", "related", "semantic", "missing",
    "supports", "explains", "requires",
]


class KGNode(BaseModel):
    id: str
    kind: KGNodeKind
    label: str
    detail: str = ""
    group: Literal["resume", "jd", "shared", "result"] = "shared"
    weight: float = 1.0


class KGEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: KGEdgeKind
    label: str = ""
    weight: float = 1.0


class KnowledgeGraph(BaseModel):
    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)


class KGEvent(BaseModel):
    """One incremental update to the knowledge graph, emitted while the agent runs."""
    seq: int
    step: str  # mirrors the agent tool name, or "guard" / "done"
    message: str
    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)
    ms: int = 0
    by: Literal["agent", "fallback", "system"] = "system"
    done: bool = False
    result: MatchResult | None = None


class MatchResult(BaseModel):
    match_id: str
    status: Literal["ok", "insufficient_information"] = "ok"
    score: int | None = None
    band: str | None = None
    confidence: str | None = None
    sub_scores: dict[str, float] = Field(default_factory=dict)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    requirements: list[RequirementOut] = Field(default_factory=list)
    justifications: list[str] = Field(default_factory=list)
    message: str | None = None
    hint: str | None = None
    mode: str = "agent"
    explain_mode: str | None = None
    model: str = ""
    latency_ms: int = 0
    trace: list[dict] = Field(default_factory=list)
    knowledge_graph: KnowledgeGraph | None = None


KGEvent.model_rebuild()
