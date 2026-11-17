import { CircleAlert } from "lucide-react";

export function Notice({ title, children, tone = "warn" }: { title: string; children?: React.ReactNode; tone?: "warn" | "error" }) {
  const color = tone === "error" ? "border-missing bg-missing-soft" : "border-related bg-related-soft";
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`flex gap-3 rounded-md border-l-4 p-4 ${color}`}>
      <CircleAlert className={`mt-0.5 size-5 shrink-0 ${tone === "error" ? "text-missing" : "text-related"}`} aria-hidden />
      <div>
        <p className="font-semibold">{title}</p>
        {children && <div className="mt-1 text-sm text-ink/80">{children}</div>}
      </div>
    </div>
  );
}
