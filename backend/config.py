"""Centralized configuration loader for environment-driven runtime settings."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_sql_model: str = os.getenv("GROQ_SQL_MODEL", "llama-3.3-70b-versatile")
    groq_insight_model: str = os.getenv("GROQ_INSIGHT_MODEL", "llama-3.3-70b-versatile")
    app_title: str = os.getenv("APP_TITLE", "AI Business Intelligence Copilot")
    sqlite_temp_prefix: str = os.getenv("SQLITE_TEMP_PREFIX", "sql_analyst_")
    sample_preview_rows: int = int(os.getenv("SAMPLE_PREVIEW_ROWS", "5"))
    max_sql_retries: int = int(os.getenv("MAX_SQL_RETRIES", "2"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    log_file: str = os.getenv("LOG_FILE", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
