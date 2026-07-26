import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    status_file: Path = Path(os.getenv("HOMEHUB_STATUS_FILE", "/data/status/status.json"))
    config_file: Path = Path(os.getenv("HOMEHUB_CONFIG_FILE", "/app/config/homehub.yaml"))
    static_dir: Path = Path(os.getenv("HOMEHUB_STATIC_DIR", "/app/static"))
    version: str = os.getenv("HOMEHUB_VERSION", "0.1.0-dev")
    commit: str = os.getenv("HOMEHUB_COMMIT_SHA", "development")
    build_time: str = os.getenv("HOMEHUB_BUILD_TIME", "unknown")
    fresh_seconds: int = int(os.getenv("HOMEHUB_FRESH_SECONDS", "60"))
    stale_seconds: int = int(os.getenv("HOMEHUB_STALE_SECONDS", "300"))
