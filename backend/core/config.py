from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, SecretStr
import os
from dotenv import load_dotenv


class Settings(BaseModel):
    """Application configuration holder. Values are provided by `get_settings()`.

    This avoids depending on `pydantic-settings` (not present in all envs).
    """

    APP_NAME: str = "wazire"
    ENV: str = "development"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # DATABASE_URL = "postgresql+asyncpg://user:password@localhost/exam_db"
    # DATABASE_URL = "sqlite+aiosqlite:///exam_db.sqlite"
    # DATABASE_URL = "mysql+aiomysql://user:password@localhost/exam_db"
    DATABASE_URL: Optional[str] = "postgresql+asyncpg://wazire:wazire@localhost:5432/wazire"
    REDIS_URL: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None

    SECRET_KEY: Optional[SecretStr] = SecretStr("change-me-in-production")
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600

    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    REQUEST_ID_HEADERS: str = "X-Request-ID,X-Correlation-ID"

    GROQ_API_KEYS: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # Frontend origin for CORS (production-safe; overrides CORS_ORIGINS when set)
    FRONTEND_ORIGIN: Optional[str] = None

    # Kafka settings
    # Brevo (Sendinblue) transactional email settings
    BREVO_API_KEY: Optional[SecretStr] = None
    BREVO_SENDER_NAME: Optional[str] = "Wazire"
    BREVO_SENDER_EMAIL: Optional[str] = None
    # Secret used to validate incoming payment provider webhooks (HMAC-SHA256)
    PAYMENT_WEBHOOK_SECRET: Optional[SecretStr] = None

    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: Optional[str] = None
    KAFKA_TOPIC_PREFIX: Optional[str] = None
    KAFKA_USERNAME: Optional[str] = None
    KAFKA_PASSWORD: Optional[str] = None
    KAFKA_SECURITY_PROTOCOL: Optional[str] = "PLAINTEXT"
    KAFKA_SASL_MECHANISM: Optional[str] = None
    # Scheduler intervals (minutes) for the internal scheduler that publishes Kafka events
    SCHEDULER_EXAM_STATUS_UPDATE_INTERVAL: Optional[int] = None
    SCHEDULER_EMAIL_SEND_INTERVAL: Optional[int] = None
    # Frontend URL used to build verification links
    FRONTEND_URL: Optional[str] = "http://localhost:5173"

    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [s.strip() for s in self.CORS_ORIGINS.split(",") if s.strip()]
        return list(self.CORS_ORIGINS)

    def request_id_headers_list(self) -> List[str]:
        """Return `REQUEST_ID_HEADERS` as a list — accepts comma string or list."""
        if isinstance(self.REQUEST_ID_HEADERS, str):
            return [s.strip() for s in self.REQUEST_ID_HEADERS.split(",") if s.strip()]
        return list(self.REQUEST_ID_HEADERS)

    def kafka_bootstrap_list(self) -> List[str]:
        """Return `KAFKA_BOOTSTRAP_SERVERS` as a list of brokers."""
        if not self.KAFKA_BOOTSTRAP_SERVERS:
            return []
        if isinstance(self.KAFKA_BOOTSTRAP_SERVERS, str):
            return [s.strip() for s in self.KAFKA_BOOTSTRAP_SERVERS.split(",") if s.strip()]
        return list(self.KAFKA_BOOTSTRAP_SERVERS)
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> Optional[str]:
        """Return a SQLAlchemy-compatible DB URL.

        This helper will detect common schemes and normalize them to a
        SQLAlchemy-friendly form. It prefers async drivers where reasonable
        (e.g. `postgresql+asyncpg`, `sqlite+aiosqlite`, `mysql+aiomysql`).
        If the provided `DATABASE_URL` already contains an explicit driver
        (a `+` in the scheme), it will be returned unchanged.
        """
        url = self.DATABASE_URL
        if not url:
            return None

        u = url.strip()
        lower = u.lower()

        # If the scheme already specifies a driver (contains '+'), return as-is
        scheme_part = lower.split("://", 1)[0]
        if "+" in scheme_part:
            return u

        # SQLite: prefer aiosqlite for async usage
        if lower.startswith("sqlite://"):
            return u.replace("sqlite://", "sqlite+aiosqlite://", 1)

        # Postgres: normalize to postgresql+asyncpg
        if lower.startswith("postgres://"):
            return u.replace("postgres://", "postgresql+asyncpg://", 1)
        if lower.startswith("postgresql://"):
            return u.replace("postgresql://", "postgresql+asyncpg://", 1)

        # MySQL / MariaDB: prefer aiomysql / asyncmy
        if lower.startswith("mysql://"):
            return u.replace("mysql://", "mysql+aiomysql://", 1)
        if lower.startswith("mariadb://"):
            return u.replace("mariadb://", "mariadb+asyncmy://", 1)

        # Fallback: return the original URL unchanged
        return u

    def validate(self) -> None:
        """Validate configuration settings.
        
        Raises:
            ValueError: If any required configuration is missing or invalid
        """
        errors = []
        
        # Validate SECRET_KEY
        if not self.SECRET_KEY or self.SECRET_KEY.get_secret_value() == "change-me-in-production":
            if self.ENV == "production":
                errors.append("SECRET_KEY must be set in production environment")
        
        # Validate DATABASE_URL
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        # Validate GROQ_API_KEYS in production
        if self.ENV == "production":
            if not self.GROQ_API_KEYS:
                errors.append("GROQ_API_KEYS must be set in production environment")
            # Warn / require BREVO in production if email sending is enabled by app logic
            if not self.BREVO_API_KEY or (self.BREVO_SENDER_EMAIL is None):
                errors.append("BREVO_API_KEY and BREVO_SENDER_EMAIL must be set in production for transactional emails")
            # Require webhook secret in production to secure payment callbacks
            if not self.PAYMENT_WEBHOOK_SECRET:
                errors.append("PAYMENT_WEBHOOK_SECRET must be set in production to validate payment webhooks")
        
        # Validate ACCESS_TOKEN_EXPIRE_SECONDS
        if self.ACCESS_TOKEN_EXPIRE_SECONDS < 60:
            errors.append("ACCESS_TOKEN_EXPIRE_SECONDS must be at least 60 seconds")
        
        # Validate PORT
        if not (1 <= self.PORT <= 65535):
            errors.append("PORT must be between 1 and 65535")
        
        # No Celery validation required — Kafka-based scheduler handles intervals
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


_settings: Optional[Settings] = None


def get_settings(force_reload: bool = False) -> Settings:
    """Create and cache a Settings instance from environment variables.

    This function intentionally avoids `BaseSettings` to keep the runtime
    dependency-free across environments.
    """
    global _settings
    if _settings is None or force_reload:
        # Load .env file if it exists
        load_dotenv()
        
        # Helper to parse comma-separated lists
        def _parse_list(val: Optional[str], default: List[str]) -> List[str]:
            if val is None:
                return default
            return [s.strip() for s in val.split(",") if s.strip()]
        # Build a defaults instance to safely read class default values
        _defaults = Settings()

        s = Settings(
            APP_NAME=os.getenv("APP_NAME", _defaults.APP_NAME),
            ENV=os.getenv("ENV", _defaults.ENV),
            DEBUG=os.getenv("DEBUG", str(_defaults.DEBUG)).lower() in ("1", "true", "yes"),
            HOST=os.getenv("HOST", _defaults.HOST),
            PORT=int(os.getenv("PORT", str(_defaults.PORT))),
            DATABASE_URL=os.getenv("DATABASE_URL", _defaults.DATABASE_URL),
            REDIS_URL=os.getenv("REDIS_URL", _defaults.REDIS_URL),
            REDIS_PASSWORD=os.getenv("REDIS_PASSWORD", _defaults.REDIS_PASSWORD),
            SECRET_KEY=SecretStr(os.getenv("SECRET_KEY")) if os.getenv("SECRET_KEY") else _defaults.SECRET_KEY,
            ACCESS_TOKEN_EXPIRE_SECONDS=int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", str(_defaults.ACCESS_TOKEN_EXPIRE_SECONDS))),
            CORS_ORIGINS=_parse_list(os.getenv("CORS_ORIGINS"), _defaults.CORS_ORIGINS),
            REQUEST_ID_HEADERS=os.getenv("REQUEST_ID_HEADERS", _defaults.REQUEST_ID_HEADERS),
            GROQ_API_KEYS=os.getenv("GROQ_API_KEYS", _defaults.GROQ_API_KEYS),
            LOG_LEVEL=os.getenv("LOG_LEVEL", _defaults.LOG_LEVEL).upper(),
            FRONTEND_ORIGIN=os.getenv("FRONTEND_ORIGIN", _defaults.FRONTEND_ORIGIN),
            KAFKA_BOOTSTRAP_SERVERS=os.getenv("KAFKA_BOOTSTRAP_SERVERS", _defaults.KAFKA_BOOTSTRAP_SERVERS),
            KAFKA_TOPIC_PREFIX=os.getenv("KAFKA_TOPIC_PREFIX", _defaults.KAFKA_TOPIC_PREFIX),
            KAFKA_USERNAME=os.getenv("KAFKA_USERNAME", _defaults.KAFKA_USERNAME),
            KAFKA_PASSWORD=os.getenv("KAFKA_PASSWORD", _defaults.KAFKA_PASSWORD),
            KAFKA_SECURITY_PROTOCOL=os.getenv("KAFKA_SECURITY_PROTOCOL", _defaults.KAFKA_SECURITY_PROTOCOL),
            KAFKA_SASL_MECHANISM=os.getenv("KAFKA_SASL_MECHANISM", _defaults.KAFKA_SASL_MECHANISM),
            SCHEDULER_EXAM_STATUS_UPDATE_INTERVAL=os.getenv("SCHEDULER_EXAM_STATUS_UPDATE_INTERVAL", None),
            SCHEDULER_EMAIL_SEND_INTERVAL=os.getenv("SCHEDULER_EMAIL_SEND_INTERVAL", None),
            FRONTEND_URL=os.getenv("FRONTEND_URL", _defaults.FRONTEND_URL),
            BREVO_API_KEY=SecretStr(os.getenv("BREVO_API_KEY")) if os.getenv("BREVO_API_KEY") else _defaults.BREVO_API_KEY,
            BREVO_SENDER_NAME=os.getenv("BREVO_SENDER_NAME", _defaults.BREVO_SENDER_NAME),
            BREVO_SENDER_EMAIL=os.getenv("BREVO_SENDER_EMAIL", _defaults.BREVO_SENDER_EMAIL),
            PAYMENT_WEBHOOK_SECRET=SecretStr(os.getenv("PAYMENT_WEBHOOK_SECRET")) if os.getenv("PAYMENT_WEBHOOK_SECRET") else _defaults.PAYMENT_WEBHOOK_SECRET,
        )
        
        # Validate configuration
        s.validate()
        
        _settings = s
    return _settings


__all__ = ["Settings", "get_settings"]
