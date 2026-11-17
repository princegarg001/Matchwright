import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function ModelStatus() {
  const q = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  const [color, text] = q.isError
    ? ["bg-missing", "API unreachable"]
    : !q.data
      ? ["bg-slate/50", "Checking model"]
      : q.data.offline_mode
        ? ["bg-related", "Offline mode"]
        : q.data.llm.loaded
          ? ["bg-exact", `${q.data.llm.model} ready`]
          : ["bg-missing", "Model not loaded"];
  return (
    <p className="flex items-center gap-2 text-sm text-slate" role="status">
      <span className={`size-2 rounded-full ${color}`} aria-hidden />
      {text}
    </p>
  );
}
