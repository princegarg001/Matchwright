import type { Health, KGEvent, LiveJob, MatchResult } from "./types";

const BASE = "/api"; // proxied to FastAPI by Vite (dev) or nginx (prod), which add the API key

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public hint = "",
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, init);
  } catch {
    throw new ApiError(0, "Can't reach the matching service.", "Check that the API is running on port 8000.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error;
    throw new ApiError(res.status, err?.message ?? `Request failed (${res.status})`, err?.hint ?? "");
  }
  return body as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export type JobSource = "all" | "remotive" | "adzuna";

export const api = {
  health: () => request<Health>("/health"),

  match: (resume_text: string, jd_text: string) =>
    request<MatchResult>(
      "/v1/match",
      json({ resume_text, jd_text, options: { return_trace: true, use_cache: true } }),
    ),

  matchFile: (file: File, jd_text: string) => {
    const form = new FormData();
    form.append("resume", file);
    form.append("jd_text", jd_text);
    return request<MatchResult>("/v1/match/upload", { method: "POST", body: form });
  },

  getMatch: (id: string) => request<MatchResult>(`/v1/match/${encodeURIComponent(id)}`),

  searchJobs: (q: string, source: JobSource = "all") =>
    request<{ source: string; adzuna_configured?: boolean; results: LiveJob[] }>(
      `/v1/jobs/search?q=${encodeURIComponent(q)}&source=${encodeURIComponent(source)}&limit=10`,
    ),
};

/**
 * Reads newline-delimited JSON (one KGEvent per line) from a streaming match response and calls
 * `onEvent` for each one as it arrives — this is what makes the knowledge-graph view "live"
 * instead of a single snapshot at the end. Throws ApiError if the request itself fails; a graceful
 * "insufficient_information" result still arrives as a normal event with `done: true`.
 */
async function consumeNdjson(res: Response, onEvent: (event: KGEvent) => void): Promise<void> {
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => null);
    const err = body?.error;
    throw new ApiError(res.status, err?.message ?? `Request failed (${res.status})`, err?.hint ?? "");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline: number;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) onEvent(JSON.parse(line) as KGEvent);
    }
  }
  const tail = buffer.trim();
  if (tail) onEvent(JSON.parse(tail) as KGEvent);
}

export const streamApi = {
  match: async (resume_text: string, jd_text: string, onEvent: (event: KGEvent) => void): Promise<void> => {
    let res: Response;
    try {
      res = await fetch(BASE + "/v1/match/stream", json({ resume_text, jd_text }));
    } catch {
      throw new ApiError(0, "Can't reach the matching service.", "Check that the API is running on port 8000.");
    }
    await consumeNdjson(res, onEvent);
  },

  matchFile: async (file: File, jd_text: string, onEvent: (event: KGEvent) => void): Promise<void> => {
    const form = new FormData();
    form.append("resume", file);
    form.append("jd_text", jd_text);
    let res: Response;
    try {
      res = await fetch(BASE + "/v1/match/stream/upload", { method: "POST", body: form });
    } catch {
      throw new ApiError(0, "Can't reach the matching service.", "Check that the API is running on port 8000.");
    }
    await consumeNdjson(res, onEvent);
  },
};
