import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.settings import Settings


def snapshot(generated_at: datetime) -> dict:
    return {
        "schemaVersion": 1,
        "generatedAt": generated_at.isoformat(),
        "system": {
            "hostname": "test-server",
            "os": "Ubuntu 24.04 LTS",
            "kernel": "6.8.0-test",
            "uptimeSeconds": 3600,
            "cpuPercent": 12.5,
            "loadAverage": [0.1, 0.2, 0.3],
            "memory": {"totalBytes": 8000, "usedBytes": 2000},
            "disk": {"totalBytes": 100000, "usedBytes": 30000},
            "temperatureCelsius": 48.0,
            "ipv4": "192.168.0.9",
        },
        "services": [
            {
                "id": "docker",
                "name": "Docker",
                "status": "healthy",
                "systemdState": "active",
            }
        ],
        "applications": [],
    }


def configure(tmp_path: Path, generated_at: datetime) -> TestClient:
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps(snapshot(generated_at)), encoding="utf-8")
    config_file = tmp_path / "homehub.yaml"
    config_file.write_text(
        """server:
  serverDisplayName: Test Home
  refreshIntervalSeconds: 20
links:
  - id: github
    name: GitHub
    url: https://github.com/example/homehub
""",
        encoding="utf-8",
    )
    main.settings = Settings(
        status_file=status_file,
        config_file=config_file,
        static_dir=tmp_path / "missing-static",
        version="0.1.0",
        commit="abc123",
        build_time="2026-07-27T00:00:00Z",
        fresh_seconds=60,
        stale_seconds=300,
    )
    return TestClient(main.app)


def test_health_does_not_require_snapshot(tmp_path: Path):
    client = configure(tmp_path, datetime.now(UTC))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0", "commit": "abc123"}


def test_dashboard_returns_fresh_snapshot_and_links(tmp_path: Path):
    client = configure(tmp_path, datetime.now(UTC))
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["fresh"] is True
    assert body["freshness"] == "fresh"
    assert body["system"]["hostname"] == "test-server"
    assert body["links"][0]["id"] == "github"


def test_ready_reports_delayed_snapshot(tmp_path: Path):
    client = configure(tmp_path, datetime.now(UTC) - timedelta(seconds=90))
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["statusFileFresh"] is False


def test_ready_rejects_stale_snapshot(tmp_path: Path):
    client = configure(tmp_path, datetime.now(UTC) - timedelta(minutes=10))
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "status snapshot is stale"


def test_invalid_snapshot_returns_503(tmp_path: Path):
    client = configure(tmp_path, datetime.now(UTC))
    main.settings.status_file.write_text("not-json", encoding="utf-8")
    response = client.get("/api/dashboard")
    assert response.status_code == 503
    assert response.json()["detail"] == "status snapshot is invalid"


def test_public_config(tmp_path: Path):
    client = configure(tmp_path, datetime.now(UTC))
    response = client.get("/api/config/public")
    assert response.status_code == 200
    assert response.json()["serverDisplayName"] == "Test Home"
    assert response.json()["refreshIntervalSeconds"] == 20
