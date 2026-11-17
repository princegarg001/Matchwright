import { FileDrop } from "./FileDrop";
import { Segmented } from "./Segmented";

export type ResumeMode = "file" | "paste";

export function ResumeInput({
  mode, onMode, file, onFile, text, onText,
}: {
  mode: ResumeMode; onMode: (m: ResumeMode) => void;
  file: File | null; onFile: (f: File | null) => void;
  text: string; onText: (t: string) => void;
}) {
  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Resume</h2>
        <Segmented label="Resume input" value={mode} onChange={onMode}
          options={[{ value: "file", label: "Upload file" }, { value: "paste", label: "Paste text" }]} />
      </div>
      {mode === "file" ? (
        <FileDrop files={file ? [file] : []} onFiles={(f) => onFile(f[0] ?? null)} hint="PDF, DOCX or TXT, up to 2 MB. Scanned images can't be read." />
      ) : (
        <textarea
          aria-label="Resume text"
          value={text}
          onChange={(e) => onText(e.target.value)}
          placeholder="Paste the full resume, including skills and experience."
          className="min-h-64 flex-1 resize-y rounded-md border border-rule bg-sheet p-3 text-sm leading-relaxed placeholder:text-slate/70 focus:border-blueprint focus:outline-none"
        />
      )}
      <p className="text-xs text-slate">Emails, phone numbers and links are removed before the model reads anything.</p>
    </div>
  );
}
