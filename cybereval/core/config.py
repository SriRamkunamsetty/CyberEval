"""
CyberEval - Core Configuration
Follows strict production and security guidelines:
- Multi-tiered secret resolution (Env -> file -> cryptographically secure ephemeral secret)
- Safe host/port defaults (binds to 127.0.0.1 for local testing)
- Database URI configuration (SQLite with aiosqlite for local dev, PostgreSQL for production)
"""

import os
import secrets
import logging
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

logger = logging.getLogger("cybereval.config")

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_secure_jwt_secret() -> str:
    """Resolve secret from environment, local secret file, or generate secure random token."""
    env_secret = os.getenv("CYBEREVAL_SECRET_KEY")
    if env_secret:
        return env_secret
    secret_file = BASE_DIR / ".secret_key"
    if secret_file.exists():
        try:
            return secret_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    # Generate ephemeral cryptographically secure secret
    logger.warning("Generating ephemeral secret for CyberEval session. Instance-isolated.")
    generated = secrets.token_hex(32)
    try:
        secret_file.write_text(generated, encoding="utf-8")
    except Exception:
        pass
    return generated


class Settings(BaseSettings):
    PROJECT_NAME: str = "CyberEval"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = get_secure_jwt_secret()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Server network settings
    HOST: str = "127.0.0.1"
    PORT: int = 8080
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{BASE_DIR.as_posix()}/cybereval.db"
    )
    
    # Benchmark settings
    DEFAULT_DATASET_NAME: str = "cybereval-core-v1"
    DATASET_STORAGE_PATH: str = str(BASE_DIR / "cybereval" / "benchmark" / "scenarios")
    
    # Evaluation execution limits
    MAX_CONCURRENT_EVALS: int = 5
    EVALUATION_TIMEOUT_SECONDS: int = 120
    
    # Model API Keys (optional; fallback to built-in deterministic baseline/flawed mock models)
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
