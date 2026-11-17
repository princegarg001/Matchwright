import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Notice } from "../components/Notice";
import { ResultView } from "../components/ResultView";
import { api } from "../lib/api";

export function MatchDetailPage() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["match", id], queryFn: () => api.getMatch(id), retry: false });
  return (
    <div className="space-y-8">
      <Link to="/" className="text-sm font-medium text-blueprint underline underline-offset-2">Score another match</Link>
      <h1 className="text-3xl font-semibold tracking-tight">Saved result</h1>
      {q.isPending && <p className="text-slate">Loading result…</p>}
      {q.isError && <Notice tone="error" title="This result wasn't found.">The link may be wrong, or the result was deleted.</Notice>}
      {q.data && <ResultView result={q.data} />}
    </div>
  );
}
