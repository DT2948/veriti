import time
from collections import defaultdict


class RateLimiter:
    """
    Simple in-memory rate limiter based on client IP.

    Privacy note: We use IP only for rate limiting. IPs are NOT stored
    alongside submissions and are NOT logged to any persistent storage.
    The rate limiter only keeps IPs in memory temporarily and they are
    never written to the database.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 300):
        """Allow max_requests per window_seconds per IP."""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = defaultdict(list)

    def _prune(self, client_ip: str) -> None:
        now = time.time()
        self._requests[client_ip] = [
            timestamp
            for timestamp in self._requests[client_ip]
            if now - timestamp < self.window_seconds
        ]

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed. Clean old entries."""
        self._prune(client_ip)
        if len(self._requests[client_ip]) >= self.max_requests:
            return False
        self._requests[client_ip].append(time.time())
        return True

    def remaining(self, client_ip: str) -> int:
        """Return how many requests remain in the window."""
        self._prune(client_ip)
        return max(0, self.max_requests - len(self._requests[client_ip]))


upload_rate_limiter = RateLimiter(max_requests=5, window_seconds=300)
