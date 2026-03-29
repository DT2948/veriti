export interface Incident {
  id: string;
  type: string;
  title: string;
  summary: string;
  source_type: string;
  confidence_tier: "official" | "corroborated" | "plausible" | "unverified";
  confidence_score: number;
  latitude: number;
  longitude: number;
  grid_cell: string;
  timestamp_first_seen: string;
  timestamp_last_updated: string;
  number_of_reports: number;
  official_overlap: boolean;
  media_count: number;
  tags: string[];
  verification_notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncidentListResponse {
  total: number;
  items: Incident[];
}

export interface MapIncident {
  id: string;
  type: string;
  title: string;
  confidence_tier: "official" | "corroborated" | "plausible" | "unverified";
  confidence_score: number;
  latitude: number;
  longitude: number;
  number_of_reports: number;
  is_active: boolean;
}
