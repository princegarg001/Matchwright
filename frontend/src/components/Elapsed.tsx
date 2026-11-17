import { useEffect, useState } from "react";

export function Elapsed({ label }: { label: string }) {
  const [s, setS] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setS((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <p className="flex items-center gap-3 text-sm text-slate" role="status" aria-live="polite">
      <span className="relative flex size-2.5" aria-hidden>
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-blueprint/50" />
        <span className="relative inline-flex size-2.5 rounded-full bg-blueprint" />
      </span>
      {label} <span className="tabular">{Math.floor(s / 60)}:{String(s % 60).padStart(2, "0")}</span>
    </p>
  );
}
