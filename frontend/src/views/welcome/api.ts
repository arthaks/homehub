import { http } from "@/utils/http";
import type { DashboardResponse, PublicConfig } from "./types";

export const getDashboard = () =>
  http.request<DashboardResponse>("get", "/api/dashboard");

export const getPublicConfig = () =>
  http.request<PublicConfig>("get", "/api/config/public");
