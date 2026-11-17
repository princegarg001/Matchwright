import { useMemo } from "react";
import { KIND } from "../lib/format";
import { graphHeight, layoutGraph, VIEW_W } from "../lib/kgLayout";
import type { KGEdge, KGEdgeKind, KGNode } from "../lib/types";

const NODE_FILL: Record<string, string> = {
  resume_doc: "var(--color-ink)",
  jd_doc: "var(--color-ink)",
  score: "var(--color-blueprint)",
  explanation: "var(--color-blueprint)",
  sub_score: "var(--color-blueprint-soft)",
  resume_skill: "var(--color-sheet)",
  jd_skill: "var(--color-sheet)",
  canonical_skill: "var(--color-sheet)",
  soft_skill: "var(--color-sheet)",
  experience: "var(--color-sheet)",
  education: "var(--color-sheet)",
};
const NODE_TEXT: Record<string, string> = {
  resume_doc: "var(--color-paper)", jd_doc: "var(--color-paper)",
  score: "var(--color-paper)", explanation: "var(--color-paper)",
};
const NODE_STROKE: Record<KGNode["group"], string> = {
  resume: "var(--color-blueprint)",
  jd: "var(--color-slate)",
  result: "var(--color-blueprint)",
  shared: "var(--color-slate)",
};
const BIG_KINDS = new Set(["resume_doc", "jd_doc", "score", "explanation"]);

const EDGE_STROKE: Record<KGEdgeKind, string> = {
  contains: "var(--color-rule)",
  requires: "var(--color-rule)",
  normalizes_to: "var(--color-slate)",
  supports: "var(--color-blueprint)",
  explains: "var(--color-blueprint)",
  exact: "var(--color-exact)",
  related: "var(--color-related)",
  semantic: "var(--color-semantic)",
  missing: "var(--color-missing)",
};
const EDGE_DASH: Partial<Record<KGEdgeKind, string>> = {
  related: "6 5",
  semantic: "1.5 4",
};

function radiusFor(n: KGNode): number {
  if (BIG_KINDS.has(n.kind)) return 15 + Math.min(n.weight, 2) * 2;
  return n.kind === "sub_score" ? 11 : 9;
}

function widthFor(label: string, r: number): number {
  return Math.max(r * 2 + 8, label.length * 6.4 + 20);
}

export function KnowledgeGraphView({ nodes, edges, caption }: { nodes: KGNode[]; edges: KGEdge[]; caption?: string }) {
  const height = useMemo(() => graphHeight(nodes), [nodes]);
  const positions = useMemo(() => layoutGraph(nodes, height), [nodes, height]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-md border border-dashed border-rule text-sm text-slate">
        The graph will appear here as soon as scoring starts.
      </div>
    );
  }

  return (
    <div>
      <svg viewBox={`0 0 ${VIEW_W} ${height}`} className="h-auto w-full" role="img" aria-hidden style={{ overflow: "visible" }}>
        <g>
          {edges.map((e) => {
            const a = positions[e.source];
            const b = positions[e.target];
            if (!a || !b) return null;
            return (
              <g key={e.id} className="kg-enter">
                <line
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={EDGE_STROKE[e.kind]}
                  strokeWidth={e.kind === "exact" || e.kind === "supports" ? 2 : 1.4}
                  strokeDasharray={EDGE_DASH[e.kind]}
                  opacity={e.kind === "contains" || e.kind === "requires" ? 0.45 : 0.85}
                />
                {e.label && ["exact", "related", "semantic"].includes(e.kind) && (
                  <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 4} textAnchor="middle" fontSize="10"
                        fill={EDGE_STROKE[e.kind]} className="tabular">
                    {e.label}
                  </text>
                )}
              </g>
            );
          })}
        </g>
        <g>
          {nodes.map((n) => {
            const p = positions[n.id];
            if (!p) return null;
            const r = radiusFor(n);
            const w = widthFor(n.label, r);
            const big = BIG_KINDS.has(n.kind);
            return (
              <g key={n.id} className="kg-enter" transform={`translate(${p.x} ${p.y})`}>
                {/* Prefixed so this never exactly duplicates the visible <text> label (which would
                    make the two indistinguishable to text queries, including in our own tests). */}
                <title>Node: {n.label}{n.detail ? ` — ${n.detail}` : ""}</title>
                {big ? (
                  <rect x={-w / 2} y={-16} width={w} height={32} rx={8}
                        fill={NODE_FILL[n.kind]} stroke={NODE_STROKE[n.group]} strokeWidth={1.5} />
                ) : (
                  <rect x={-w / 2} y={-13} width={w} height={26} rx={13}
                        fill={NODE_FILL[n.kind] ?? "var(--color-sheet)"} stroke={NODE_STROKE[n.group]} strokeWidth={1.3} />
                )}
                <text x={0} y={4} textAnchor="middle" fontSize={big ? 12 : 10.5}
                      fontWeight={big ? 600 : 500}
                      fill={NODE_TEXT[n.kind] ?? "var(--color-ink)"}>
                  {n.label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate">
        {caption && <p>{caption}</p>}
        <ul className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Line colors">
          {(["exact", "related", "semantic"] as const).map((k) => (
            <li key={k} className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-5" style={{
                background: KIND[k].stroke,
                borderTop: k === "exact" ? undefined : `2px ${k === "related" ? "dashed" : "dotted"} ${KIND[k].stroke}`,
                height: k === "exact" ? 2 : 0,
              }} />
              {KIND[k].label}
            </li>
          ))}
          <li className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--color-blueprint)" }} />
            Supports score
          </li>
        </ul>
      </div>
    </div>
  );
}
