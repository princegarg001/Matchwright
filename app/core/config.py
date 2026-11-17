"""Central settings, read from environment variables or .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "ollama"  # "ollama" (local) or "openai_compatible" (hosted, for Render)
    llm_model: str = "phi3:mini"
    ollama_base_url: str = "http://localhost:11434"
    num_ctx: int = 4096
    llm_timeout_s: int = 120

    # Hosted fallback so the service can run on Render without self-hosting Ollama.
    openai_compatible_base_url: str = "https://api.groq.com/openai/v1"
    openai_compatible_model: str = "llama-3.1-8b-instant"
    openai_compatible_api_key: str = ""

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

    # New: live knowledge-graph trace during /v1/match/stream
    kg_trace_enabled: bool = True


settings = Settings()
