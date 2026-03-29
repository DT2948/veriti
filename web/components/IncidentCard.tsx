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

function isRecentlyUpdated(timestamp: string, minutes = 2): boolean {
  const date = parseUtcTimestamp(timestamp);
  if (Number.isNaN(date.getTime())) {
    return false;
  }
  return Date.now() - date.getTime() <= minutes * 60 * 1000;
}

function hasGenericSummary(summary: string): boolean {
  const normalized = (summary || "").toLowerCase();
  return (
    normalized.includes("independent report(s) indicate") ||
    normalized.includes("photos were received alongside these reports") ||
    normalized.includes("videos were received alongside these reports") ||
    normalized.includes("photos and videos were received alongside these reports")
  );
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
  const accentColor = {
    official: "#22C55E",
    corroborated: "#F97316",
    plausible: "#EAB308",
    unverified: "#A89BA8",
  }[incident.confidence_tier];
  const analyzing = isRecentlyUpdated(incident.timestamp_last_updated) &&
    hasGenericSummary(incident.summary);
  const summaryPreview = analyzing
    ? "Analyzing submitted media and generating summary..."
    : incident.summary
      ? incident.summary
      : "Awaiting summary";

  return (
    <button
      id={`incident-${incident.id}`}
      type="button"
      onClick={onClick}
      style={{ borderLeftColor: accentColor }}
      className={`w-full border-l-[3px] bg-transparent px-3 py-3 text-left transition hover:bg-panel/40 ${
        highlighted ? "veriti-card-flash" : ""
      } ${expanded ? "bg-panel/60" : ""}`}
    >
      <div className="flex items-start gap-2">
        <div className="mt-1 text-2xl">{incident.emoji ?? "❓"}</div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 space-y-1">
              <h3 className="truncate text-sm font-semibold text-textPrimary">
                {incident.title}
              </h3>
              <p className="text-[10px] uppercase tracking-[0.14em] text-textMuted">
                {sourceLabel(incident.source_type)}
              </p>
            </div>
            <ConfidenceBadge tier={incident.confidence_tier} />
          </div>

          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-textSecondary">
            <p>{incident.number_of_reports} reports</p>
            <p className="text-textMuted">•</p>
            <p>{formatRelativeTime(incident.timestamp_last_updated)}</p>
            {analyzing ? (
              <>
                <p className="text-textMuted">•</p>
                <p className="text-official">Updating</p>
              </>
            ) : null}
          </div>

          <p className={`truncate text-xs ${analyzing ? "text-official" : "text-textMuted"}`}>
            {summaryPreview}
          </p>

          {expanded ? <IncidentDetail incident={incident} /> : null}
        </div>
      </div>
    </button>
  );
}
