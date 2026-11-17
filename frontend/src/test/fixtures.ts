import type { KnowledgeGraph, MatchResult } from "../lib/types";

export const okGraph: KnowledgeGraph = {
  nodes: [
    { id: "doc:resume", kind: "resume_doc", label: "Resume", detail: "", group: "resume", weight: 1.7 },
    { id: "doc:jd", kind: "jd_doc", label: "Job description", detail: "", group: "jd", weight: 1.7 },
    { id: "skill:resume:python", kind: "resume_skill", label: "python", detail: "llm", group: "resume", weight: 1 },
    { id: "skill:jd:python", kind: "jd_skill", label: "python", detail: "required · must-have", group: "jd", weight: 1.3 },
    { id: "skill:jd:a/b testing", kind: "jd_skill", label: "a/b testing", detail: "required · not found in resume", group: "jd", weight: 1 },
    { id: "result:score", kind: "score", label: "74 / 100", detail: "good fit", group: "result", weight: 2.2 },
  ],
  edges: [
    { id: "e:contains:skill:resume:python", source: "doc:resume", target: "skill:resume:python", kind: "contains", label: "", weight: 1 },
    { id: "e:req:skill:jd:python", source: "doc:jd", target: "skill:jd:python", kind: "requires", label: "must-have", weight: 1 },
    { id: "e:match:python", source: "skill:resume:python", target: "skill:jd:python", kind: "exact", label: "100%", weight: 1 },
  ],
};

export const okResult: MatchResult = {
  match_id: "m_test123", status: "ok", score: 74, band: "good", confidence: "high",
  sub_scores: { required: 0.78, preferred: 0.4, experience: 1, education: 1 },
  matched_skills: ["python", "sql"], missing_skills: ["a/b testing"], transferable_skills: ["tensorflow -> pytorch"],
  requirements: [
    { jd_skill: "python", matched_with: "python", kind: "exact", credit: 1, required: true, mandatory: true, evidence: "ETL jobs in Python and SQL" },
    { jd_skill: "pytorch", matched_with: "tensorflow", kind: "related", credit: 0.7, required: true, mandatory: false, evidence: "models in TensorFlow" },
    { jd_skill: "a/b testing", matched_with: null, kind: "missing", credit: 0, required: true, mandatory: false, evidence: "" },
    { jd_skill: "docker", matched_with: "docker", kind: "exact", credit: 1, required: false, mandatory: false, evidence: "Docker" },
  ],
  justifications: ["Directly matches 2 of 3 required skills (python).", "5 years meets the 3-year requirement.", "Missing required skills: a/b testing."],
  message: null, hint: null, mode: "agent", explain_mode: "llm", model: "phi3:mini", latency_ms: 41200,
  trace: [
    { step: 1, tool: "extract_skills", input: "resume", output: "resume profile stored: 12 skills", ms: 15000, by: "agent" },
    { step: 2, tool: "score_match", input: "run", output: "score=74", ms: 2, by: "fallback" },
  ],
  knowledge_graph: okGraph,
};
