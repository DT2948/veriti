"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchIncidents, fetchMapIncidents } from "@/lib/api";
import type { Incident, MapIncident } from "@/types/incident";

interface UseIncidentsResult {
  incidents: Incident[];
  mapIncidents: MapIncident[];
  total: number;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  autoRefresh: boolean;
  setAutoRefresh: (value: boolean) => void;
  lastUpdatedAt: number | null;
  highlightedIds: Set<string>;
  refresh: () => Promise<void>;
}

function buildChangeSet(previous: Incident[], next: Incident[]): Set<string> {
  const previousById = new Map(previous.map((incident) => [incident.id, incident]));
  const changed = new Set<string>();

  for (const incident of next) {
    const existing = previousById.get(incident.id);
    if (!existing) {
      changed.add(incident.id);
      continue;
    }

    if (
      existing.number_of_reports !== incident.number_of_reports ||
      existing.confidence_tier !== incident.confidence_tier
    ) {
      changed.add(incident.id);
    }
  }

  return changed;
}

export function useIncidents(): UseIncidentsResult {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [mapIncidents, setMapIncidents] = useState<MapIncident[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<number | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());

  const incidentsRef = useRef<Incident[]>([]);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      setRefreshing(true);

      const [incidentResponse, mapResponse] = await Promise.all([
        fetchIncidents(),
        fetchMapIncidents(),
      ]);

      const sorted = [...incidentResponse.items].sort(
        (a, b) =>
          new Date(b.timestamp_last_updated).getTime() -
          new Date(a.timestamp_last_updated).getTime(),
      );

      const changed = buildChangeSet(incidentsRef.current, sorted);
      incidentsRef.current = sorted;

      setIncidents(sorted);
      setMapIncidents(mapResponse);
      setTotal(incidentResponse.total);
      setLastUpdatedAt(Date.now());

      if (changed.size > 0) {
        setHighlightedIds(changed);
        window.setTimeout(() => {
          setHighlightedIds(new Set());
        }, 2200);
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not load live incidents.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void refresh();
    }, 10_000);

    return () => window.clearInterval(intervalId);
  }, [autoRefresh, refresh]);

  return useMemo(
    () => ({
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
    }),
    [
      incidents,
      mapIncidents,
      total,
      loading,
      refreshing,
      error,
      autoRefresh,
      lastUpdatedAt,
      highlightedIds,
      refresh,
    ],
  );
}
