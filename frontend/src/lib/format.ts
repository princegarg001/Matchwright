import type { Band, MatchKind } from "./types";

export const BANDS: { band: Band; from: number; to: number; label: string }[] = [
  { band: "weak", from: 0, to: 40, label: "Weak fit" },
  { band: "partial", from: 40, to: 60, label: "Partial fit" },
  { band: "good", from: 60, to: 80, label: "Good fit" },
  { band: "strong", from: 80, to: 101, label: "Strong fit" },
];

export const bandLabel = (b: Band | null) => BANDS.find((x) => x.band === b)?.label ?? "Not scored";

export const KIND: Record<MatchKind, { label: string; text: string; soft: string; stroke: string; dash?: string }> = {
  exact: { label: "Exact match", text: "text-exact", soft: "bg-exact-soft", stroke: "var(--color-exact)" },
  related: { label: "Related skill", text: "text-related", soft: "bg-related-soft", stroke: "var(--color-related)", dash: "6 5" },
  semantic: { label: "Similar meaning", text: "text-semantic", soft: "bg-semantic-soft", stroke: "var(--color-semantic)", dash: "1.5 4" },
  missing: { label: "Not found", text: "text-missing", soft: "bg-missing-soft", stroke: "var(--color-missing)" },
};

export const SUB_SCORE_LABEL: Record<string, string> = {
  required: "Required skills",
  preferred: "Preferred skills",
  semantic: "Overall similarity",
  experience: "Experience",
  education: "Education",
};

export const TOOL_LABEL: Record<string, string> = {
  extract_skills: "Read skills",
  normalize_skills: "Matched skill names",
  score_match: "Calculated score",
  explain_match: "Wrote reasons",
};

export const pct = (x: number) => `${Math.round(x * 100)}%`;
export const seconds = (ms: number) => (ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);
