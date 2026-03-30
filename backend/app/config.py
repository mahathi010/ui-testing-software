"""ui_testing_software configuration."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "ui_testing_software"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    APP_DEBUG: bool = False

    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/ui_testing_software"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "changeme"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    def get_cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
