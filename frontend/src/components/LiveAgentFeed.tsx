import { TOOL_LABEL, seconds } from "../lib/format";
import type { LiveStep } from "../lib/useKnowledgeGraphStream";

/** The live step feed shown while /v1/match/stream is still running — each row appears the
 * instant that step finishes, which is what makes the knowledge graph above it feel "live". */
export function LiveAgentFeed({ steps, running }: { steps: LiveStep[]; running: boolean }) {
  if (!steps.length) return null;
  return (
    <ol className="space-y-0" aria-live="polite">
      {steps.map((s, i) => (
        <li key={s.seq} className="kg-enter relative grid grid-cols-[1.75rem_1fr] gap-3 pb-4 last:pb-0">
          {i < steps.length - 1 && <span className="absolute left-[0.8rem] top-7 bottom-0 w-px bg-rule" aria-hidden />}
          <span className="tabular grid size-7 place-items-center rounded-full border border-rule bg-sheet text-xs font-semibold">
            {i + 1}
          </span>
          <div className="min-w-0 pt-0.5 text-sm">
            <p className="font-medium">{TOOL_LABEL[s.step] ?? s.step}</p>
            <p className="text-slate">{s.message}</p>
            <p className="text-xs text-slate tabular">
              {seconds(s.ms)}{s.by === "fallback" ? ", run by the fixed pipeline" : ""}
            </p>
          </div>
        </li>
      ))}
      {running && (
        <li className="grid grid-cols-[1.75rem_1fr] gap-3">
          <span className="grid size-7 place-items-center" aria-hidden>
            <span className="relative flex size-2.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-blueprint/50" />
              <span className="relative inline-flex size-2.5 rounded-full bg-blueprint" />
            </span>
          </span>
          <p className="pt-0.5 text-sm text-slate">Working…</p>
        </li>
      )}
    </ol>
  );
}
