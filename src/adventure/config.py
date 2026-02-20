"""Configuration for Adventure."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration."""

    database_url: str = "sqlite:///./adventure.db"
    host: str = "localhost"
    port: int = 1965
    certfile: Path | None = None
    keyfile: Path | None = None
    log_level: str = "INFO"
    log_file: Path | None = None
    json_logs: bool = False
    hash_fingerprints: bool = True

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        certfile = os.getenv("ADVENTURE_CERTFILE")
        keyfile = os.getenv("ADVENTURE_KEYFILE")
        log_file = os.getenv("ADVENTURE_LOG_FILE")

        return cls(
            database_url=os.getenv("ADVENTURE_DATABASE_URL", cls.database_url),
            host=os.getenv("ADVENTURE_HOST", cls.host),
            port=int(os.getenv("ADVENTURE_PORT", str(cls.port))),
            certfile=Path(certfile) if certfile else None,
            keyfile=Path(keyfile) if keyfile else None,
            log_level=os.getenv("ADVENTURE_LOG_LEVEL", cls.log_level),
            log_file=Path(log_file) if log_file else None,
            json_logs=os.getenv("ADVENTURE_JSON_LOGS", "").lower()
            in ("true", "1", "yes"),
            hash_fingerprints=os.getenv("ADVENTURE_HASH_FINGERPRINTS", "true").lower()
            not in ("false", "0", "no"),
        )
