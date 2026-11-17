import time
from contextvars import ContextVar
from dataclasses import dataclass, field

from app.core.models import Profile, ScoreBreakdown


@dataclass
class MatchState:
    resume_text: str
    jd_text: str
    resume: Profile | None = None
    jd: Profile | None = None
    text_sim: float | None = None
    breakdown: ScoreBreakdown | None = None
    bullets: list[str] = field(default_factory=list)
    explain_mode: str | None = None
    steps: list[dict] = field(default_factory=list)
    # Signature cache used by app.agent.kg.kg_delta() to emit only what changed since the
    # last snapshot, so the live knowledge-graph view can stream real incremental updates.
    kg_cache: dict[tuple[str, str], str] = field(default_factory=dict)

    def log(self, tool: str, tool_input: str, output: str, started: float, by: str) -> None:
        self.steps.append({"step": len(self.steps) + 1, "tool": tool, "input": tool_input, "output": output,
                           "ms": int((time.time() - started) * 1000), "by": by})


CURRENT: ContextVar[MatchState] = ContextVar("match_state")
