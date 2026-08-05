export type PerformanceOutcome = "success" | "error" | "skipped";

export interface PerformanceEvent {
  operation: string;
  durationMs: number;
  outcome: PerformanceOutcome;
  active: number;
  peakActive: number;
}

const enabled = process.env.NEXT_PUBLIC_PERFORMANCE_METRICS === "true";
const events: PerformanceEvent[] = [];
let active = 0;
let peakActive = 0;

if (enabled && typeof window !== "undefined") {
  (
    window as Window & {
      __VERITI_PERFORMANCE_EVENTS__?: readonly PerformanceEvent[];
    }
  ).__VERITI_PERFORMANCE_EVENTS__ = events;
}

export function beginPerformanceEvent(): number {
  active += 1;
  peakActive = Math.max(peakActive, active);
  return performance.now();
}

export function finishPerformanceEvent(
  operation: string,
  started: number,
  outcome: PerformanceOutcome,
): void {
  const event = {
    operation,
    durationMs: Number((performance.now() - started).toFixed(3)),
    outcome,
    active,
    peakActive,
  };
  active = Math.max(0, active - 1);
  if (!enabled) return;
  events.push(event);
  if (events.length > 500) events.shift();
}

export function recordPerformanceDuration(
  operation: string,
  durationMs: number,
  outcome: PerformanceOutcome = "success",
): void {
  if (!enabled) return;
  events.push({ operation, durationMs, outcome, active, peakActive });
  if (events.length > 500) events.shift();
}

export function getPerformanceEvents(): readonly PerformanceEvent[] {
  return events;
}
