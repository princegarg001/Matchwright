"""Optional Langfuse tracing helper. Never raises when disabled or misconfigured."""
import logging
import sys
from contextlib import contextmanager
from functools import lru_cache

from app.core.config import settings

log = logging.getLogger(__name__)


@lru_cache
def get_langfuse_client():
    """Register and return the cached Langfuse client, or None when disabled/unconfigured."""
    if not (settings.langfuse_enabled and settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    from langfuse import Langfuse
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def langfuse_callbacks() -> list:
    """Return LangChain callbacks for AgentExecutor when Langfuse is enabled."""
    if not settings.langfuse_enabled:
        return []
    try:
        if get_langfuse_client() is None:
            log.warning("langfuse enabled but LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are missing")
            return []
        from langfuse.langchain import CallbackHandler
        return [CallbackHandler(public_key=settings.langfuse_public_key)]
    except Exception as e:
        log.warning("langfuse disabled: %s", e)
        return []


def safe_update(span, **kwargs) -> None:
    """Best-effort update on an active Langfuse observation."""
    if span is None:
        return
    try:
        span.update(**kwargs)
    except Exception as e:
        log.warning("langfuse span update failed: %s", e)


def flush_langfuse() -> None:
    """Flush pending Langfuse events without raising."""
    try:
        client = get_langfuse_client()
        if client is not None:
            client.flush()
    except Exception as e:
        log.warning("langfuse flush failed: %s", e)


@contextmanager
def trace_span(name: str, as_type: str = "span", flush: bool = False, **kwargs):
    """Context manager wrapping Langfuse observations safely without interfering with caller exceptions."""
    cm = None
    span = None
    client = None
    try:
        client = get_langfuse_client()
        if client is not None:
            cm = client.start_as_current_observation(name=name, as_type=as_type, **kwargs)
            span = cm.__enter__()
    except Exception as e:
        log.warning("langfuse span start failed (%s): %s", name, e)
        cm = None
        span = None
    try:
        yield span
    finally:
        if cm is not None:
            try:
                cm.__exit__(*sys.exc_info())
            except Exception as e:
                log.warning("langfuse span close failed (%s): %s", name, e)
        if flush and client is not None:
            flush_langfuse()
