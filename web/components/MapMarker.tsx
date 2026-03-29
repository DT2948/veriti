"use client";

import { useEffect, useMemo, useRef } from "react";
import { CircleMarker, Popup } from "react-leaflet";
import type L from "leaflet";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { Incident, MapIncident } from "@/types/incident";

const CONFIDENCE_COLORS: Record<string, { fillColor: string; radius: number }> = {
  unverified: { fillColor: "#6B7280", radius: 10 },
  plausible: { fillColor: "#FACC15", radius: 11 },
  corroborated: { fillColor: "#F97316", radius: 14 },
  confirmed: { fillColor: "#EF4444", radius: 15 },
  official: { fillColor: "#22C55E", radius: 16 },
};

function markerStyle(tier: MapIncident["confidence_tier"] | "confirmed") {
  const tierStyle = CONFIDENCE_COLORS[tier] ?? CONFIDENCE_COLORS.unverified;
  return {
    fillColor: tierStyle.fillColor,
    borderColor: tierStyle.fillColor,
    radius: tierStyle.radius,
  };
}

function parseUtcTimestamp(timestamp: string): Date {
  return new Date(timestamp.endsWith("Z") ? timestamp : `${timestamp}Z`);
}

function isRecent(timestamp?: string): boolean {
  if (!timestamp) {
    return false;
  }
  const parsed = parseUtcTimestamp(timestamp);
  if (Number.isNaN(parsed.getTime())) {
    return false;
  }
  return Date.now() - parsed.getTime() <= 2 * 60_000;
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
  const { fillColor, borderColor, radius } = markerStyle(
    mapIncident.confidence_tier,
  );
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
      eventHandlers={{
        click: () => {
          onViewDetails(mapIncident.id);
        },
      }}
      radius={radius}
      pathOptions={{
        color: borderColor,
        fillColor,
        fillOpacity: selected ? 0.7 : 0.58,
        opacity: selected ? 0.84 : 0.74,
        stroke: false,
        className: recent ? "veriti-marker-soft-pulse" : undefined,
      }}
    >
      <Popup>
        <div className="w-56 space-y-3">
          <div className="space-y-2">
            <p className="text-base font-semibold text-slate-100">
              {(mapIncident.emoji ?? "❓") + " " + mapIncident.title}
            </p>
            <ConfidenceBadge tier={mapIncident.confidence_tier} />
          </div>
          <div className="space-y-1 text-sm text-slate-300">
            <p>{mapIncident.number_of_reports} reports</p>
            <p>{summaryPreview}</p>
          </div>
        </div>
      </Popup>
    </CircleMarker>
  );
}
