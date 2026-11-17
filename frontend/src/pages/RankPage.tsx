import { useState } from "react";
import { Link } from "react-router-dom";
import { FileDrop } from "../components/FileDrop";
import { Notice } from "../components/Notice";
import { api, ApiError } from "../lib/api";
import { bandLabel } from "../lib/format";
import type { MatchResult } from "../lib/types";

type Row = { file: string; result?: MatchResult; error?: string };

export function RankPage() {
  const [jd, setJd] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [running, setRunning] = useState(false);
  const done = rows.filter((r) => r.result || r.error).length;

  const run = async () => {
    setRunning(true);
    setRows(files.map((f) => ({ file: f.name })));
    // One at a time: the local model handles one request well; parallel calls just queue.
    for (const [i, f] of files.entries()) {
      try {
        const result = await api.matchFile(f, jd);
        setRows((rs) => rs.map((r, j) => (j === i ? { ...r, result } : r)));
      } catch (e) {
        const error = e instanceof ApiError ? e.message : "Scoring failed.";
        setRows((rs) => rs.map((r, j) => (j === i ? { ...r, error } : r)));
      }
    }
    setRunning(false);
  };

  const ranked = [...rows].sort((a, b) => (b.result?.score ?? -1) - (a.result?.score ?? -1));

  return (
    <div className="space-y-10">
      <header className="max-w-2xl">
        <h1 className="text-4xl font-semibold tracking-tight">Rank resumes for one job</h1>
        <p className="mt-3 text-lg text-slate">Score up to 20 resumes against the same job description and compare them side by side.</p>
      </header>

      <div className="grid gap-8 rounded-lg border border-rule bg-sheet p-5 md:p-6 lg:grid-cols-2">
        <div className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Job description</h2>
          <textarea aria-label="Job description text" value={jd} onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the full job description."
            className="min-h-64 flex-1 rounded-md border border-rule bg-sheet p-3 text-sm leading-relaxed focus:border-blueprint focus:outline-none" />
        </div>
        <div className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Resumes</h2>
          <FileDrop multiple files={files} onFiles={(f) => setFiles(f.slice(0, 20))} hint="Up to 20 files. PDF, DOCX or TXT." />
        </div>
        <div className="flex items-center gap-4 border-t border-rule pt-5 lg:col-span-2">
          <button type="button" onClick={run} disabled={running || !jd.trim() || files.length === 0}
            className="rounded-md bg-blueprint px-5 py-2.5 font-semibold text-paper hover:bg-ink disabled:cursor-not-allowed disabled:bg-slate/40">
            {running ? `Scoring ${done + 1} of ${files.length}…` : `Rank ${files.length || ""} resume${files.length === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>

      {rows.length > 0 && (
        <section aria-labelledby="rank-title">
          <h2 id="rank-title" className="text-2xl font-semibold">Ranking</h2>
          <ol className="mt-4 border-b border-rule">
            {ranked.map((r, i) => (
              <li key={r.file} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-4 border-t border-rule py-4 md:grid-cols-[2rem_minmax(0,16rem)_10rem_minmax(0,1fr)] md:items-center">
                <span className="tabular text-lg font-semibold text-slate">{r.result?.score != null ? i + 1 : "–"}</span>
                <div className="min-w-0">
                  <p className="truncate font-medium">{r.file}</p>
                  {r.result?.score != null && (
                    <Link to={`/matches/${r.result.match_id}`} className="text-sm font-medium text-blueprint underline underline-offset-2">Open full result</Link>
                  )}
                </div>
                <div className="col-start-2 md:col-start-auto">
                  {r.result?.score != null ? (
                    <>
                      <div className="flex items-baseline gap-2"><span className="tabular text-2xl font-semibold">{r.result.score}</span><span className="text-sm text-slate">{bandLabel(r.result.band)}</span></div>
                      <div className="mt-1 h-1.5 rounded-sm bg-rule/70"><div className="h-full rounded-sm bg-blueprint" style={{ width: `${r.result.score}%` }} /></div>
                    </>
                  ) : r.error ? <span className="text-sm text-missing">{r.error}</span>
                    : r.result ? <span className="text-sm text-related">Not enough information</span>
                    : <span className="text-sm text-slate">Waiting…</span>}
                </div>
                <p className="col-start-2 text-sm text-slate md:col-start-auto">{r.result?.justifications[0] ?? r.result?.message ?? ""}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
      {!running && rows.length > 0 && rows.every((r) => r.error) && (
        <Notice tone="error" title="None of the resumes could be scored.">Check that the API is running, then try again.</Notice>
      )}
    </div>
  );
}
