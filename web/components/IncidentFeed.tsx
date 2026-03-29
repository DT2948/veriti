"use client";

import { useEffect } from "react";

import { IncidentCard } from "@/components/IncidentCard";
import type { Incident } from "@/types/incident";

export function IncidentFeed({
  incidents,
  selectedIncidentId,
  onSelectIncident,
  highlightedIds,
}: {
  incidents: Incident[];
  selectedIncidentId: string | null;
  onSelectIncident: (incident: Incident) => void;
  highlightedIds: Set<string>;
}) {
  useEffect(() => {
    if (!selectedIncidentId) {
      return;
    }

    const element = document.getElementById(`incident-${selectedIncidentId}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [selectedIncidentId]);

  return (
    <aside className="flex h-full min-h-0 flex-col overflow-hidden border-l border-line bg-ink">
      <div className="shrink-0 border-b border-line px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-textMuted">
          Incident Feed
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-line">
          {incidents.map((incident) => (
            <IncidentCard
              key={incident.id}
              incident={incident}
              expanded={selectedIncidentId === incident.id}
              highlighted={highlightedIds.has(incident.id)}
              onClick={() => onSelectIncident(incident)}
            />
          ))}
          {incidents.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm text-textMuted">
              No active incidents available.
            </div>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
