import { FileText, X } from "lucide-react";
import { useId, useRef, useState } from "react";

export const ACCEPT = ".pdf,.docx,.txt";
const MAX_MB = 2;

export function validateFile(f: File): string | null {
  if (!/\.(pdf|docx|txt)$/i.test(f.name)) return "Use a PDF, DOCX or TXT file.";
  if (f.size > MAX_MB * 1024 * 1024) return `Files must be ${MAX_MB} MB or smaller.`;
  return null;
}

export function FileDrop({
  files, onFiles, multiple = false, hint,
}: { files: File[]; onFiles: (f: File[]) => void; multiple?: boolean; hint: string }) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const take = (list: FileList | null) => {
    if (!list) return;
    const picked = Array.from(list);
    const bad = picked.map(validateFile).find(Boolean);
    setError(bad ?? null);
    const good = picked.filter((f) => !validateFile(f));
    onFiles(multiple ? [...files, ...good] : good.slice(0, 1));
  };

  return (
    <div>
      <label
        htmlFor={id}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); take(e.dataTransfer.files); }}
        className={`flex min-h-40 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed px-4 py-6 text-center transition-colors ${
          over ? "border-blueprint bg-blueprint-soft" : "border-rule bg-paper hover:border-slate"
        }`}
      >
        <FileText className="size-6 text-slate" aria-hidden />
        <span className="font-medium">Drop {multiple ? "resumes" : "a resume"} here or choose {multiple ? "files" : "a file"}</span>
        <span className="text-sm text-slate">{hint}</span>
        <input id={id} ref={input} type="file" accept={ACCEPT} multiple={multiple} className="sr-only"
          onChange={(e) => { take(e.target.files); if (input.current) input.current.value = ""; }} />
      </label>
      {error && <p className="mt-2 text-sm text-missing" role="alert">{error}</p>}
      {files.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center justify-between gap-3 rounded-md border border-rule bg-sheet px-3 py-2 text-sm">
              <span className="truncate">{f.name}</span>
              <button type="button" aria-label={`Remove ${f.name}`} className="text-slate hover:text-missing"
                onClick={() => onFiles(files.filter((_, j) => j !== i))}>
                <X className="size-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
