import { SUB_SCORE_LABEL, pct } from "../lib/format";

const ORDER = ["required", "preferred", "semantic", "experience", "education"];

export function SubScores({ subScores }: { subScores: Record<string, number> }) {
  const keys = ORDER.filter((k) => k in subScores);
  return (
    <section aria-labelledby="subs-title">
      <h2 id="subs-title" className="text-lg font-semibold">
        Score breakdown
      </h2>
      <dl className="mt-3 space-y-3">
        {keys.map((k) => (
          <div key={k} className="grid grid-cols-[9.5rem_1fr_3rem] items-center gap-3 text-sm">
            <dt className="text-slate">{SUB_SCORE_LABEL[k] ?? k}</dt>
            <dd className="h-2 rounded-sm bg-rule/70" aria-hidden>
              <div className="h-full rounded-sm bg-blueprint" style={{ width: pct(subScores[k]) }} />
            </dd>
            <dd className="tabular text-right font-medium">{pct(subScores[k])}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 max-w-prose text-xs text-slate">
        Experience and education count for less when the core skills don't match, so a long career in another field can't
        lift a weak fit.
      </p>
    </section>
  );
}
