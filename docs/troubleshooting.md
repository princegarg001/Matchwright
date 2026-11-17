# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'AgentExecutor' from 'langchain.agents'` | LangChain 1.x moved it | `pip install langchain-classic`; import from `langchain_classic.agents` |
| `model does not support tools` | Native tool calling with phi3 | Use the text ReAct agent in this repo (no `bind_tools`) |
| Agent loops / "Invalid Format: Missing 'Action:'" | Small model drifts from format | `handle_parsing_errors=True` (already on), keep the worked example, the fallback finishes the job; report `mode` honestly |
| Invalid JSON from extraction | Schema too large / context overflow | Keep `LLMExtraction` small, `temperature=0`, chunks ≤ 1,200 chars, `num_ctx=4096` |
| Very slow on CPU | 6 chunks × 2 docs × LLM | Lower `MAX_CHUNKS_PER_DOC` to 3, cache results, use a GPU, pre-warm before demos, or switch `LLM_PROVIDER=openai_compatible` |
| `httpx.ConnectError` to Ollama in Docker | Wrong host | `OLLAMA_BASE_URL=http://ollama:11434` inside compose; `http://localhost:11434` outside |
| Kaggle 403 | Token missing or terms not accepted | Place `kaggle.json`; open the dataset page once and accept terms |
| Sections not detected | Header styles vary | Add header words to `RESUME_HEADER_WORDS` / `JD_HEADERS`; inspect 5 raw rows |
| Score feels too high/low | Untuned weights | Fit weights on gold labels (see README "Evaluation"); adjust credits in `scoring.py` |
| `sentence-transformers` download blocked | No internet on first run | `USE_EMBEDDINGS=false` (semantic weight is renormalised automatically) |
| UI shows "API unreachable" | API not running, or wrong `API_URL` in `frontend/.env` | Start `make run`; check `curl localhost:5173/api/health` |
| UI errors with "Missing or invalid X-API-Key" | Key in `frontend/.env` (dev) or root `.env` (Docker) differs from the API's `API_KEY` | Use the same value in both; restart `npm run dev` after editing `.env` |
| Browser request cut off after 60s | nginx default timeout | Keep `proxy_read_timeout 600s` in the nginx template; lower `MAX_CHUNKS_PER_DOC` |
| Deep link like `/rank` returns 404 in production | SPA fallback missing | Keep `try_files $uri /index.html` in the nginx template |
| **Knowledge graph never appears / stays empty** | `/v1/match/stream` blocked, or a proxy buffers the whole response before forwarding it | Check `curl -N` shows lines arriving one at a time, not all at once; in nginx keep `proxy_buffering off;` on the `/api/` location (already set in `frontend/nginx/default.conf.template`); Render's edge does not buffer NDJSON either |
| Live graph freezes partway through | The browser tab lost the connection, or the resume/JD guard rejected the input mid-stream | Check the last event's `step` — `"guard"` or `"error"` means the stream ended on purpose with a `result`; read `result.message` |
| Render deploy: API returns 503 forever | `OPENAI_COMPATIBLE_API_KEY` not set, or wrong base URL for the chosen provider | Set the key in the Render dashboard (it's `sync: false` in `render.yaml` on purpose); check `/health` → `llm.loaded` |
| Render deploy: UI can't reach the API | `API_UPSTREAM` on `matchwright-web` wasn't set to the real API URL | Render Blueprint can't give nginx a full scheme+host automatically; set `API_UPSTREAM` to the API service's `https://...onrender.com` URL by hand once it's known |
