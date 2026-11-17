import { render, screen } from "@testing-library/react";
import { KnowledgeGraphView } from "../components/KnowledgeGraphView";
import { graphHeight, layoutGraph } from "../lib/kgLayout";
import { okGraph } from "./fixtures";

describe("kgLayout", () => {
  it("places resume nodes left of jd nodes and keeps every node inside the view", () => {
    const h = graphHeight(okGraph.nodes);
    const pos = layoutGraph(okGraph.nodes, h);
    expect(pos["doc:resume"].x).toBeLessThan(pos["doc:jd"].x);
    for (const n of okGraph.nodes) {
      expect(pos[n.id].y).toBeGreaterThanOrEqual(0);
      expect(pos[n.id].y).toBeLessThanOrEqual(h);
    }
  });

  it("grows the view height with more nodes per column, within bounds", () => {
    expect(graphHeight([])).toBeGreaterThanOrEqual(320);
    const many = Array.from({ length: 30 }, (_, i) => ({
      id: `n${i}`, kind: "resume_skill" as const, label: `skill ${i}`, detail: "", group: "resume" as const, weight: 1,
    }));
    expect(graphHeight(many)).toBeLessThanOrEqual(760);
  });
});

describe("KnowledgeGraphView", () => {
  it("shows a placeholder before any nodes arrive", () => {
    render(<KnowledgeGraphView nodes={[]} edges={[]} />);
    expect(screen.getByText(/graph will appear here/i)).toBeInTheDocument();
  });

  it("renders every node label once nodes are present", () => {
    render(<KnowledgeGraphView nodes={okGraph.nodes} edges={okGraph.edges} caption="3 nodes" />);
    expect(screen.getByText("Resume")).toBeInTheDocument();
    expect(screen.getByText("Job description")).toBeInTheDocument();
    expect(screen.getByText("74 / 100")).toBeInTheDocument();
    expect(screen.getByText("3 nodes")).toBeInTheDocument();
  });
});
