"""Single place that talks to the model. Swap provider via env without touching callers.

Two providers are supported:
- "ollama" (default): local Phi-3-mini via Ollama. Free, private, needs the model pulled locally.
- "openai_compatible": any OpenAI-compatible /chat/completions endpoint (Groq, Together, Fireworks,
  OpenRouter, ...). Used for the hosted Render deployment, where self-hosting Ollama is impractical
  on the free/standard plan (no persistent disk / GPU). Both paths go through the same chat_json /
  chat_text / get_agent_llm functions, so nothing above this layer needs to know which one is active.
"""
import json
import logging
import time
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.telemetry import safe_update, trace_span

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    pass


def _with_backoff(fn, attempts: int = 3, base_delay: float = 1.5):
    """Hosted providers (Groq especially, since reasoning models burn tokens-per-minute fast)
    return transient connection/429 errors under normal load. Retrying a couple of times with
    exponential backoff is the difference between a flaky demo and a working one; only the last
    attempt's error is surfaced, wrapped as LLMUnavailable."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # connection errors, timeouts, rate limits
            last = e
            if i < attempts - 1:
                log.warning("LLM call failed (attempt %d/%d): %s — retrying", i + 1, attempts, e)
                time.sleep(base_delay * (2**i))
    raise LLMUnavailable(str(last)) from last


@lru_cache
def _ollama_client():
    import ollama
    return ollama.Client(host=settings.ollama_base_url, timeout=settings.llm_timeout_s)


@lru_cache
def _openai_client():
    from openai import OpenAI
    return OpenAI(base_url=settings.openai_compatible_base_url, api_key=settings.openai_compatible_api_key or "none")


def _options() -> dict:
    return {"temperature": 0, "num_ctx": settings.num_ctx, "seed": 7}


def _chat_json_ollama(messages: list[dict], schema: type[T]) -> str:
    resp = _ollama_client().chat(model=settings.llm_model, messages=messages,
                                 format=schema.model_json_schema(), options=_options())
    return resp.message.content


def _chat_json_openai(messages: list[dict], schema: type[T]) -> str:
    json_schema = {"name": schema.__name__, "schema": schema.model_json_schema()}
    resp = _openai_client().chat.completions.create(
        model=settings.openai_compatible_model, messages=messages, temperature=0,
        response_format={"type": "json_schema", "json_schema": json_schema},
    )
    return resp.choices[0].message.content


def _active_model() -> str:
    if settings.llm_provider == "openai_compatible":
        return settings.openai_compatible_model
    return settings.llm_model


def chat_json(system: str, user: str, schema: type[T], retries: int = 1) -> T:
    """Constrained JSON generation validated by Pydantic, with one corrective retry."""
    if settings.offline_mode:
        raise LLMUnavailable("offline mode")
    active_model = _active_model()
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user + "\n\nJSON schema:\n" + json.dumps(schema.model_json_schema())}]
    last_err = None
    with trace_span("chat_json", as_type="generation", model=active_model,
                    input={"schema": schema.__name__, "user": user[:1200]}) as gen:
        for _ in range(retries + 1):
            try:
                if settings.llm_provider == "openai_compatible":
                    content = _with_backoff(lambda: _chat_json_openai(messages, schema))
                else:
                    content = _with_backoff(lambda: _chat_json_ollama(messages, schema))
                parsed = schema.model_validate_json(content)
                safe_update(gen, output=parsed.model_dump())
                return parsed
            except ValidationError as e:
                last_err = e
                err_msg = f"Your JSON was invalid: {e.errors()[:3]}. Return valid JSON."
                messages.append({"role": "user", "content": err_msg})
        safe_update(gen, level="ERROR", status_message=str(last_err))
    raise LLMUnavailable(f"invalid JSON after retries: {last_err}")


def chat_text(system: str, user: str) -> str:
    if settings.offline_mode:
        raise LLMUnavailable("offline mode")
    active_model = _active_model()
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _call() -> str:
        if settings.llm_provider == "openai_compatible":
            resp = _openai_client().chat.completions.create(
                model=settings.openai_compatible_model, temperature=0, messages=msgs,
            )
            return (resp.choices[0].message.content or "").strip()
        resp = _ollama_client().chat(model=settings.llm_model, options=_options(), messages=msgs)
        return resp.message.content.strip()

    with trace_span("chat_text", as_type="generation", model=active_model, input={"user": user[:1200]}) as gen:
        out = _with_backoff(_call)
        safe_update(gen, output=out[:1200])
        return out


def get_agent_llm():
    """LangChain chat model for the text ReAct agent specifically — see the note on
    openai_compatible_agent_model in app/core/config.py for why this can differ from the model
    chat_json/chat_text use."""
    if settings.llm_provider == "openai_compatible":
        from langchain_openai import ChatOpenAI
        model = settings.openai_compatible_agent_model or settings.openai_compatible_model
        return ChatOpenAI(model=model, base_url=settings.openai_compatible_base_url,
                          api_key=settings.openai_compatible_api_key or "none", temperature=0)
    from langchain_ollama import ChatOllama
    return ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url,
                      temperature=0, num_ctx=settings.num_ctx)


def model_status() -> dict:
    if settings.offline_mode:
        return {"provider": "offline", "model": None, "loaded": False}
    if settings.llm_provider == "openai_compatible":
        loaded = bool(settings.openai_compatible_api_key)
        return {"provider": "openai_compatible", "model": settings.openai_compatible_model, "loaded": loaded,
                "available": [settings.openai_compatible_model] if loaded else []}
    try:
        models = _ollama_client().list().models
        names = [getattr(m, "model", None) or getattr(m, "name", "") for m in models]
        return {"provider": settings.llm_provider, "model": settings.llm_model,
                "loaded": any(n.startswith(settings.llm_model.split(":")[0]) for n in names), "available": names}
    except Exception as e:
        return {"provider": settings.llm_provider, "model": settings.llm_model, "loaded": False, "error": str(e)}
