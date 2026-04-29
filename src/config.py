import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str
    DB_URL: str
    RUN_MODE: str = "polling"
    WEBHOOK_URL: str = ""
    ADMIN_USER_IDS: list[int] = []
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __post_init__(self):
        if self.ADMIN_USER_IDS and isinstance(self.ADMIN_USER_IDS, str):
            self.ADMIN_USER_IDS = [int(x.strip()) for x in self.ADMIN_USER_IDS.split(",") if x.strip()]

settings = Settings()