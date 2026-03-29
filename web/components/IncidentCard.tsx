"use client";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { IncidentDetail } from "@/components/IncidentDetail";
import type { Incident } from "@/types/incident";

function iconForType(type: string): string {
  switch (type) {
    case "explosion":
      return "💥";
    case "debris":
      return "🧱";
    case "siren":
      return "🚨";
    case "missile":
      return "🚀";
    case "warning":
      return "⚠️";
    default:
      return "❓";
  }
}

function sourceLabel(sourceType: string): string {
  if (sourceType === "official") {
    return "📡 Official";
  }
  if (sourceType === "mixed") {
    return "🔀 Mixed";
  }
  return "👥 Public";
}

function formatRelativeTime(timestamp: string): string {
  const diffMs = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.max(0, Math.floor(diffMs / 60_000));
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours} hour${hours === 1 ? "" : "s"} ago`;
}

export function IncidentCard({
  incident,
  expanded,
  onClick,
  highlighted,
}: {
  incident: Incident;
  expanded: boolean;
  onClick: () => void;
  highlighted: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-3xl border bg-panel px-4 py-4 text-left shadow-panel transition hover:border-slate-500/45 hover:bg-panelSoft ${
        highlighted ? "veriti-card-flash border-official/40" : "border-line"
      } ${expanded ? "bg-panelSoft" : ""}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-1 text-2xl">{iconForType(incident.type)}</div>
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-slate-100">
                {incident.title}
              </h3>
              <p className="text-xs uppercase tracking-[0.14em] text-slate-500">
                {sourceLabel(incident.source_type)}
              </p>
            </div>
            <ConfidenceBadge tier={incident.confidence_tier} />
          </div>

          <div className="grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
            <p>{Math.round(incident.confidence_score * 100)}% confidence</p>
            <p>{incident.number_of_reports} independent reports</p>
            <p>{formatRelativeTime(incident.timestamp_last_updated)}</p>
            <p className="text-slate-400">
              {incident.summary ? `${incident.summary.slice(0, 70)}...` : "Awaiting summary"}
            </p>
          </div>

          {expanded ? <IncidentDetail incident={incident} /> : null}
        </div>
      </div>
    </button>
  );
}
