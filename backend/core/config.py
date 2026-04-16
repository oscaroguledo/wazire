from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, SecretStr


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
    DATABASE_URL: Optional[str] = "sqlite+aiosqlite:///./wazire_dev.db"
    REDIS_URL: Optional[str] = None

    SECRET_KEY: Optional[SecretStr] = SecretStr('sasaassasdsfsdfs')
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600

    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    REQUEST_ID_HEADERS: str = "X-Request-ID,X-Correlation-ID"

    GROQ_API_KEY: str = "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"

    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [s.strip() for s in self.CORS_ORIGINS.split(",") if s.strip()]
        return list(self.CORS_ORIGINS)

    def request_id_headers_list(self) -> List[str]:
        """Return `REQUEST_ID_HEADERS` as a list — accepts comma string or list."""
        if isinstance(self.REQUEST_ID_HEADERS, str):
            return [s.strip() for s in self.REQUEST_ID_HEADERS.split(",") if s.strip()]
        return list(self.REQUEST_ID_HEADERS)
    
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


_settings: Optional[Settings] = None


def get_settings(force_reload: bool = False) -> Settings:
    """Create and cache a Settings instance from environment variables.

    This function intentionally avoids `BaseSettings` to keep the runtime
    dependency-free across environments.
    """
    import os
    from dotenv import load_dotenv

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
            SECRET_KEY=SecretStr(os.getenv("SECRET_KEY")) if os.getenv("SECRET_KEY") else _defaults.SECRET_KEY,
            ACCESS_TOKEN_EXPIRE_SECONDS=int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", str(_defaults.ACCESS_TOKEN_EXPIRE_SECONDS))),
            CORS_ORIGINS=_parse_list(os.getenv("CORS_ORIGINS"), _defaults.CORS_ORIGINS),
            REQUEST_ID_HEADERS=os.getenv("REQUEST_ID_HEADERS", _defaults.REQUEST_ID_HEADERS),
        )
        _settings = s
    return _settings


__all__ = ["Settings", "get_settings"]
