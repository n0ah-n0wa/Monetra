import { apiClient } from "@/api/client";

export type HealthResponse = {
  status: "ok";
};

export async function fetchHealth(): Promise<HealthResponse> {
  return apiClient.get<HealthResponse>("/health");
}
