"""ui_testing_software configuration."""

import os


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "ui_testing_software")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))


settings = Settings()
