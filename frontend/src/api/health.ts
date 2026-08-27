export type HealthResponse = {
  status: "ok";
};

export async function fetchHealth(): Promise<HealthResponse> {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Health check failed");
  }

  return response.json() as Promise<HealthResponse>;
}

export async function fetchReady(): Promise<{ status: string }> {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
  const response = await fetch(`${API_BASE_URL}/ready`, {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Readiness check failed");
  }

  return response.json() as Promise<{ status: string }>;
}
