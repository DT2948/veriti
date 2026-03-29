"use client";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { IncidentDetail } from "@/components/IncidentDetail";
import type { Incident } from "@/types/incident";

function sourceLabel(sourceType: string): string {
  if (sourceType === "official") {
    return "📡 Official";
  }
  if (sourceType === "mixed") {
    return "🔀 Mixed";
  }
  return "👥 Public";
}

function parseUtcTimestamp(timestamp: string): Date {
  return new Date(timestamp.endsWith("Z") ? timestamp : `${timestamp}Z`);
}

function formatRelativeTime(timestamp: string): string {
  const date = parseUtcTimestamp(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "unknown time";
  }
  const diffMs = Date.now() - date.getTime();
  const diffSeconds = Math.max(0, Math.floor(diffMs / 1000));
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return `${diffSeconds} second${diffSeconds !== 1 ? "s" : ""} ago`;
  }
  if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes !== 1 ? "s" : ""} ago`;
  }
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
  }
  return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;
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
      id={`incident-${incident.id}`}
      type="button"
      onClick={onClick}
      className={`w-full rounded-3xl border bg-panel px-4 py-4 text-left shadow-panel transition hover:border-slate-500/45 hover:bg-panelSoft ${
        highlighted ? "veriti-card-flash border-official/40" : "border-line"
      } ${expanded ? "bg-panelSoft" : ""}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-1 text-2xl">{incident.emoji ?? "❓"}</div>
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
