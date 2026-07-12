from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    YOUTUBE_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    APP_ENV: str = "development"
    PORT: int = 8001

    RUNWAY_API_KEY: str = ""
    CORS_ORIGINS: str = "*"

    # Paid Instagram data via RapidAPI (activates real IG metrics when set)
    RAPIDAPI_KEY: str = ""
    RAPIDAPI_INSTAGRAM_HOST: str = "instagram-scraper-api2.p.rapidapi.com"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
