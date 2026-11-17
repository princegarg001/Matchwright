import { useEffect, useRef, useState } from "react";
import { JobInput } from "../components/JobInput";
import { KnowledgeGraphView } from "../components/KnowledgeGraphView";
import { LiveAgentFeed } from "../components/LiveAgentFeed";
import { Notice } from "../components/Notice";
import { ResultView } from "../components/ResultView";
import { ResumeInput, type ResumeMode } from "../components/ResumeInput";
import { streamApi } from "../lib/api";
import { useKnowledgeGraphStream } from "../lib/useKnowledgeGraphStream";

export function MatchPage() {
  const [mode, setMode] = useState<ResumeMode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [jd, setJd] = useState("");
  const resultRef = useRef<HTMLDivElement>(null);
  const graph = useKnowledgeGraphStream();

  useEffect(() => {
    if (graph.result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [graph.result]);

  const hasResume = mode === "file" ? !!file : resumeText.trim().length > 0;
  const ready = hasResume && jd.trim().length > 0;
  const missing = !hasResume ? "Add a resume to continue." : !jd.trim() ? "Add a job description to continue." : "";

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ready || graph.running) return;
    graph.run((onEvent) =>
      mode === "file" && file ? streamApi.matchFile(file, jd, onEvent) : streamApi.match(resumeText, jd, onEvent),
    );
  };

  const showLive = graph.running || (graph.steps.length > 0 && !graph.result);

  return (
    <div className="space-y-12">
      <header className="max-w-2xl">
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">How well does this resume fit the job?</h1>
        <p className="mt-3 text-lg text-slate">
          Get a score out of 100, three plain reasons, and the agent's own knowledge graph built live as it reads
          both documents.
        </p>
      </header>

      <form onSubmit={submit} className="rounded-lg border border-rule bg-sheet p-5 md:p-6">
        <div className="grid gap-8 lg:grid-cols-2">
          <ResumeInput mode={mode} onMode={setMode} file={file} onFile={setFile} text={resumeText} onText={setResumeText} />
          <JobInput value={jd} onChange={setJd} />
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-rule pt-5">
          <button
            type="submit"
            disabled={!ready || graph.running}
            className="rounded-md bg-blueprint px-5 py-2.5 font-semibold text-paper transition-colors hover:bg-ink disabled:cursor-not-allowed disabled:bg-slate/40"
          >
            {graph.running ? "Scoring…" : "Score match"}
          </button>
          {!graph.running && missing && <p className="text-sm text-slate">{missing}</p>}
        </div>
      </form>

      <div ref={resultRef} className="scroll-mt-6 space-y-8">
        {graph.error && (
          <Notice tone="error" title={graph.error}>
            <p>Check that the API is running, then try again.</p>
          </Notice>
        )}

        {showLive && (
          <section aria-labelledby="live-title" className="rounded-lg border border-rule bg-sheet p-5 md:p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="live-title" className="text-xl font-semibold">
                How the agent is thinking
              </h2>
              <p className="text-sm text-slate">Phi-3-mini is reading both documents; this updates as each step finishes.</p>
            </div>
            <div className="mt-5 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <KnowledgeGraphView nodes={graph.nodes} edges={graph.edges} caption={`${graph.nodes.length} nodes so far`} />
              <LiveAgentFeed steps={graph.steps} running={graph.running} />
            </div>
          </section>
        )}

        {graph.result && <ResultView result={graph.result} />}
      </div>
    </div>
  );
}
