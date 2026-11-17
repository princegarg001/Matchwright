export function Segmented<T extends string>({
  value, onChange, options, label,
}: { value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; label: string }) {
  return (
    <div role="tablist" aria-label={label} className="inline-flex rounded-md border border-rule bg-paper p-0.5 text-sm">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
          className={`rounded px-3 py-1 font-medium transition-colors ${
            value === o.value ? "bg-sheet text-ink shadow-[0_0_0_1px_var(--color-rule)]" : "text-slate hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
