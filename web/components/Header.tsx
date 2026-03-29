"use client";

import { PulsingDot } from "@/components/PulsingDot";

interface HeaderProps {
  autoRefresh: boolean;
  onToggleAutoRefresh: (value: boolean) => void;
  incidentCount: number;
  refreshing: boolean;
  onOpenOfficialSource: () => void;
}

export function Header({
  autoRefresh,
  onToggleAutoRefresh,
  incidentCount,
  refreshing,
  onOpenOfficialSource,
}: HeaderProps) {
  void onToggleAutoRefresh;

  return (
    <header className="flex min-h-[50px] items-center justify-between border-b border-line bg-ink px-3 py-2">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-line bg-panel text-xs font-semibold tracking-[0.18em] text-slate-100">
          <span className="text-2xl">🛡️</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-100">
              Veriti
            </h1>
            {refreshing ? (
              <span className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
                Refreshing
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex items-center gap-2 px-1 text-[11px] uppercase tracking-[0.18em] text-slate-500">
          <PulsingDot active={autoRefresh} colorClass="bg-success" />
          <span>LIVE</span>
        </div>

        <button
          type="button"
          onClick={onOpenOfficialSource}
          className="inline-flex items-center rounded-sm border border-line bg-transparent px-2.5 py-1.5 text-xs text-slate-300 transition hover:border-official/40 hover:text-slate-100"
        >
          <span>📡</span>
          Official Source
        </button>

        <button
          type="button"
          disabled
          title="Coming soon"
          className="inline-flex cursor-not-allowed items-center rounded-sm border border-line bg-transparent px-2.5 py-1.5 text-xs text-slate-500"
        >
          <span>🔊</span>
          Audio briefing
        </button>

        <div className="px-1 text-xs text-slate-500">
          {incidentCount} active
        </div>
      </div>
    </header>
  );
}
