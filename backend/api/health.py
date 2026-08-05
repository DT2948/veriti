from collections import Counter

from fastapi import APIRouter, HTTPException
from benchmarking.metrics import registry
from benchmarking.statistics import summarize_samples

from config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health_check() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": "veriti",
        "version": "0.1.0",
        "benchmark_mode": settings.benchmark_mode,
        "gemini_mode": settings.gemini_mode,
    }


@router.get("/health/performance")
def performance_summary() -> dict:
    if not settings.benchmark_mode:
        raise HTTPException(status_code=404, detail="Not found")
    events = registry.snapshot()
    operations = {}
    for operation in sorted({event.operation for event in events}):
        selected = [event for event in events if event.operation == operation]
        operations[operation] = {
            **summarize_samples([
                {"duration_ms": event.duration_ms, "success": event.outcome == "success"}
                for event in selected
            ]),
            "outcomes": dict(Counter(event.outcome for event in selected)),
        }
    return {
        "active_requests": max(0, registry.active - 1),
        "peak_active_requests": registry.peak_active,
        "buffered_events": len(events),
        "operations": operations,
    }
