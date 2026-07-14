"""Configuration centralisee de PRISME. Toutes les variables viennent de l'environnement."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"

    gemini_api_key: str = ""
    mistral_api_key: str = ""

    gemini_model: str = "gemini-2.5-flash"
    mistral_model: str = "mistral-small-latest"

    supabase_url: str = ""
    supabase_service_key: str = ""

    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
