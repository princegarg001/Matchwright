import { KIND } from "../lib/format";
import type { MatchKind, Requirement } from "../lib/types";

const ORDER: MatchKind[] = ["exact", "related", "semantic", "missing"];

function Connector({ kind }: { kind: MatchKind }) {
  const k = KIND[kind];
  if (kind === "missing") {
    return (
      <div className="flex items-center" aria-hidden>
        <span className="size-2 shrink-0 rounded-full" style={{ background: k.stroke }} />
        <span className="h-0.5 w-2/5" style={{ background: k.stroke }} />
        <span className="mx-auto text-sm font-semibold leading-none" style={{ color: k.stroke }}>
          ×
        </span>
        <span className="w-2/5" />
        <span className="size-2 shrink-0 rounded-full border-2" style={{ borderColor: k.stroke }} />
      </div>
    );
  }
  const style = kind === "exact" ? "solid" : kind === "related" ? "dashed" : "dotted";
  return (
    <div className="flex items-center" aria-hidden>
      <span className="size-2 shrink-0 rounded-full" style={{ background: k.stroke }} />
      <span className="flex-1 border-t-2" style={{ borderColor: k.stroke, borderTopStyle: style }} />
      <span className="size-2 shrink-0 rounded-full" style={{ background: k.stroke }} />
    </div>
  );
}

function Row({ r }: { r: Requirement }) {
  const k = KIND[r.kind];
  return (
    <li className="grid grid-cols-[minmax(0,1fr)] gap-x-4 gap-y-1 border-t border-rule py-3 md:grid-cols-[minmax(0,14rem)_6rem_minmax(0,1fr)] md:items-center">
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="font-medium">{r.jd_skill}</span>
        {r.mandatory && <span className="rounded-sm bg-ink px-1.5 py-0.5 text-xs font-medium text-paper">Must have</span>}
      </div>
      <div className="hidden md:block">
        <Connector kind={r.kind} />
      </div>
      <div className="min-w-0 text-sm">
        <span className={`mr-2 font-medium ${k.text}`}>
          <span className="md:sr-only">{k.label}: </span>
          {r.kind === "missing" ? "Not found in resume" : r.matched_with}
        </span>
        {r.kind !== "missing" && r.evidence && <q className="text-slate">{r.evidence}</q>}
      </div>
    </li>
  );
}

function Legend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate" aria-label="Line styles">
      {ORDER.map((kind) => (
        <li key={kind} className="flex items-center gap-2">
          <span className="w-10">
            <Connector kind={kind} />
          </span>
          {KIND[kind].label}
        </li>
      ))}
    </ul>
  );
}

/** Each job requirement joined to the resume evidence that satisfies it. */
export function RequirementLedger({ requirements }: { requirements: Requirement[] }) {
  const sort = (a: Requirement, b: Requirement) =>
    Number(b.mandatory) - Number(a.mandatory) || ORDER.indexOf(a.kind) - ORDER.indexOf(b.kind);
  const groups = [
    { title: "Required", rows: requirements.filter((r) => r.required).sort(sort) },
    { title: "Preferred", rows: requirements.filter((r) => !r.required).sort(sort) },
  ].filter((g) => g.rows.length);

  return (
    <section aria-labelledby="ledger-title" className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="ledger-title" className="text-2xl font-semibold">
            Requirements and evidence
          </h2>
          <p className="mt-1 text-slate">What the job asks for, joined to where the resume shows it.</p>
        </div>
        <Legend />
      </div>
      {groups.map((g) => (
        <div key={g.title}>
          <h3 className="mb-1 text-sm font-semibold text-slate">
            {g.title} <span className="tabular font-normal">({g.rows.filter((r) => r.kind !== "missing").length} of {g.rows.length} met)</span>
          </h3>
          <ul className="border-b border-rule">
            {g.rows.map((r) => (
              <Row key={r.jd_skill} r={r} />
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
