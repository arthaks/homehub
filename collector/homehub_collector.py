#!/usr/bin/env python3
"""Collect a deliberately small, non-sensitive HomeHub status snapshot."""

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_SERVICES = {
    "ssh": ("SSH", "ssh.service"),
    "network-manager": ("NetworkManager", "NetworkManager.service"),
    "docker": ("Docker", "docker.service"),
    "containerd": ("containerd", "containerd.service"),
    "mihomo": ("Mihomo", "mihomo.service"),
    "mihomo-subscription": (
        "Mihomo subscription timer",
        "mihomo-subscription-update.timer",
    ),
}


def run(*args: str, timeout: float = 3) -> str:
    try:
        return subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def read_key_values(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def cpu_times() -> tuple[int, int]:
    fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
    values = [int(value) for value in fields]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return sum(values), idle


def cpu_percent(interval: float = 0.15) -> float:
    total_a, idle_a = cpu_times()
    time.sleep(interval)
    total_b, idle_b = cpu_times()
    total_delta = total_b - total_a
    return round(0 if total_delta <= 0 else 100 * (1 - (idle_b - idle_a) / total_delta), 1)


def memory_status() -> dict[str, int]:
    values = read_key_values(Path("/proc/meminfo"))
    total = int(values["MemTotal"].split()[0]) * 1024
    available = int(values["MemAvailable"].split()[0]) * 1024
    return {"totalBytes": total, "usedBytes": total - available}


def temperature() -> float | None:
    readings: list[float] = []
    for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            value = float(path.read_text(encoding="utf-8").strip())
            readings.append(value / 1000 if value > 1000 else value)
        except (OSError, ValueError):
            continue
    plausible = [value for value in readings if 0 < value < 120]
    return round(max(plausible), 1) if plausible else None


def primary_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 9))
            return sock.getsockname()[0]
    except OSError:
        return None


def service_status(identifier: str, name: str, unit: str) -> dict[str, Any]:
    active = run("systemctl", "is-active", unit)
    enabled = run("systemctl", "is-enabled", unit)
    status = "healthy" if active == "active" else "down"
    if active in {"activating", "deactivating", "reloading"}:
        status = "warning"
    elif active not in {"active", "inactive", "failed"}:
        status = "unknown"
    return {
        "id": identifier,
        "name": name,
        "status": status,
        "systemdState": active or "unknown",
        "detail": f"enabled={enabled or 'unknown'}",
    }


def probe_json(url: str, timeout: float = 2) -> tuple[bool, dict[str, Any], str | None]:
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        elapsed = int((time.monotonic() - started) * 1000)
        return True, body if isinstance(body, dict) else {}, f"{elapsed} ms"
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return False, {}, type(exc).__name__


def mihomo_details(services: list[dict[str, Any]]) -> None:
    target = next((service for service in services if service["id"] == "mihomo"), None)
    if not target or target["status"] != "healthy":
        return
    ok, data, detail = probe_json("http://127.0.0.1:9090/version")
    if ok:
        target["version"] = data.get("version")
        target["detail"] = f"API {detail}"
    else:
        target["status"] = "warning"
        target["detail"] = f"service active, API unavailable ({detail})"


def subscription_details(services: list[dict[str, Any]]) -> None:
    target = next(
        (service for service in services if service["id"] == "mihomo-subscription"), None
    )
    if not target:
        return
    result = run(
        "systemctl",
        "show",
        "mihomo-subscription-update.service",
        "--property=Result,ExecMainStatus,InactiveExitTimestamp",
    )
    values = dict(
        line.split("=", 1) for line in result.splitlines() if "=" in line
    )
    last_result = values.get("Result", "unknown")
    timestamp = values.get("InactiveExitTimestamp", "")
    if last_result not in {"success", "unknown", ""}:
        target["status"] = "warning"
    target["detail"] = f"last={last_result}" + (f", {timestamp}" if timestamp else "")


def application_status() -> list[dict[str, Any]]:
    version_file = Path("/srv/apps/homehub/deploy-state/current.json")
    app: dict[str, Any] = {
        "id": "homehub",
        "name": "HomeHub",
        "status": "healthy",
        "url": "http://192.168.0.9:8088",
    }
    if version_file.exists():
        try:
            data = json.loads(version_file.read_text(encoding="utf-8"))
            app.update(
                {
                    key: data[key]
                    for key in ("version", "commit", "deployedAt")
                    if key in data
                }
            )
        except (OSError, ValueError):
            app["status"] = "warning"
    return [app]


def operating_system_name() -> str:
    try:
        return platform.freedesktop_os_release().get("PRETTY_NAME", platform.system())
    except OSError:
        return f"{platform.system()} {platform.release()}"


def build_snapshot() -> dict[str, Any]:
    disk = shutil.disk_usage("/")
    services = [
        service_status(identifier, name, unit)
        for identifier, (name, unit) in DEFAULT_SERVICES.items()
    ]
    mihomo_details(services)
    subscription_details(services)
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "system": {
            "hostname": socket.gethostname(),
            "os": operating_system_name(),
            "kernel": platform.release(),
            "uptimeSeconds": int(float(Path("/proc/uptime").read_text().split()[0])),
            "cpuPercent": cpu_percent(),
            "loadAverage": [round(value, 2) for value in os.getloadavg()],
            "memory": memory_status(),
            "disk": {"totalBytes": disk.total, "usedBytes": disk.used},
            "temperatureCelsius": temperature(),
            "ipv4": primary_ipv4(),
        },
        "services": services,
        "applications": application_status(),
    }


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/var/lib/homehub/status.json"))
    args = parser.parse_args()
    atomic_write(args.output, build_snapshot())


if __name__ == "__main__":
    main()
