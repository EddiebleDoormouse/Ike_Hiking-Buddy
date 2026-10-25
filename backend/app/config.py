"""Application settings and shared planning thresholds."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Load application settings from the repository's .env file."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    GEMINI_API_KEY: str | None = None
    MONGODB_URI: str | None = None
    MONGODB_DB: str = "hikingbuddy"
    HB_DATA_DIR: str = "~/hb-data"
    PLANTNET_API_KEY: str | None = None
    KINDWISE_MUSHROOM_API_KEY: str | None = None
    MEDIA_MODEL: str = "gemini-3.8-flash"
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    def allowed_origins_list(self) -> list[str]:
        """Return configured CORS origins, excluding blank entries."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()

CONFIRM_CONF = 0.7
CONFIRM_GBIF = 5
PLAUSIBLE_CONF = 0.4
SPECIALIST_AGREE_MIN = 0.3
SPECIALIST_DISAGREE_MIN = 0.5
MAX_GUST_KMH = 50
MAX_PRECIP_PROB = 70
SUNSET_BUFFER_MIN = 60
