"""Application configuration.

All runtime settings are derived from environment variables so that the
backend can run in development, test, and production without code changes.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Comma-separated list of allowed browser origins (no wildcard with cookies).
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- LLM backend ---
    # "hf" (Hugging Face hosted inference, default).
    LLM_PROVIDER: str = "hf"

    # --- Hugging Face hosted inference ---
    HF_TOKEN: str = ""
    HF_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    HF_BASE_URL: str = ""  # optional: your own inference endpoint

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./data/openresearch.db"

    # --- Vector store ---
    VECTOR_DB_PATH: str = "./data/chroma"

    # --- Research loop ---
    MAX_RESEARCH_ITERATIONS: int = 3
    MAX_SEARCH_RESULTS: int = 5
    MAX_REPORT_REVISIONS: int = 2

    # --- Search provider ---
    SEARCH_PROVIDER: str = "duckduckgo"  # "duckduckgo" | "tavily"
    TAVILY_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
