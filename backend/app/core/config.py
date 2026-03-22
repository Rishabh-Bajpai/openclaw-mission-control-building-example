from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "OpenClaw Mission Control"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./mission_control.db"

    HOST: str = "0.0.0.0"
    PORT: int = 8002

    OPENCLAW_GATEWAY_TOKEN: Optional[str] = None
    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18789"

    LLM_API_URL: str = "https://api.openai.com/v1/chat/completions"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4"

    AGENTS_DIR: str = "agents"
    HEARTBEAT_INTERVAL_MINUTES: int = 15
    STANDUP_TIME: str = "08:00"

    class Config:
        env_file = ".env"


settings = Settings()
