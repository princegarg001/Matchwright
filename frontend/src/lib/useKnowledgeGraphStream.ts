import { useCallback, useRef, useState } from "react";
import { ApiError } from "./api";
import type { KGEdge, KGEvent, KGNode, MatchResult } from "./types";

export interface LiveStep {
  seq: number;
  step: string;
  message: string;
  ms: number;
  by: KGEvent["by"];
}

/**
 * Accumulates the knowledge graph and the step feed from a streaming /v1/match/stream(/upload)
 * call. Nodes/edges arrive as deltas (only what's new or changed) and are merged by id, so the
 * graph genuinely grows in front of the viewer instead of appearing all at once.
 */
export function useKnowledgeGraphStream() {
  const [nodes, setNodes] = useState<Record<string, KGNode>>({});
  const [edges, setEdges] = useState<Record<string, KGEdge>>({});
  const [steps, setSteps] = useState<LiveStep[]>([]);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const generation = useRef(0);

  const run = useCallback(async (send: (onEvent: (event: KGEvent) => void) => Promise<void>) => {
    const gen = ++generation.current;
    setNodes({});
    setEdges({});
    setSteps([]);
    setResult(null);
    setError(null);
    setRunning(true);

    const onEvent = (event: KGEvent) => {
      if (generation.current !== gen) return; // a newer run started; drop stale events
      if (event.nodes.length) setNodes((prev) => { const next = { ...prev }; event.nodes.forEach((n) => (next[n.id] = n)); return next; });
      if (event.edges.length) setEdges((prev) => { const next = { ...prev }; event.edges.forEach((e) => (next[e.id] = e)); return next; });
      if (event.step !== "start") {
        setSteps((prev) => [...prev, { seq: event.seq, step: event.step, message: event.message, ms: event.ms, by: event.by }]);
      }
      if (event.done && event.result) setResult(event.result);
    };

    try {
      await send(onEvent);
    } catch (e) {
      if (generation.current === gen) setError(e instanceof ApiError ? e.message : "Scoring failed.");
    } finally {
      if (generation.current === gen) setRunning(false);
    }
  }, []);

  return {
    nodes: Object.values(nodes),
    edges: Object.values(edges),
    steps,
    result,
    error,
    running,
    run,
  };
}
