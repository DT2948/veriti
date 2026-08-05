from __future__ import annotations

import logging
import time
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from threading import Lock

logger = logging.getLogger("veriti.performance")


@dataclass(frozen=True)
class MetricEvent:
    operation: str
    duration_ms: float
    outcome: str
    labels: dict[str, str]
    active: int
    peak_active: int


class MetricRegistry:
    def __init__(self, max_events: int = 2000) -> None:
        self._events: deque[MetricEvent] = deque(maxlen=max_events)
        self._lock = Lock()
        self._active = 0
        self._peak_active = 0

    def begin(self) -> float:
        with self._lock:
            self._active += 1
            self._peak_active = max(self._peak_active, self._active)
        return time.perf_counter()

    def finish(self, operation: str, started: float, outcome: str = "success",
               labels: dict[str, str] | None = None) -> MetricEvent:
        with self._lock:
            active = self._active
            self._active = max(0, self._active - 1)
            event = MetricEvent(
                operation, round((time.perf_counter() - started) * 1000, 3),
                outcome, dict(labels or {}), active, self._peak_active,
            )
            self._events.append(event)
        logger.info("performance_metric %s", asdict(event))
        return event

    def record(self, operation: str, duration_ms: float, outcome: str = "success",
               labels: dict[str, str] | None = None) -> MetricEvent:
        with self._lock:
            event = MetricEvent(
                operation, round(duration_ms, 3), outcome, dict(labels or {}),
                self._active, self._peak_active,
            )
            self._events.append(event)
        logger.info("performance_metric %s", asdict(event))
        return event

    def snapshot(self) -> list[MetricEvent]:
        with self._lock:
            return list(self._events)

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    @property
    def peak_active(self) -> int:
        with self._lock:
            return self._peak_active

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._active = 0
            self._peak_active = 0


@dataclass
class CorrelationTiming:
    accepted_at: float
    verification_started_at: float | None = None
    verification_completed_at: float | None = None
    gemini_mode: str = "live"
    fallback_used: bool = False


class CorrelationStore:
    def __init__(self, max_entries: int = 2000) -> None:
        self._entries: OrderedDict[str, CorrelationTiming] = OrderedDict()
        self._max_entries = max_entries
        self._lock = Lock()

    def accepted(self, correlation_id: str, gemini_mode: str) -> None:
        with self._lock:
            self._entries[correlation_id] = CorrelationTiming(time.time(), gemini_mode=gemini_mode)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def started(self, correlation_id: str) -> None:
        with self._lock:
            if entry := self._entries.get(correlation_id):
                entry.verification_started_at = time.time()

    def completed(self, correlation_id: str, fallback_used: bool = False) -> None:
        with self._lock:
            if entry := self._entries.get(correlation_id):
                entry.verification_completed_at = time.time()
                entry.fallback_used = fallback_used

    def get(self, correlation_id: str) -> CorrelationTiming | None:
        with self._lock:
            return self._entries.get(correlation_id)


def classify_exception(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return "timeout"
    if "429" in message or ("rate" in name and "limit" in name):
        return "rate_limited"
    return "error"


registry = MetricRegistry()
correlations = CorrelationStore()
