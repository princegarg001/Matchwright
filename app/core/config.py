"""Central settings, read from environment variables or .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Default provider is the hosted Groq path: ~2-3s per call and noticeably more capable
    # extraction than phi3:mini (measured directly: clean skill names, correct years/evidence)
    # vs. 30-90s+ per call on CPU-only Ollama. Set LLM_PROVIDER=ollama for fully local/offline use
    # (privacy, no API key, DoD's original local-Phi-3-mini path) when speed isn't the priority.
    llm_provider: str = "openai_compatible"  # "openai_compatible" (hosted, fast) or "ollama" (local)
    llm_model: str = "phi3:mini"
    ollama_base_url: str = "http://localhost:11434"
    num_ctx: int = 4096
    llm_timeout_s: int = 120

    openai_compatible_base_url: str = "https://api.groq.com/openai/v1"
    openai_compatible_model: str = "openai/gpt-oss-120b"
    openai_compatible_api_key: str = ""
    # Measured directly against Groq: gpt-oss-120b gives excellent structured-JSON extraction but
    # gets stuck re-doing step 1 of the text ReAct loop forever (it doesn't progress on its own
    # Observations); qwen3.8-27b is the reverse (perfect ReAct, unreliable json_schema output). So
    # the agent's own LLM is configured separately from the one chat_json/chat_text use.
    openai_compatible_agent_model: str = "qwen/qwen3.8-27b"

    offline_mode: bool = False
    use_agent: bool = True
    use_embeddings: bool = True
    use_skillner: bool = False
    embed_model: str = "BAAI/bge-small-en-v1.5"

    api_key: str = "change-me"
    cors_origins: str = "http://localhost:5173"  # comma-separated; only needed when not using the proxy
    data_dir: str = "data"
    db_path: str = "data/results.db"
    aliases_path: str = "config/aliases.yaml"
    max_upload_mb: float = 2.0
    max_chunks_per_doc: int = 6

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"

    langfuse_enabled: bool = False
    # Passed explicitly to langfuse's CallbackHandler (see app/agent/executor.py), rather than
    # relying on it reading os.environ directly: pydantic-settings loads .env into these fields,
    # not into the process environment, so langfuse would otherwise never see them.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # New: live knowledge-graph trace during /v1/match/stream
    kg_trace_enabled: bool = True


settings = Settings()
