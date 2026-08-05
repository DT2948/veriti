import type { Incident, IncidentListResponse, MapIncident } from "@/types/incident";
import { beginPerformanceEvent, finishPerformanceEvent } from "@/lib/performance";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJson<T>(path: string, operation: string): Promise<T> {
  const started = beginPerformanceEvent();
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch ${path}: ${response.status}`);
    }

    const payload = await response.json() as T;
    finishPerformanceEvent(operation, started, "success");
    return payload;
  } catch (error) {
    finishPerformanceEvent(operation, started, "error");
    throw error;
  }
}

export async function fetchIncidents(): Promise<IncidentListResponse> {
  return fetchJson<IncidentListResponse>("/api/v1/incidents", "dashboard.incidents_fetch");
}

export async function fetchMapIncidents(): Promise<MapIncident[]> {
  return fetchJson<MapIncident[]>("/api/v1/incidents/map", "dashboard.map_fetch");
}

export async function createOfficialAlert(input: {
  text: string;
  source_url?: string;
}): Promise<Incident> {
  const response = await fetch(`${API_BASE_URL}/api/v1/official-alerts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let detail = `Failed to create official alert: ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        detail = payload.detail;
      }
    } catch {
      // Keep the default message.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<Incident>;
}
