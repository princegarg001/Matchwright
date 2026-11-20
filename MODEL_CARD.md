# Model card — Matchwright (Resume–JD Matcher)

**Intended use.** Decision support for a recruiter or hiring manager screening resumes against a
job description: a 0–100 fit score, three grounded reasons, and a requirement-by-requirement
ledger of evidence. A person makes every hiring decision; the tool never auto-rejects anyone.

**Out of scope.** Fully automated accept/reject decisions. Non-English documents. Roles or skills
far outside the alias vocabulary in `config/aliases.yaml` (extend it before relying on the tool
for a new domain). Legal/compliance screening (background checks, visa status, etc.).

**Models.**
- Default (fast, `temperature=0`): hosted via Groq, `openai/gpt-oss-120b` for extraction/scoring/
  explanation and `qwen/qwen3.8-27b` for the ReAct agent loop specifically — measured directly:
  gpt-oss-120b gives materially better structured-extraction quality but never progresses past
  step 1 of the plain-text ReAct format (it doesn't act on its own tool Observations), so the
  agent uses a different, confirmed-compatible model. ~2-3s/call.
- Local/offline alternative (`LLM_PROVIDER=ollama`): Phi-3-mini (3.8B) via Ollama, 4K context,
  no API key, full privacy — ~25-50s/call on CPU, the path this project's DoD originally targeted.
- Optional: `BAAI/bge-small-en-v1.5` sentence embeddings (via `sentence-transformers`, downloaded
  from the Hugging Face Hub on first use) for the semantic-similarity sub-score; disabled by
  default on the hosted deployment to keep the image small.

**Data.**
- Kaggle "Resume Dataset" (`snehaanbhawal/resume-dataset`, 2,400+ resumes, 24 categories).
- Kaggle "LinkedIn Job Postings 2023–2024" (`arshkon/linkedin-job-postings`, ~124k postings).
- Remotive (free, no key) and optionally Adzuna (free tier, needs an app id/key) for live job
  postings used in the UI's "Find a live job" search and in `make data --live`.

**How the score is produced.** The LLM only extracts (skills, years, education) from text; a
deterministic Python function (`app/tools/scoring.py`) computes the score from that structured
data; the LLM writes the final explanation, which a validator checks is grounded in the computed
facts before it is shown. The score is reproducible and unit-tested, and is not directly subject
to prompt injection inside the resume or JD text.

**Metrics.** See `reports/eval.md` (Spearman correlation and NDCG@5 against human ratings,
compared to a TF-IDF baseline) and `reports/bias.md` (counterfactual fairness: score should not
move by more than 2 points when names/pronouns are swapped) after running `make eval` / `make bias`.

**Limitations.** Kaggle resumes are template-formatted and may not represent your real applicant
pool. A 4K-context small model means long documents are chunked, so extraction can miss a skill
mentioned only once in a chunk the model doesn't see (capped at `MAX_CHUNKS_PER_DOC`). CPU-only
Ollama inference is slow (tens of seconds per call). Groq's free tier caps `gpt-oss-120b` at
200,000 tokens/day per account — a handful of extraction-heavy runs can exhaust it for the day,
after which calls fail over to the deterministic keyword extractor (correct scores, lower
`confidence`) until the quota resets; see `docs/troubleshooting.md`. English only.

**Human oversight.** Every score is logged with input hashes, the model used, and the exact
weights (`app/core/store.py`), so a result can be audited later. The UI's "requirement ledger"
and "knowledge graph" views are deliberately literal about what matched and what didn't, so a
reviewer can check the model's work rather than trust a single number.

**Contact.** See the repository owner listed in the GitHub remote.
