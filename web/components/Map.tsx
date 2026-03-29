"use client";

import { useEffect, useMemo } from "react";
import L from "leaflet";
import { MapContainer, TileLayer, useMap } from "react-leaflet";

import { MapMarker } from "@/components/MapMarker";
import type { Incident, MapIncident } from "@/types/incident";

function MapController({
  selectedIncident,
}: {
  selectedIncident: Incident | null;
}) {
  const map = useMap();

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      map.invalidateSize();
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [map]);

  useEffect(() => {
    if (!selectedIncident) {
      return;
    }

    const mapSize = map.getSize();
    const targetLatLng = L.latLng(
      selectedIncident.latitude,
      selectedIncident.longitude,
    );
    const targetPoint = map.latLngToContainerPoint(targetLatLng);
    const offsetX = mapSize.x * 0.18;
    const offsetPoint = L.point(targetPoint.x - offsetX, targetPoint.y);
    const offsetLatLng = map.containerPointToLatLng(offsetPoint);

    map.flyTo([selectedIncident.latitude + 0.02, selectedIncident.longitude], 13, {
      duration: 1.1,
    });
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
          center={[25.2048, 55.2708]}
          zoom={11}
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
