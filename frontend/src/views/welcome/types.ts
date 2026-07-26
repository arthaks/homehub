export type HealthState = "healthy" | "warning" | "down" | "unknown";

export interface ResourceUsage {
  totalBytes: number;
  usedBytes: number;
}

export interface SystemStatus {
  hostname: string;
  os: string;
  kernel: string;
  uptimeSeconds: number;
  cpuPercent: number;
  loadAverage: number[];
  memory: ResourceUsage;
  disk: ResourceUsage;
  temperatureCelsius: number | null;
  ipv4: string | null;
}

export interface ServiceStatus {
  id: string;
  name: string;
  status: HealthState;
  systemdState?: string;
  version?: string;
  detail?: string;
}

export interface ApplicationStatus {
  id: string;
  name: string;
  status: HealthState;
  version?: string;
  commit?: string;
  deployedAt?: string;
  url?: string;
  repository?: string;
}

export interface QuickLink {
  id: string;
  name: string;
  url: string;
  category: string;
  description?: string;
}

export interface DashboardResponse {
  schemaVersion: number;
  generatedAt: string;
  fresh: boolean;
  ageSeconds: number;
  freshness: "fresh" | "delayed" | "stale";
  system: SystemStatus;
  services: ServiceStatus[];
  applications: ApplicationStatus[];
  links: QuickLink[];
}

export interface PublicConfig {
  serverDisplayName: string;
  timezone: string;
  refreshIntervalSeconds: number;
}
