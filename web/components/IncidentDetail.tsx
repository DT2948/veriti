import type { Incident } from "@/types/incident";

export function IncidentDetail({ incident }: { incident: Incident }) {
  return (
    <div className="space-y-3 border-t border-line pt-3 text-sm text-slate-300">
      <p className="leading-6 text-slate-200">{incident.summary}</p>
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
