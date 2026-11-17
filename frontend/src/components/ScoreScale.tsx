import { BANDS, bandLabel } from "../lib/format";
import type { Band } from "../lib/types";

const BAND_FILL: Record<Band, string> = {
  weak: "bg-missing/15",
  partial: "bg-related/15",
  good: "bg-exact/15",
  strong: "bg-exact/30",
};

/** The score on a 0–100 scale with the band thresholds drawn, so 59 vs 61 reads as a boundary, not a mystery. */
export function ScoreScale({ score, band, confidence }: { score: number; band: Band | null; confidence: string | null }) {
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <section aria-label="Match score">
      <div className="flex items-end gap-4">
        <p className="tabular text-7xl font-semibold leading-none tracking-tight text-ink" data-testid="score">
          {score}
        </p>
        <div className="pb-1.5">
          <p className="text-xl font-semibold">{bandLabel(band)}</p>
          {confidence && <p className="text-sm text-slate">Extraction confidence: {confidence}</p>}
        </div>
      </div>

      <div className="relative mt-6 h-3 w-full max-w-md" role="img" aria-label={`Score ${score} out of 100, ${bandLabel(band)}`}>
        <div className="flex h-full overflow-hidden rounded-sm">
          {BANDS.map((b) => (
            <div key={b.band} className={`${BAND_FILL[b.band]} h-full`} style={{ width: `${Math.min(b.to, 100) - b.from}%` }} />
          ))}
        </div>
        <div
          className="absolute -top-1.5 h-6 w-1 -translate-x-1/2 rounded-full bg-ink"
          style={{ left: `${clamped}%` }}
          aria-hidden
        />
      </div>
      <div className="relative mt-1.5 h-4 w-full max-w-md text-xs text-slate tabular" aria-hidden>
        {[0, 40, 60, 80, 100].map((t) => (
          <span key={t} className="absolute -translate-x-1/2" style={{ left: `${t}%` }}>
            {t}
          </span>
        ))}
      </div>
    </section>
  );
}
