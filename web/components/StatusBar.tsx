"use client";

import { useEffect, useState } from "react";

function formatSecondsAgo(lastUpdatedAt: number | null, now: number): string {
  if (!lastUpdatedAt) {
    return "never";
  }

  const seconds = Math.max(
    0,
    Math.floor((now - lastUpdatedAt) / 1000),
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
  void autoRefresh;
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, []);

  return (
    <footer className="flex h-6 items-center justify-end border-t border-line px-3 text-[11px] text-slate-500/90">
      <div>Last updated {formatSecondsAgo(lastUpdatedAt, now)}</div>
    </footer>
  );
}
