from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MemoryStatus(BaseModel):
    totalBytes: int = Field(ge=0)
    usedBytes: int = Field(ge=0)


class DiskStatus(MemoryStatus):
    pass


class SystemStatus(BaseModel):
    hostname: str
    os: str
    kernel: str
    uptimeSeconds: int = Field(ge=0)
    cpuPercent: float = Field(ge=0, le=100)
    loadAverage: list[float] = Field(min_length=3, max_length=3)
    memory: MemoryStatus
    disk: DiskStatus
    temperatureCelsius: float | None = None
    ipv4: str | None = None


HealthState = Literal["healthy", "warning", "down", "unknown"]


class ServiceStatus(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    status: HealthState
    systemdState: str | None = None
    version: str | None = None
    detail: str | None = None


class ApplicationStatus(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    status: HealthState
    version: str | None = None
    commit: str | None = None
    deployedAt: str | None = None
    url: str | None = None
    repository: str | None = None


class StatusSnapshot(BaseModel):
    schemaVersion: int = 1
    generatedAt: str
    system: SystemStatus
    services: list[ServiceStatus] = []
    applications: list[ApplicationStatus] = []


class QuickLink(BaseModel):
    id: str
    name: str
    url: str
    category: str = "general"
    description: str | None = None


class DashboardResponse(StatusSnapshot):
    fresh: bool
    ageSeconds: int
    freshness: Literal["fresh", "delayed", "stale"]
    links: list[QuickLink] = []


class PublicConfig(BaseModel):
    serverDisplayName: str = "Home Server"
    timezone: str = "Asia/Shanghai"
    refreshIntervalSeconds: int = Field(default=15, ge=5, le=300)


class VersionResponse(BaseModel):
    name: str = "homehub"
    version: str
    commit: str
    buildTime: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    commit: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "not-ready"]
    statusFileAvailable: bool
    statusFileFresh: bool
    detail: str | None = None


JsonObject = dict[str, Any]
