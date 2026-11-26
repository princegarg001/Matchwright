"""FastAPI microservice. Run: uvicorn app.api.main:app --reload"""
import logging
import time
import uuid

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.agent.executor import run_match
from app.agent.kg_stream import stream_match
from app.api.parsing import file_to_text
from app.core import store
from app.core.config import settings
from app.core.models import MatchResult
from app.data.redact import redact
from app.llm.provider import model_status
from app.tools.extract import extract_profile, normalize_profile

logging.basicConfig(level=logging.INFO, format='{"t":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}')
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Resume-JD Matcher", version="1.0.0",
              description="Agentic resume to job description matching on a small language model. "
                          "Decision support only.")
app.state.limiter = limiter
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_methods=["GET", "POST"], allow_headers=["*"])

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except Exception:  # metrics are optional
    pass


# ---------- errors: one consistent shape ----------
def _err(status: int, code: str, message: str, hint: str = "") -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "hint": hint}})


@app.exception_handler(HTTPException)
async def http_exc(_: Request, exc: HTTPException):
    return _err(exc.status_code, f"http_{exc.status_code}", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exc(_: Request, exc: RequestValidationError):
    return _err(422, "validation_error", "Request body is invalid", str(exc.errors()[:3]))


@app.exception_handler(RateLimitExceeded)
async def rate_exc(_: Request, exc: RateLimitExceeded):
    return _err(429, "rate_limited", "Too many requests", str(exc.detail))


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    t0 = time.time()
    resp = await call_next(request)
    resp.headers["x-request-id"] = rid
    logging.info("rid=%s %s %s %s %dms", rid, request.method, request.url.path, resp.status_code,
                 int((time.time() - t0) * 1000))
    return resp


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(401, "Missing or invalid X-API-Key header")


# ---------- schemas ----------
class MatchOptions(BaseModel):
    return_trace: bool = False
    use_agent: bool | None = None
    use_cache: bool = True


class MatchRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=60_000)
    jd_text: str = Field(min_length=1, max_length=60_000)
    options: MatchOptions = MatchOptions()


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=60_000)
    doc_type: str = Field(pattern="^(resume|jd)$")


class RankResume(BaseModel):
    id: str
    text: str = Field(min_length=1, max_length=60_000)


class RankRequest(BaseModel):
    jd_text: str = Field(min_length=1, max_length=60_000)
    resumes: list[RankResume] = Field(min_length=1, max_length=20)


# ---------- routes ----------
@app.get("/health")
def health():
    return {"status": "ok", "llm": model_status(), "offline_mode": settings.offline_mode,
            "agent": settings.use_agent}


@app.get("/ready")
def ready():
    st = model_status()
    if not settings.offline_mode and not st.get("loaded"):
        raise HTTPException(503, f"Model {settings.llm_model} not loaded")
    return {"ready": True}


def _do_match(resume_text: str, jd_text: str, opts: MatchOptions) -> MatchResult:
    resume_text, jd_text = redact(resume_text), redact(jd_text)
    if opts.use_cache and not opts.return_trace:
        cached = store.find_cached(resume_text, jd_text)
        if cached:
            return MatchResult(**{**cached, "mode": cached.get("mode", "") + "+cache"})
    res = run_match(resume_text, jd_text, use_agent=opts.use_agent, return_trace=True)
    store.save(res.match_id, resume_text, jd_text, res.model_dump())
    if not opts.return_trace:
        res.trace = []
    return res


@app.post("/v1/match", response_model=MatchResult, dependencies=[Depends(require_key)])
@limiter.limit("30/minute")
def match(request: Request, body: MatchRequest):
    return _do_match(body.resume_text, body.jd_text, body.options)


@app.post("/v1/match/upload", response_model=MatchResult, dependencies=[Depends(require_key)])
@limiter.limit("10/minute")
async def match_upload(request: Request, resume: UploadFile = File(...), jd_text: str = Form(...)):
    text = await file_to_text(resume, settings.max_upload_mb)
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(_do_match, text, jd_text, MatchOptions())


def _ndjson(resume_text: str, jd_text: str):
    """One NDJSON line per agent step, so the frontend's knowledge-graph view can render the
    steps as they really happen. A plain sync generator: Starlette iterates it in a worker
    thread (`iterate_in_threadpool`) so it never blocks the event loop."""
    for event in stream_match(resume_text, jd_text):
        yield (event.model_dump_json() + "\n").encode()


@app.post("/v1/match/stream", dependencies=[Depends(require_key)])
@limiter.limit("20/minute")
def match_stream(request: Request, body: MatchRequest):
    """Newline-delimited JSON stream of KGEvent: the live knowledge-graph trace behind the
    'View knowledge graph' button. Each line is one agent step with only its new nodes/edges."""
    resume_text, jd_text = redact(body.resume_text), redact(body.jd_text)
    return StreamingResponse(_ndjson(resume_text, jd_text), media_type="application/x-ndjson")


@app.post("/v1/match/stream/upload", dependencies=[Depends(require_key)])
@limiter.limit("10/minute")
async def match_stream_upload(request: Request, resume: UploadFile = File(...), jd_text: str = Form(...)):
    text = redact(await file_to_text(resume, settings.max_upload_mb))
    return StreamingResponse(_ndjson(text, redact(jd_text)), media_type="application/x-ndjson")


@app.post("/v1/extract", dependencies=[Depends(require_key)])
@limiter.limit("30/minute")
def extract(request: Request, body: ExtractRequest):
    p = normalize_profile(extract_profile(redact(body.text), body.doc_type))
    return p.model_dump(exclude={"text"})


@app.post("/v1/rank", dependencies=[Depends(require_key)])
@limiter.limit("5/minute")
def rank(request: Request, body: RankRequest):
    rows = []
    for r in body.resumes:
        res = _do_match(r.text, body.jd_text, MatchOptions())
        rows.append({"id": r.id, "score": res.score, "band": res.band, "status": res.status,
                     "match_id": res.match_id, "justifications": res.justifications})
    rows.sort(key=lambda x: (x["score"] is not None, x["score"] or 0), reverse=True)
    return {"jd_chars": len(body.jd_text), "ranked": rows}


@app.get("/v1/jobs/search", dependencies=[Depends(require_key)])
def jobs_search(q: str = "", source: str = "remotive", limit: int = 10):
    from app.data import live_jobs
    try:
        return {
            "source": source,
            "adzuna_configured": bool(settings.adzuna_app_id and settings.adzuna_app_key),
            "results": live_jobs.search(q, source, min(limit, 25)),
        }
    except Exception as e:
        raise HTTPException(502, f"Job source unavailable: {e}") from e


@app.get("/v1/match/{match_id}", dependencies=[Depends(require_key)])
def get_match(match_id: str):
    body = store.get(match_id)
    if not body:
        raise HTTPException(404, "match_id not found")
    return body
