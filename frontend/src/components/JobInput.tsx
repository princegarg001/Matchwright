import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import type { LiveJob } from "../lib/types";
import { Segmented } from "./Segmented";

type Mode = "paste" | "search";

export function JobInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [mode, setMode] = useState<Mode>("paste");
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<LiveJob | null>(null);
  const jobs = useQuery({ queryKey: ["jobs", query], queryFn: () => api.searchJobs(query), enabled: query.length > 1 });

  const choose = (job: LiveJob) => {
    setPicked(job);
    onChange(job.text);
    setMode("paste");
  };

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Job description</h2>
        <Segmented label="Job description input" value={mode} onChange={setMode}
          options={[{ value: "paste", label: "Paste text" }, { value: "search", label: "Find a live job" }]} />
      </div>

      {mode === "paste" ? (
        <>
          <textarea
            aria-label="Job description text"
            value={value}
            onChange={(e) => { onChange(e.target.value); setPicked(null); }}
            placeholder="Paste the full job description, including requirements and preferred skills."
            className="min-h-64 flex-1 resize-y rounded-md border border-rule bg-sheet p-3 text-sm leading-relaxed placeholder:text-slate/70 focus:border-blueprint focus:outline-none"
          />
          {picked && (
            <p className="text-sm text-slate">
              {picked.title} at {picked.company}, from{" "}
              <a href={picked.url} target="_blank" rel="noreferrer" className="font-medium text-blueprint underline underline-offset-2">
                {picked.source === "remotive" ? "Remotive" : picked.source}
              </a>
            </p>
          )}
        </>
      ) : (
        <div className="flex flex-1 flex-col gap-3">
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setQuery(draft.trim()); }}>
            <input
              aria-label="Job title or skill"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Job title or skill, for example data engineer"
              className="flex-1 rounded-md border border-rule bg-sheet px-3 py-2 text-sm focus:border-blueprint focus:outline-none"
            />
            <button type="submit" className="inline-flex items-center gap-1.5 rounded-md border border-rule bg-sheet px-3 text-sm font-medium hover:border-blueprint">
              <Search className="size-4" aria-hidden /> Search
            </button>
          </form>
          <div className="min-h-52 flex-1 overflow-auto rounded-md border border-rule bg-sheet" aria-live="polite">
            {!query && <p className="p-4 text-sm text-slate">Search remote job boards and pick a posting to score against.</p>}
            {jobs.isFetching && <p className="p-4 text-sm text-slate">Searching…</p>}
            {jobs.isError && <p className="p-4 text-sm text-missing">Job search is unavailable right now. Paste a job description instead.</p>}
            {jobs.data && jobs.data.results.length === 0 && <p className="p-4 text-sm text-slate">No jobs found for “{query}”. Try a broader title.</p>}
            <ul>
              {jobs.data?.results.map((j) => (
                <li key={j.job_id} className="border-b border-rule last:border-0">
                  <button type="button" onClick={() => choose(j)} className="w-full px-4 py-3 text-left hover:bg-blueprint-soft">
                    <span className="block font-medium">{j.title}</span>
                    <span className="block text-sm text-slate">{j.company}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
