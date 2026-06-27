import os
import logging
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables.

    Centralizes all configuration for database, authentication, and external
    API keys in one place. Using a class-based approach allows easy testing
    by overriding attributes via dependency injection.

    Why class over module-level constants:
        - Testable: can override settings in unit tests
        - Self-documenting: all config lives in one place
        - Type-safe: mypy catches missing attributes
    """
    PROJECT_NAME: str = "AI Interview Preparation Agent"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./interview_agent.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkeyforinterviewagent")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
