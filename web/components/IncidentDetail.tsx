import type { Incident } from "@/types/incident";

function parseUtcTimestamp(timestamp: string): Date {
  return new Date(timestamp.endsWith("Z") ? timestamp : `${timestamp}Z`);
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

export function IncidentDetail({ incident }: { incident: Incident }) {
  const analyzing = isRecentlyUpdated(incident.timestamp_last_updated) &&
    hasGenericSummary(incident.summary);
  const summaryText = analyzing
    ? "Analyzing submitted media and generating a richer incident summary..."
    : incident.summary;

  return (
    <div className="space-y-3 border-t border-line pt-3 text-sm text-slate-300">
      {analyzing ? (
        <div className="rounded-2xl border border-official/50 bg-official/15 px-3 py-3 text-sm font-medium text-official shadow-[0_0_0_1px_rgba(34,197,94,0.08)]">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-official animate-pulse" />
            <span>Analyzing submitted media and refreshing summary...</span>
          </div>
        </div>
      ) : null}
      <p className={`leading-6 ${analyzing ? "font-medium text-official" : "text-slate-200"}`}>
        {summaryText}
      </p>
      <div>
        <p className="mb-1 text-xs uppercase tracking-[0.14em] text-slate-500">
          Verification Notes
        </p>
        <p className="leading-6">{incident.verification_notes}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {incident.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-line bg-panelSoft px-2 py-1 text-xs text-slate-300"
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
