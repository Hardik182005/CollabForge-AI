from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    PORT: int = 8001
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    PUBLIC_APP_URL: str = ""

    # ── LLM / media providers ────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # ── Anakin ───────────────────────────────────────────────────────────
    ANAKIN_API_KEY: str = ""
    ANAKIN_API_KEY_2: str = ""   # fallback key: used when the primary is credit-exhausted
    ANAKIN_API_BASE_URL: str = "https://api.anakin.io"
    ANAKIN_JOB_TIMEOUT_SECONDS: int = 120
    ANAKIN_CACHE_TTL_SECONDS: int = 3600
    ANAKIN_MAX_CREDITS_PER_REQUEST: int = 25

    # ── Optional data providers ──────────────────────────────────────────
    YOUTUBE_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    RAPIDAPI_KEY: str = ""
    RAPIDAPI_INSTAGRAM_HOST: str = "instagram-scraper-api2.p.rapidapi.com"

    # ── AWS / persistence ────────────────────────────────────────────────
    AWS_REGION: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_DYNAMODB_TABLE: str = ""
    AWS_CLOUDFRONT_DISTRIBUTION_ID: str = ""
    DATABASE_MODE: str = "local"  # local | dynamodb
    LOCAL_STORAGE_PATH: str = "./data/local"

    # legacy compat (kept so old envs don't crash)
    CORS_ORIGINS: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def cors_origins() -> list:
    raw = settings.FRONTEND_ORIGINS or settings.CORS_ORIGINS or ""
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or ["http://localhost:3000"]


def validate_startup() -> dict:
    """Report provider availability. Missing optional providers disable
    capabilities; nothing crashes. Production additionally requires the
    core research/generation providers."""
    status = {
        "openai": bool(settings.OPENAI_API_KEY),
        "groq": bool(settings.GROQ_API_KEY) and not settings.GROQ_API_KEY.startswith("gsk_..."),
        "gemini": bool(settings.GEMINI_API_KEY),
        "elevenlabs": bool(settings.ELEVENLABS_API_KEY),
        "anakin": bool(settings.ANAKIN_API_KEY),
        "youtube_api": bool(settings.YOUTUBE_API_KEY),
        "dynamodb": settings.DATABASE_MODE == "dynamodb" and bool(settings.AWS_DYNAMODB_TABLE),
    }
    if settings.APP_ENV == "production":
        missing = [k for k in ("openai", "anakin") if not status[k]]
        if missing:
            raise RuntimeError(
                f"Production startup blocked — required providers not configured: {', '.join(missing)}"
            )
    return status
