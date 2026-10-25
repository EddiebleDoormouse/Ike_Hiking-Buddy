"""Application settings loaded from environment variables or .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings needed by the backend services."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GEMINI_API_KEY: str | None = None
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "hikingbuddy"
    MEDIA_MODEL: str = "gemini-3.8-flash"


settings = Settings()
