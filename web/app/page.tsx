"use client";

// Make sure the backend is running on localhost:8000 (or set NEXT_PUBLIC_API_URL).

import dynamic from "next/dynamic";
import { useState } from "react";

import { Header } from "@/components/Header";
import { IncidentFeed } from "@/components/IncidentFeed";
import { StatusBar } from "@/components/StatusBar";
import { useIncidents } from "@/hooks/useIncidents";
import type { Incident } from "@/types/incident";

const CrisisMap = dynamic(() => import("@/components/Map"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center rounded-3xl border border-line bg-panel text-sm text-slate-400 shadow-panel">
      Loading map...
    </div>
  ),
});

export default function DashboardPage() {
  const {
    incidents,
    mapIncidents,
    total,
    loading,
    refreshing,
    error,
    autoRefresh,
    setAutoRefresh,
    lastUpdatedAt,
    highlightedIds,
  } = useIncidents();
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    null,
  );

  return (
    <main className="h-screen overflow-hidden bg-transparent px-4 py-4 text-slate-100 md:px-6">
      <div className="mx-auto flex h-full max-w-[1800px] flex-col gap-4 overflow-hidden">
        <div className="shrink-0">
          <Header
            autoRefresh={autoRefresh}
            onToggleAutoRefresh={setAutoRefresh}
            incidentCount={total}
            refreshing={refreshing}
          />
        </div>

        <section className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden lg:flex-row">
          <div className="relative min-h-[42vh] flex-1 overflow-hidden lg:min-h-0">
            <div className="absolute inset-0">
              <CrisisMap
                incidents={incidents}
                mapIncidents={mapIncidents}
                selectedIncidentId={selectedIncidentId}
                onSelectIncident={setSelectedIncidentId}
              />
            </div>
            {loading ? (
              <div className="pointer-events-none absolute inset-x-4 top-4 rounded-full border border-line bg-ink/80 px-3 py-2 text-xs uppercase tracking-[0.16em] text-slate-400 backdrop-blur">
                Connecting to live incident map...
              </div>
            ) : null}
            {error ? (
              <div className="pointer-events-none absolute inset-x-4 top-16 rounded-2xl border border-corroborated/40 bg-corroborated/10 px-4 py-3 text-sm text-corroborated backdrop-blur">
                {error}
              </div>
            ) : null}
          </div>

          <div className="min-h-0 w-full overflow-hidden lg:w-[400px] xl:w-[34%]">
            <IncidentFeed
              incidents={incidents}
              selectedIncidentId={selectedIncidentId}
              highlightedIds={highlightedIds}
              onSelectIncident={(incident: Incident) => {
                setSelectedIncidentId(incident.id);
              }}
            />
          </div>
        </section>

        <div className="shrink-0">
          <StatusBar lastUpdatedAt={lastUpdatedAt} autoRefresh={autoRefresh} />
        </div>
      </div>
    </main>
  );
}
