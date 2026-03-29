"use client";

import { PulsingDot } from "@/components/PulsingDot";

interface HeaderProps {
  autoRefresh: boolean;
  onToggleAutoRefresh: (value: boolean) => void;
  incidentCount: number;
  refreshing: boolean;
}

export function Header({
  autoRefresh,
  onToggleAutoRefresh,
  incidentCount,
  refreshing,
}: HeaderProps) {
  return (
    <header className="flex flex-col gap-4 rounded-3xl border border-line bg-panel/90 px-5 py-4 shadow-panel backdrop-blur md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-official/15 ring-1 ring-official/25">
          <span className="text-2xl">🛡️</span>
        </div>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
              Veriti
            </h1>
            {refreshing ? (
              <span className="text-xs uppercase tracking-[0.16em] text-slate-400">
                Refreshing
              </span>
            ) : null}
          </div>
          <p className="text-sm text-slate-400">Live Crisis Verification</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => onToggleAutoRefresh(!autoRefresh)}
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition ${
            autoRefresh
              ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
              : "border-line bg-panelSoft text-slate-300"
          }`}
        >
          <PulsingDot active={autoRefresh} colorClass="bg-emerald-400" />
          Auto-refresh {autoRefresh ? "ON" : "OFF"}
        </button>

        <button
          type="button"
          disabled
          title="Coming soon"
          className="inline-flex cursor-not-allowed items-center gap-2 rounded-full border border-line bg-panelSoft px-3 py-2 text-sm text-slate-500"
        >
          <span>🔊</span>
          Audio briefing
        </button>

        <div className="rounded-full border border-line bg-panelSoft px-3 py-2 text-sm text-slate-300">
          {incidentCount} active incidents
        </div>
      </div>
    </header>
  );
}
