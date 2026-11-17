import type { KGNode } from "./types";

export interface Point {
  x: number;
  y: number;
}

export const VIEW_W = 1000;

const COLUMN_X: Record<KGNode["group"], number> = {
  resume: 150,
  jd: 850,
  result: 500,
  shared: 500,
};

// Within a column, pin the "big" nodes (documents, the final score) first, in this order,
// then lay out everything else in the order it arrived — so the graph grows downward and to
// the side as the agent works, instead of jumping around.
const KIND_RANK: Record<string, number> = {
  resume_doc: 0, jd_doc: 0, score: 0,
  experience: 1, education: 1,
  sub_score: 2,
  resume_skill: 3, jd_skill: 3, canonical_skill: 3, soft_skill: 3,
  explanation: 4,
};

/** Deterministic layered layout: one column per group, stacked top-to-bottom by kind then arrival
 * order. No physics simulation, so it never jitters and stays stable as nodes are added live. */
export function layoutGraph(nodes: KGNode[], height: number): Record<string, Point> {
  const byGroup = new Map<KGNode["group"], KGNode[]>();
  for (const n of nodes) {
    const list = byGroup.get(n.group) ?? [];
    list.push(n);
    byGroup.set(n.group, list);
  }

  const positions: Record<string, Point> = {};
  const top = 56;
  const bottom = height - 40;

  for (const [group, list] of byGroup) {
    const sorted = [...list].sort((a, b) => (KIND_RANK[a.kind] ?? 9) - (KIND_RANK[b.kind] ?? 9));
    const n = sorted.length;
    const x = COLUMN_X[group] ?? VIEW_W / 2;
    sorted.forEach((node, i) => {
      const y = n <= 1 ? (top + bottom) / 2 : top + ((bottom - top) * i) / (n - 1);
      positions[node.id] = { x, y };
    });
  }
  return positions;
}

/** A compact height that keeps rows readable without wasting space when a graph is small. */
export function graphHeight(nodes: KGNode[]): number {
  const maxPerColumn = Math.max(1, ...Array.from(
    nodes.reduce((m, n) => m.set(n.group, (m.get(n.group) ?? 0) + 1), new Map<string, number>()).values(),
  ));
  return Math.max(320, Math.min(760, 70 + maxPerColumn * 46));
}
