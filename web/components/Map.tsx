"use client";

import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";

import { MapMarker } from "@/components/MapMarker";
import type { Incident, MapIncident } from "@/types/incident";

const DEFAULT_CENTER: [number, number] = [25.2048, 55.2708];
const DEFAULT_ZOOM = 11;

function MapController({
  selectedIncident,
}: {
  selectedIncident: Incident | null;
}) {
  const map = useMap();
  const previousSelectedId = useRef<string | null>(null);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      map.invalidateSize();
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [map]);

  useEffect(() => {
    if (!selectedIncident) {
      if (previousSelectedId.current) {
        map.flyTo(DEFAULT_CENTER, DEFAULT_ZOOM, {
          duration: 1,
        });
      }
      previousSelectedId.current = null;
      return;
    }

    map.flyTo([selectedIncident.latitude + 0.02, selectedIncident.longitude], 13, {
      duration: 1.1,
    });
    previousSelectedId.current = selectedIncident.id;
  }, [map, selectedIncident?.id, selectedIncident?.latitude, selectedIncident?.longitude]);

  return null;
}

export default function CrisisMap({
  incidents,
  mapIncidents,
  selectedIncidentId,
  onSelectIncident,
}: {
  incidents: Incident[];
  mapIncidents: MapIncident[];
  selectedIncidentId: string | null;
  onSelectIncident: (id: string) => void;
}) {
  const incidentById = useMemo(
    () => new globalThis.Map(incidents.map((incident) => [incident.id, incident])),
    [incidents],
  );

  const selectedIncident =
    incidents.find((incident) => incident.id === selectedIncidentId) ?? null;

  return (
    <div className="relative h-full min-h-0 overflow-hidden border border-line bg-panel">
      <div className="absolute inset-0">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapController selectedIncident={selectedIncident} />
          {mapIncidents.map((mapIncident) => (
            <MapMarker
              key={mapIncident.id}
              mapIncident={mapIncident}
              incident={incidentById.get(mapIncident.id)}
              selected={selectedIncidentId === mapIncident.id}
              onViewDetails={onSelectIncident}
            />
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
