"use client";

import { useEffect, useMemo, useRef } from "react";
import { CircleMarker, Popup } from "react-leaflet";
import type L from "leaflet";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { Incident, MapIncident } from "@/types/incident";

function markerStyle(tier: MapIncident["confidence_tier"]) {
  switch (tier) {
    case "official":
      return { color: "#4c8dff", radius: 16 };
    case "corroborated":
      return { color: "#ef4444", radius: 14 };
    case "plausible":
      return { color: "#f59e0b", radius: 11 };
    default:
      return { color: "#94a3b8", radius: 8 };
  }
}

function isRecent(timestamp?: string): boolean {
  if (!timestamp) {
    return false;
  }
  return Date.now() - new Date(timestamp).getTime() <= 2 * 60_000;
}

export function MapMarker({
  mapIncident,
  incident,
  selected,
  onViewDetails,
}: {
  mapIncident: MapIncident;
  incident?: Incident;
  selected: boolean;
  onViewDetails: (id: string) => void;
}) {
  const markerRef = useRef<L.CircleMarker | null>(null);
  const { color, radius } = markerStyle(mapIncident.confidence_tier);
  const recent = isRecent(incident?.timestamp_last_updated);

  useEffect(() => {
    if (selected) {
      markerRef.current?.openPopup();
    }
  }, [selected]);

  const summaryPreview = useMemo(() => {
    const summary = incident?.summary ?? "Awaiting analyst summary.";
    return summary.length > 100 ? `${summary.slice(0, 100)}...` : summary;
  }, [incident?.summary]);

  return (
    <CircleMarker
      ref={(instance) => {
        markerRef.current = instance;
      }}
      center={[mapIncident.latitude, mapIncident.longitude]}
      radius={radius}
      pathOptions={{
        color,
        fillColor: color,
        fillOpacity: 0.78,
        weight: selected ? 3 : 2,
        className: recent ? "veriti-marker-pulse" : undefined,
      }}
    >
      <Popup>
        <div className="w-56 space-y-3">
          <div className="space-y-2">
            <p className="text-base font-semibold text-slate-100">
              {mapIncident.title}
            </p>
            <ConfidenceBadge tier={mapIncident.confidence_tier} />
          </div>
          <div className="space-y-1 text-sm text-slate-300">
            <p>{mapIncident.number_of_reports} reports</p>
            <p>{summaryPreview}</p>
          </div>
          <button
            type="button"
            onClick={() => onViewDetails(mapIncident.id)}
            className="inline-flex rounded-full border border-official/30 bg-official/10 px-3 py-1.5 text-sm text-official"
          >
            View Details
          </button>
        </div>
      </Popup>
    </CircleMarker>
  );
}
