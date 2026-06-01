from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openrouter_api_key: str = Field(default="")
    llm_model: str = Field(default="meta-llama/llama-3.3-70b-instruct:free")
    llm_fallback_models: str = Field(
        default="meta-llama/llama-3.1-8b-instruct:free,qwen/qwen-2.5-coder-32b-instruct:free"
    )
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2048, ge=1, le=8192)

    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8080")

    prometheus_url: str = Field(default="http://localhost:9090")
    loki_url: str = Field(default="http://localhost:3100")

    database_url: str = Field(default="postgresql://copilot:copilot@localhost:5432/copilot")
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")
    embedding_dim: int = Field(default=384)
    rag_top_k: int = Field(default=4)
    rag_similarity_threshold: float = Field(default=0.35)
    auto_ingest_runbooks: bool = Field(default=True)
    runbooks_dir: str = Field(default="./runbooks")

    k8s_api_url: str = Field(default="")
    k8s_bearer_token: str = Field(default="")
    agent_max_iterations: int = Field(default=5)

    log_level: str = Field(default="INFO")

    @property
    def fallback_models(self) -> List[str]:
        return [m.strip() for m in self.llm_fallback_models.split(",") if m.strip()]

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
