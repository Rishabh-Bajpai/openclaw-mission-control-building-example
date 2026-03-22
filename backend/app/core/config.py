"""
Configuration Management using Pydantic Settings

This module handles all application configuration through environment variables.
It uses Pydantic Settings to automatically load values from .env files and
provide type validation.

Environment Configuration:
-------------------------
Configuration is loaded from environment variables with fallbacks to defaults.
Create a .env file in the backend directory (see .env.example for template).

Required Variables:
- OPENCLAW_GATEWAY_TOKEN: Authentication token for OpenClaw Gateway
- LLM_API_KEY: API key for LLM service (OpenAI compatible)

Optional Variables (have defaults):
- DATABASE_URL: Database connection string
- OPENCLAW_GATEWAY_URL: WebSocket URL for OpenClaw
- LLM_API_URL: LLM API endpoint
- LLM_MODEL: Model name (e.g., gpt-4)
- HOST/PORT: Server binding

Example .env file:
------------------
```
# Database
DATABASE_URL=sqlite+aiosqlite:///./mission_control.db

# OpenClaw Gateway
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789
OPENCLAW_GATEWAY_TOKEN=your_token_here

# LLM Configuration
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4

# Server
HOST=0.0.0.0
PORT=8002
```

Usage:
------
```python
from app.core.config import settings

# Access configuration
database_url = settings.DATABASE_URL
api_key = settings.LLM_API_KEY

# Check if optional value is set
if settings.OPENCLAW_GATEWAY_TOKEN:
    # Connect to gateway
    pass
```

Extension Points:
-----------------
To add new configuration:

1. Add field to Settings class with type and default
2. Add to .env.example with description
3. Access via settings.YOUR_NEW_FIELD

Example:
```python
class Settings(BaseSettings):
    # ... existing fields ...

    # New configuration
    CUSTOM_WEBHOOK_URL: Optional[str] = None
    MAX_AGENTS_PER_TEAM: int = 10
    ENABLE_ADVANCED_FEATURES: bool = False
```

Security Notes:
---------------
- Never commit .env files with real values to version control
- Keep secrets (API keys, tokens) in environment variables only
- The .env.example file shows structure without real values
- In production, use proper secret management (AWS Secrets Manager, etc.)

Type Safety:
------------
All configuration values are type-checked at startup. If an environment
variable has an invalid type (e.g., string for an int field), Pydantic
will raise a validation error on application startup.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with environment variable loading.

    This class defines all configurable parameters for the application.
    Values are loaded from environment variables, with sensible defaults
    for development.

    Attributes:
        APP_NAME: Application display name
        DEBUG: Enable debug mode (extra logging, auto-reload)
        DATABASE_URL: SQLAlchemy database URL
        HOST: Server bind address
        PORT: Server port
        OPENCLAW_GATEWAY_TOKEN: Authentication token for OpenClaw
        OPENCLAW_GATEWAY_URL: OpenClaw WebSocket endpoint
        LLM_API_URL: LLM API endpoint URL
        LLM_API_KEY: LLM API authentication key
        LLM_MODEL: LLM model identifier
        AGENTS_DIR: Directory for agent workspaces
        HEARTBEAT_INTERVAL_MINUTES: Default agent heartbeat frequency
        STANDUP_TIME: Default standup meeting time (HH:MM)

    Example:
        >>> from app.core.config import settings
        >>> print(settings.APP_NAME)
        'OpenClaw Mission Control'
        >>> print(settings.PORT)
        8002
    """

    # Application metadata
    APP_NAME: str = "OpenClaw Mission Control"
    """Display name for the application."""

    DEBUG: bool = True
    """
    Debug mode flag.
    
    When True:
    - Enables detailed error messages
    - SQLAlchemy echoes SQL queries
    - FastAPI auto-reloads on code changes
    
    Set to False in production.
    """

    # Database configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./mission_control.db"
    """
    SQLAlchemy database connection URL.
    
    Supports:
    - SQLite: sqlite:///./mission_control.db
    - PostgreSQL: postgresql+asyncpg://user:pass@localhost/dbname
    - MySQL: mysql+aiomysql://user:pass@localhost/dbname
    
    For development, SQLite is fine. For production, use PostgreSQL.
    """

    # Server configuration
    HOST: str = "0.0.0.0"
    """Server bind address. Use 0.0.0.0 to accept all interfaces."""

    PORT: int = 8002
    """Server port number. Change if port is already in use."""

    # OpenClaw Gateway configuration
    OPENCLAW_GATEWAY_TOKEN: Optional[str] = None
    """
    Authentication token for OpenClaw Gateway.
    
    Required for connecting to OpenClaw. Get this from your OpenClaw
    installation or configuration. Keep this secret!
    
    Example: "37d476b085dca4d9a17adc2dd1607b8dbb79f2b7a7a4529d"
    """

    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18789"
    """
    WebSocket URL for OpenClaw Gateway.
    
    Default assumes OpenClaw is running locally on port 18789.
    Change if OpenClaw is on a different host/port.
    
    Format: ws://host:port or wss://host:port (for TLS)
    """

    # LLM Service configuration
    LLM_API_URL: str = "https://api.openai.com/v1/chat/completions"
    """
    LLM API endpoint URL.
    
    Supports any OpenAI-compatible API:
    - OpenAI: https://api.openai.com/v1/chat/completions
    - Local (LM Studio): http://localhost:1234/v1/chat/completions
    - Custom: Your own API endpoint
    """

    LLM_API_KEY: Optional[str] = None
    """
    API key for LLM service authentication.
    
    Required for cloud providers (OpenAI, Anthropic, etc.).
    Not needed for local models (LM Studio, etc.).
    
    Keep this secret and never commit to version control!
    """

    LLM_MODEL: str = "gpt-4"
    """
    LLM model identifier.
    
    Examples:
    - OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
    - Local: model-name-from-lm-studio
    - Custom: your-model-name
    """

    # Agent defaults
    AGENTS_DIR: str = "agents"
    """Directory name for agent workspace storage."""

    HEARTBEAT_INTERVAL_MINUTES: int = 15
    """
    Default heartbeat frequency for new agents.
    
    How often agents wake up to check for tasks (in minutes).
    Set to 0 to disable heartbeats (manual activation only).
    """

    STANDUP_TIME: str = "08:00"
    """
    Default standup meeting time (24-hour format HH:MM).
    
    Used by the scheduler to trigger daily standup meetings.
    Agents should be active at this time.
    """

    class Config:
        """
        Pydantic configuration.

        env_file: Load environment variables from this file
        env_file_encoding: File encoding
        """

        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
# Import this to access configuration anywhere in the app
settings = Settings()
"""
Global settings instance.

Usage:
    from app.core.config import settings
    
    # Access any setting
    db_url = settings.DATABASE_URL
    token = settings.OPENCLAW_GATEWAY_TOKEN

Note: Settings are loaded once at import time. Changes to .env file
require application restart to take effect.
"""
