"use client";

// Make sure the backend is running on localhost:8000 (or set NEXT_PUBLIC_API_URL).

import dynamic from "next/dynamic";
import { useState } from "react";

import { Header } from "@/components/Header";
import { IncidentFeed } from "@/components/IncidentFeed";
import { OfficialSourcePanel } from "@/components/OfficialSourcePanel";
import { StatusBar } from "@/components/StatusBar";
import { useIncidents } from "@/hooks/useIncidents";
import type { Incident } from "@/types/incident";

const CrisisMap = dynamic(() => import("@/components/Map"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center border border-line bg-panel text-sm text-slate-500">
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
    refresh,
  } = useIncidents();
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    null,
  );
  const [officialSourceOpen, setOfficialSourceOpen] = useState(false);

  return (
    <main className="h-screen overflow-hidden bg-transparent px-0 py-0 text-slate-100">
      <OfficialSourcePanel
        open={officialSourceOpen}
        onClose={() => setOfficialSourceOpen(false)}
        onCreated={refresh}
      />
      <div className="mx-auto flex h-full max-w-[1800px] flex-col gap-0 overflow-hidden">
        <div className="shrink-0">
          <Header
            autoRefresh={autoRefresh}
            onToggleAutoRefresh={setAutoRefresh}
            incidentCount={total}
            refreshing={refreshing}
            onOpenOfficialSource={() => setOfficialSourceOpen(true)}
          />
        </div>

        <section className="flex min-h-0 flex-1 flex-col gap-0 overflow-hidden lg:flex-row">
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
              <div className="pointer-events-none absolute inset-x-3 top-3 border border-line bg-ink/90 px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-slate-500 backdrop-blur">
                Connecting to live incident map...
              </div>
            ) : null}
            {error ? (
              <div className="pointer-events-none absolute inset-x-3 top-14 border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger backdrop-blur">
                {error}
              </div>
            ) : null}
          </div>

          <div className="min-h-0 w-full overflow-hidden lg:w-[380px] xl:w-[32%]">
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
