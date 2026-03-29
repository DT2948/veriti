import type { IncidentListResponse, MapIncident } from "@/types/incident";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchIncidents(): Promise<IncidentListResponse> {
  return fetchJson<IncidentListResponse>("/api/v1/incidents");
}

export async function fetchMapIncidents(): Promise<MapIncident[]> {
  return fetchJson<MapIncident[]>("/api/v1/incidents/map");
}
