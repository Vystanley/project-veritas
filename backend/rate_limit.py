"""Shared rate limiter. Uses the caller's IP address as the key.

Tunable per-route with the @limiter.limit("N/unit") decorator. Default limits
(applied to every route unless overridden) are a safety net against runaway
clients hammering any unprotected endpoint.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500/day", "120/hour"],
)
