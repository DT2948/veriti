"use client";

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
  return (
    <aside className="flex h-full min-h-0 flex-col overflow-hidden rounded-3xl border border-line bg-panel/95 shadow-panel">
      <div className="shrink-0 border-b border-line px-5 py-4">
        <h2 className="text-lg font-semibold text-slate-100">Incident Feed</h2>
        <p className="mt-1 text-sm text-slate-400">
          Live incidents sorted by latest verification activity.
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="space-y-4">
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
            <div className="rounded-3xl border border-dashed border-line px-5 py-12 text-center text-sm text-slate-400">
              No active incidents available.
            </div>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
