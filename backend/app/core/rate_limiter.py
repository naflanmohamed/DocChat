"""
Rate Limiter
============
Prevents API abuse by limiting requests per user per time window.

Uses a simple in-memory sliding window.
In production with multiple workers, use Redis instead.

Why rate limiting?
- Free LLM APIs have quotas — one user could exhaust them for everyone
- Prevents abuse and runaway costs
- Required for any public-facing API
"""

import time
import logging
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter.

    Example: max_requests=10, window_seconds=60
    → Each user can make 10 requests per 60 seconds.
    → If they exceed that, they get a 429 error.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # user_id → deque of timestamps
        self._requests: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, user_id: str) -> bool:
        """
        Check if a user is within their rate limit.
        Returns True if allowed, False if rate limited.
        """
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            user_requests = self._requests[user_id]

            # Remove timestamps outside the current window
            while user_requests and user_requests[0] < window_start:
                user_requests.popleft()

            if len(user_requests) >= self.max_requests:
                logger.warning(
                    f"Rate limit exceeded for user '{user_id}': "
                    f"{len(user_requests)}/{self.max_requests} "
                    f"requests in {self.window_seconds}s"
                )
                return False

            # Record this request
            user_requests.append(now)
            return True

    def get_remaining(self, user_id: str) -> int:
        """How many requests the user has left in this window."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            user_requests = self._requests[user_id]

            while user_requests and user_requests[0] < window_start:
                user_requests.popleft()

            return max(0, self.max_requests - len(user_requests))

    def get_reset_time(self, user_id: str) -> float:
        """Seconds until the rate limit window resets."""
        with self._lock:
            user_requests = self._requests[user_id]
            if not user_requests:
                return 0
            oldest = user_requests[0]
            return max(0, oldest + self.window_seconds - time.time())


# Global rate limiter instances
# Chat is more expensive (LLM call) so stricter limit
chat_limiter = RateLimiter(max_requests=20, window_seconds=60)
upload_limiter = RateLimiter(max_requests=5, window_seconds=60)