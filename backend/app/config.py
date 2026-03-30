"""ui_testing_software configuration."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "ui_testing_software"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/ui_testing_software"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
