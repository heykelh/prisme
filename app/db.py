"""Client Supabase partage. Une seule instance, creee paresseusement."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL et SUPABASE_SERVICE_KEY doivent etre definis")
    return create_client(settings.supabase_url, settings.supabase_service_key)
