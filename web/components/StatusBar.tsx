"use client";

import { PulsingDot } from "@/components/PulsingDot";

function formatSecondsAgo(lastUpdatedAt: number | null): string {
  if (!lastUpdatedAt) {
    return "never";
  }

  const seconds = Math.max(
    0,
    Math.floor((Date.now() - lastUpdatedAt) / 1000),
  );

  return `${seconds} seconds ago`;
}

export function StatusBar({
  lastUpdatedAt,
  autoRefresh,
}: {
  lastUpdatedAt: number | null;
  autoRefresh: boolean;
}) {
  return (
    <footer className="flex flex-col gap-3 rounded-3xl border border-line bg-panel/90 px-5 py-4 text-sm text-slate-400 shadow-panel backdrop-blur md:flex-row md:items-center md:justify-between">
      <div>Last updated: {formatSecondsAgo(lastUpdatedAt)}</div>
      <div className="flex items-center gap-2">
        <PulsingDot active={autoRefresh} colorClass="bg-emerald-400" />
        Auto-refresh: {autoRefresh ? "ON" : "OFF"}
      </div>
      <div>Data refreshes every 10 seconds</div>
    </footer>
  );
}
