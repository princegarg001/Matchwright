# Matchwright — Resume–JD Matcher (Agentic, live knowledge graph)

![ci](https://github.com/<you>/matchwright/actions/workflows/ci.yml/badge.svg)

Scores a resume against a job description from 0–100 with 3 evidence-backed justifications, a
requirement-by-requirement evidence ledger, and a **live knowledge graph** of everything the agent
built while it worked — nodes and edges appear on screen the instant each step finishes, not after
the fact. Runs fully local on Phi-3-mini via Ollama, or against a hosted model for the public demo.

▶ Demo video: `<link>` · Live demo: `<link>` · API docs: `<link>/docs`

## How it works

The LLM **extracts** → plain Python **scores** → the LLM **explains**. A LangChain ReAct
`AgentExecutor` calls `extract_skills(resume)` → `extract_skills(jd)` → `normalize_skills` →
`score_match` → `explain_match`, in that exact order. The score is never decided by the model, so
it's reproducible, unit-tested, and not directly movable by text inside the resume or JD (see
`test_prompt_injection_does_not_change_score`).

```
Score = 100 × (0.45·required + 0.15·preferred + 0.15·semantic + 0.15·experience + 0.10·education)
capped at 60 if a must-have skill is missing.
```

### The knowledge graph (click "Score match" to see it)

Every tool call mutates one shared `MatchState` — the two documents, the skills extracted from
each, how they were normalised, how each requirement matched (or didn't), the sub-scores, and the
final explanation. `app/agent/kg.py` renders that state as a graph (`KGNode`/`KGEdge`), and
`app/agent/kg_stream.py` runs the real extraction/scoring/explanation functions one step at a
time, yielding only the nodes and edges that are new or changed after each step over
`POST /v1/match/stream` as newline-delimited JSON. The React UI
([`KnowledgeGraphView.tsx`](frontend/src/components/KnowledgeGraphView.tsx)) reads that stream and
grows the graph live — resume skills on the left, job requirements on the right, solid/dashed/
dotted lines for exact/related/similar matches (same convention as the requirement ledger), and
the score + sub-scores + explanation assembling in the middle as the last two steps run. The final
`MatchResult` also carries the finished graph (`knowledge_graph`), so a saved result
(`/matches/:id`) shows the same graph without needing to re-run anything.

`/v1/match` (the graded agentic path, driven by the real ReAct `AgentExecutor`) and
`/v1/match/stream` (the live-graph path, driving the same four tool functions directly so each
step's delta can be yielded immediately) both end up calling the identical extraction, scoring and
explanation code in `app/tools/` and `app/agent/steps.py` — neither is a simulation.

## Quick start

```bash
git clone <your-repo-url> matchwright && cd matchwright
cp .env.example .env
docker compose up --build          # app :8080, API :8000/docs
```

Local (no Docker):
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ollama pull phi3:mini && ollama serve &                  # https://ollama.com
make smoke && make run                                   # API on :8000
cd frontend && npm install && npm run dev                # UI on :5173
```

## What you need to provide

| What | Why | Get it |
|---|---|---|
| **Kaggle API token** (`kaggle.json`) | `make data` downloads the two training/eval datasets | kaggle.com → Settings → API → *Create New Token*; place at `~/.kaggle/kaggle.json`. Open each dataset page once in a browser and accept its terms, or the download 403s: [Resume Dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset), [LinkedIn Job Postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) |
| **Ollama**, locally | Runs Phi-3-mini for local dev/demo, free | [ollama.com](https://ollama.com) → `ollama pull phi3:mini` |
| **Hugging Face** — *no account needed* | `sentence-transformers` downloads `BAAI/bge-small-en-v1.5` anonymously from the Hub the first time `USE_EMBEDDINGS=true` runs, for the optional semantic-similarity sub-score. Only needed if you want that sub-score; everything else works without it | nothing to sign up for, just network access on first run |
| **A hosted LLM API key**, only for the public Render deployment | Render's web services have no persistent disk/GPU, so Ollama can't live there; the API instead talks to any OpenAI-compatible endpoint | A free key from [Groq](https://console.groq.com) (fast, generous free tier, default in `render.yaml`), or Together.ai / Fireworks / OpenRouter |
| **Adzuna app id/key** — *optional* | A second live-job source besides Remotive (which needs no key) | Free tier at [developer.adzuna.com](https://developer.adzuna.com) |
| **Langfuse keys** — *optional* | Hosted trace viewer for the agent's tool calls, for the DoD-3 screenshot | Free tier at [cloud.langfuse.com](https://cloud.langfuse.com), or self-host via `docker compose` |
| **A Render account** | To deploy the public demo (see below) | [render.com](https://render.com), free to create |
| **GitHub repo** | Render's Blueprint deploys from a connected repo; CI needs one too | push this project to GitHub |

Nothing else is required. The core agent, scoring, API, tests and UI all run with just Python,
Node and (for real LLM output) Ollama — `OFFLINE_MODE=true` even removes that last dependency for
CI and for working on everything except the two LLM-touching steps.

## Deploying to Render

Render's standard web services have **no persistent disk and no GPU**, so self-hosting Ollama
there the way `docker-compose.yml` does locally isn't practical. `render.yaml` instead deploys:

1. **matchwright-api** — the same `Dockerfile`, with `LLM_PROVIDER=openai_compatible` pointed at a
   hosted small/fast model (Groq's `llama-3.1-8b-instant` by default — swap in `render.yaml` for
   Together/Fireworks/OpenRouter/etc., any OpenAI-compatible `/chat/completions` endpoint works).
   `app/llm/provider.py` is the only place that cares which provider is active.
2. **matchwright-web** — the nginx-served React build, proxying `/api/*` to the API service.

```bash
# 1. push this repo to GitHub
# 2. Render dashboard -> New -> Blueprint -> select the repo (reads render.yaml)
# 3. after the first deploy, set the secret env vars Render prompts for:
#    matchwright-api:  OPENAI_COMPATIBLE_API_KEY, API_KEY
#    matchwright-web:  API_UPSTREAM (= matchwright-api's https://...onrender.com URL), API_KEY (same value)
```

**If you'd rather keep real local Phi-3-mini for the public demo**, run Ollama yourself (a small
always-on VM, or your own machine) and point Render's `matchwright-api` at it instead:
set `LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL=https://<your-ollama-host>` (put it behind a reverse
proxy with TLS and basic auth — never expose Ollama's bare API to the internet unauthenticated).
The cheapest zero-infrastructure alternative for a short review window is `cloudflared tunnel` from
your own machine (see `make docker-up` + the tunnel command further down) instead of Render at all.

Either path works with every feature in this README, including the live knowledge graph — it's
pure application logic, not tied to which LLM backend is active.

## Data pipeline (DoD 1)

```bash
make data            # downloads both Kaggle datasets, cleans, redacts, sections, chunks, splits
make data-small       # same, with a 500-row JD sample for a fast first run
```
Prints a stage-by-stage row-count table, a category × split crosstab, and a per-section chunk
count, and writes `data/processed/*.parquet` + `samples/chunks_sample.json`
(3 resume chunks + 3 JD chunks with `doc_id`, `section`, `chunk_idx`, `char_span`, `text`).
Paste that output here before submitting:

```
<paste `make data` output>
```

Before/after cleaning example:
```
<paste one raw Resume_str row and its cleaned+redacted output>
```

## Model check (DoD 2)

```bash
make smoke
```
```
<paste output: 3 x [OK] lines with timings>
```

## Agent trace (DoD 3)

```bash
make pairs    # fill in samples/pairs.yaml with real doc_ids first (see below)
```
Writes `reports/pairs.md`: 5 scored pairs, each with 3 justifications and its full tool trace.

Pick demo ids:
```python
import pandas as pd
r = pd.read_parquet("data/processed/resumes.parquet")
j = pd.read_parquet("data/processed/jds.parquet")
print(r[r.category == "INFORMATION-TECHNOLOGY"].sample(5, random_state=1)[["doc_id", "text"]])
print(j[j.title.str.contains("Data Scientist", case=False)][["doc_id", "title", "company_name"]].head())
```
Save a live DevOps JD for pair 2:
```bash
python -c "from app.data.live_jobs import remotive; import pathlib; j=remotive('devops',1)[0]; \
pathlib.Path('samples/jds').mkdir(parents=True, exist_ok=True); \
pathlib.Path('samples/jds/devops_remotive.txt').write_text(j['text'])"
```

```
<paste reports/pairs.md table + one Langfuse trace screenshot>
```

## API (DoD 4)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | model/provider status |
| GET | `/ready` | 200 only once the model is actually loaded |
| POST | `/v1/match` | score one resume against one JD (JSON body) — the graded agentic path |
| POST | `/v1/match/upload` | same, with the resume as an uploaded PDF/DOCX/TXT |
| **POST** | **`/v1/match/stream`** | **new** — NDJSON stream of the live knowledge-graph trace |
| **POST** | **`/v1/match/stream/upload`** | same, with an uploaded resume file |
| POST | `/v1/extract` | run extraction alone (debugging/inspection) |
| POST | `/v1/rank` | score up to 20 resumes against one JD |
| GET | `/v1/jobs/search` | live job postings (Remotive/Adzuna) |
| GET | `/v1/match/{id}` | fetch a previously computed result, incl. its knowledge graph |

```bash
make run                         # http://localhost:8000/docs
curl -s localhost:8000/health | python -m json.tool
curl -s -X POST localhost:8000/v1/match -H "X-API-Key: change-me" -H "Content-Type: application/json" \
  -d @samples/request_strong.json | python -m json.tool
# live trace, one JSON line per agent step:
curl -s -N -X POST localhost:8000/v1/match/stream -H "X-API-Key: change-me" -H "Content-Type: application/json" \
  -d @samples/request_strong.json
```

Postman collection + environment in `/postman`; Newman HTML report in `/reports` (`make newman`).

```
<paste Postman Runner screenshot: all tests green>
```

## Sample queries (real outputs)

```
<paste 3 real JSON responses: strong / partial / weak>
```

## Failure case and fallback (DoD 5)

Non-resume input → `status: insufficient_information`, no score, clear message, no 500. Full list
with detection logic and the test that proves each one in `docs/failure_cases.md`.

## Evaluation

```bash
make eval   # reports/eval.md: Spearman + NDCG@5 vs human ratings, vs a TF-IDF baseline
make bias   # reports/bias.md: counterfactual fairness (name/pronoun swap), max delta <= 2
```
```
<paste reports/eval.md and reports/bias.md>
```

## Running the tests

```bash
make test                                        # offline, no Ollama needed: 24/24 pass as shipped
OFFLINE_MODE=false pytest tests/test_api.py -k contract   # with Ollama running, exercises the real agent
cd frontend && npm test && npm run build         # 10/10 pass, typechecks, builds as shipped
```

## Limitations

Kaggle resumes are template-based and may not represent your real applicant pool. Phi-3-mini's 4K
context means long documents are chunked (`MAX_CHUNKS_PER_DOC`), so a skill mentioned only once in
an unseen chunk can be missed. CPU inference is slow; the hosted Render deployment trades local
privacy for Groq-scale latency. English only. See `MODEL_CARD.md` for the full card.

## Responsible use

PII (emails, phone numbers, URLs) is redacted before any text reaches an LLM, local or hosted.
Every match is logged with input hashes, the model used and the scoring weights
(`app/core/store.py`), so a result can be audited later — the requirement ledger and the knowledge
graph are deliberately literal about what matched and what didn't, for exactly that reason. The
tool never auto-rejects anyone; see `MODEL_CARD.md`.

## Troubleshooting

See [`docs/troubleshooting.md`](docs/troubleshooting.md).
