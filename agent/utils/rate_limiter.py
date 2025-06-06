"""
Rate limiter for API calls to respect quotas.
"""

import time
import threading
from collections import deque
from typing import Dict, Optional


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    """
    
    def __init__(self, requests_per_minute: int = 10):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_times = deque()
        self._lock = threading.Lock()
    
    def wait_if_needed(self) -> None:
        """
        Wait if necessary to respect rate limits.
        """
        with self._lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            
            # If we're at the limit, wait until the oldest request expires
            if len(self.request_times) >= self.requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0]) + 0.1  # Add small buffer
                if sleep_time > 0:
                    print(f"[RateLimiter] Rate limit reached. Waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
            
            # Record this request
            self.request_times.append(time.time())


# Global rate limiters per provider
_rate_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(provider: str, is_free_tier: bool = True) -> Optional[RateLimiter]:
    """
    Get rate limiter for a provider.
    
    Args:
        provider: Provider name (e.g., "google", "openai")
        is_free_tier: Whether using free tier
        
    Returns:
        Rate limiter instance or None if no limiting needed
    """
    if not is_free_tier:
        return None  # No rate limiting for paid tiers
    
    if provider == "google":
        if "google_free" not in _rate_limiters:
            _rate_limiters["google_free"] = RateLimiter(requests_per_minute=10)
        return _rate_limiters["google_free"]
    
    return None  # No rate limiting for other providers yet