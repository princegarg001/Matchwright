import { Check, Link2 } from "lucide-react";
import { useState } from "react";
import { seconds } from "../lib/format";
import type { MatchResult } from "../lib/types";
import { AgentTrace } from "./AgentTrace";
import { KnowledgeGraphView } from "./KnowledgeGraphView";
import { Notice } from "./Notice";
import { RequirementLedger } from "./RequirementLedger";
import { ScoreScale } from "./ScoreScale";
import { SubScores } from "./SubScores";

const MODE_LABEL: Record<string, string> = {
  agent: "Agent ran every step",
  "agent+fallback": "Agent, completed by the fixed pipeline",
  fallback_orchestrator: "Fixed pipeline (agent unavailable)",
  orchestrator: "Fixed pipeline",
  live_graph: "Ran step by step for the live graph view",
  offline: "Offline mode, no language model",
  guard: "Stopped before scoring",
};

export function modeLabel(mode: string) {
  const cached = mode.endsWith("+cache");
  const base = MODE_LABEL[mode.replace(/\+cache$/, "")] ?? mode;
  return cached ? `${base} (from cache)` : base;
}

function CopyLink({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  const url = `${window.location.origin}/matches/${id}`;
  return (
    <button
      type="button"
      onClick={() => navigator.clipboard?.writeText(url).then(() => setCopied(true))}
      className="inline-flex items-center gap-1.5 rounded-md border border-rule bg-sheet px-3 py-1.5 text-sm font-medium hover:border-blueprint"
    >
      {copied ? <Check className="size-4 text-exact" aria-hidden /> : <Link2 className="size-4" aria-hidden />}
      {copied ? "Link copied" : "Copy link to this result"}
    </button>
  );
}

export function ResultView({ result }: { result: MatchResult }) {
  if (result.status !== "ok" || result.score === null) {
    return (
      <Notice title={result.message ?? "This match could not be scored."}>
        {result.hint && <p>{result.hint}</p>}
      </Notice>
    );
  }
  return (
    <article className="space-y-12" aria-label="Match result">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <ScoreScale score={result.score} band={result.band} confidence={result.confidence} />
        <section aria-labelledby="why-title">
          <h2 id="why-title" className="text-lg font-semibold">
            Why this score
          </h2>
          <ul className="mt-3 max-w-prose space-y-3">
            {result.justifications.map((j, i) => (
              <li key={i} className="border-l-2 border-blueprint pl-4 leading-relaxed">
                {j}
              </li>
            ))}
          </ul>
        </section>
      </div>

      {result.requirements.length > 0 && <RequirementLedger requirements={result.requirements} />}

      {result.knowledge_graph && result.knowledge_graph.nodes.length > 0 && (
        <section aria-labelledby="kg-title">
          <h2 id="kg-title" className="text-2xl font-semibold">
            Knowledge graph
          </h2>
          <p className="mt-1 max-w-prose text-slate">
            Every node the agent built while scoring this match: both documents, the skills it read out of them, how
            each job requirement was matched, and how the sub-scores add up to the final number.
          </p>
          <div className="mt-4 rounded-lg border border-rule bg-sheet p-4">
            <KnowledgeGraphView nodes={result.knowledge_graph.nodes} edges={result.knowledge_graph.edges} />
          </div>
        </section>
      )}

      <div className="grid gap-10 md:grid-cols-2">
        <SubScores subScores={result.sub_scores} />
        <AgentTrace steps={result.trace} />
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-4 text-sm text-slate">
        <dl className="flex flex-wrap gap-x-6 gap-y-1">
          <div className="flex gap-1.5"><dt>Model</dt><dd className="font-medium text-ink">{result.model}</dd></div>
          <div className="flex gap-1.5"><dt>Run</dt><dd className="font-medium text-ink">{modeLabel(result.mode)}</dd></div>
          <div className="flex gap-1.5"><dt>Time</dt><dd className="tabular font-medium text-ink">{seconds(result.latency_ms)}</dd></div>
        </dl>
        <CopyLink id={result.match_id} />
      </footer>
    </article>
  );
}
