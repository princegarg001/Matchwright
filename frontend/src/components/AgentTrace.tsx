import { TOOL_LABEL, seconds } from "../lib/format";
import type { TraceStep } from "../lib/types";

/** The agent's tool calls in order. A real sequence, so it is numbered. */
export function AgentTrace({ steps }: { steps: TraceStep[] }) {
  const calls = steps.filter((s) => s.tool);
  if (!calls.length) return null;
  return (
    <section aria-labelledby="trace-title">
      <h2 id="trace-title" className="text-lg font-semibold">
        How the agent worked
      </h2>
      <ol className="mt-3 space-y-0">
        {calls.map((s, i) => (
          <li key={i} className="relative grid grid-cols-[1.75rem_1fr] gap-3 pb-4 last:pb-0">
            {i < calls.length - 1 && <span className="absolute left-[0.8rem] top-7 bottom-0 w-px bg-rule" aria-hidden />}
            <span className="tabular grid size-7 place-items-center rounded-full border border-rule bg-sheet text-xs font-semibold">
              {i + 1}
            </span>
            <div className="min-w-0 pt-0.5 text-sm">
              <p className="font-medium">
                {TOOL_LABEL[s.tool!] ?? s.tool}
                {s.input && s.tool === "extract_skills" && <span className="font-normal text-slate"> from the {s.input === "jd" ? "job description" : "resume"}</span>}
              </p>
              <p className="text-slate">
                <code className="text-xs text-ink">{s.tool}</code> {s.output}
              </p>
              <p className="text-xs text-slate tabular">
                {`${seconds(s.ms ?? 0)}${s.by === "fallback" ? ", run by the fixed pipeline" : ""}`}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
