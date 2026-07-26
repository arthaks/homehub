from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import DashboardResponse, PublicConfig, QuickLink, StatusSnapshot
from .settings import Settings


class StatusUnavailableError(RuntimeError):
    pass


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def read_snapshot(path: Path) -> StatusSnapshot:
    try:
        return StatusSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StatusUnavailableError("status snapshot does not exist") from exc
    except (OSError, ValidationError, ValueError) as exc:
        raise StatusUnavailableError("status snapshot is invalid") from exc


def load_public_config(path: Path) -> tuple[PublicConfig, list[QuickLink]]:
    if not path.exists():
        return PublicConfig(), []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        public = PublicConfig.model_validate(raw.get("server", {}))
        links = [QuickLink.model_validate(item) for item in raw.get("links", [])]
        return public, links
    except (OSError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise StatusUnavailableError("public configuration is invalid") from exc


def build_dashboard(settings: Settings, now: datetime | None = None) -> DashboardResponse:
    snapshot = read_snapshot(settings.status_file)
    generated_at = parse_timestamp(snapshot.generatedAt)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    age = max(0, int((current - generated_at).total_seconds()))
    if age <= settings.fresh_seconds:
        freshness = "fresh"
    elif age <= settings.stale_seconds:
        freshness = "delayed"
    else:
        freshness = "stale"
    _, links = load_public_config(settings.config_file)
    return DashboardResponse(
        **snapshot.model_dump(),
        fresh=freshness == "fresh",
        freshness=freshness,
        ageSeconds=age,
        links=links,
    )
