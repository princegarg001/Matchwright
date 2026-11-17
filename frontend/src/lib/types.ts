// Mirrors app/core/models.py (MatchResult, KnowledgeGraph, KGEvent). Regenerate with
// openapi-typescript if the API changes.
export type Band = "strong" | "good" | "partial" | "weak";
export type MatchKind = "exact" | "related" | "semantic" | "missing";

export interface Requirement {
  jd_skill: string;
  matched_with: string | null;
  kind: MatchKind;
  credit: number;
  required: boolean;
  mandatory: boolean;
  evidence: string;
}

export interface TraceStep {
  step?: number;
  tool?: string;
  input?: string;
  output?: string;
  ms?: number;
  by?: "agent" | "fallback";
  agent_intermediate_steps?: number;
}

// --- Knowledge graph: the agent's internal state, made visible ---
export type KGNodeKind =
  | "resume_doc" | "jd_doc" | "resume_skill" | "jd_skill" | "canonical_skill"
  | "soft_skill" | "experience" | "education" | "score" | "sub_score" | "explanation";

export type KGEdgeKind =
  | "contains" | "normalizes_to" | "exact" | "related" | "semantic" | "missing"
  | "supports" | "explains" | "requires";

export interface KGNode {
  id: string;
  kind: KGNodeKind;
  label: string;
  detail: string;
  group: "resume" | "jd" | "shared" | "result";
  weight: number;
}

export interface KGEdge {
  id: string;
  source: string;
  target: string;
  kind: KGEdgeKind;
  label: string;
  weight: number;
}

export interface KnowledgeGraph {
  nodes: KGNode[];
  edges: KGEdge[];
}

/** One line of the NDJSON stream from /v1/match/stream: one real agent step, as it happens. */
export interface KGEvent {
  seq: number;
  step: string;
  message: string;
  nodes: KGNode[];
  edges: KGEdge[];
  ms: number;
  by: "agent" | "fallback" | "system";
  done: boolean;
  result: MatchResult | null;
}

export interface MatchResult {
  match_id: string;
  status: "ok" | "insufficient_information";
  score: number | null;
  band: Band | null;
  confidence: "high" | "medium" | "low" | null;
  sub_scores: Record<string, number>;
  matched_skills: string[];
  missing_skills: string[];
  transferable_skills: string[];
  requirements: Requirement[];
  justifications: string[];
  message: string | null;
  hint: string | null;
  mode: string;
  explain_mode: string | null;
  model: string;
  latency_ms: number;
  trace: TraceStep[];
  knowledge_graph: KnowledgeGraph | null;
}

export interface Health {
  status: string;
  offline_mode: boolean;
  agent: boolean;
  llm: { provider: string; model: string | null; loaded: boolean; error?: string };
}

export interface LiveJob {
  source: string;
  job_id: string;
  title: string;
  company: string;
  url: string;
  text: string;
}

export interface RankedRow {
  id: string;
  score: number | null;
  band: Band | null;
  status: MatchResult["status"];
  match_id: string;
  justifications: string[];
}
