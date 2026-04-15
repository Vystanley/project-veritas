"""Shared rate limiter. Uses the caller's IP address as the key.

Tunable per-route with the @limiter.limit("N/unit") decorator. Default limits
(applied to every route unless overridden) are a safety net against runaway
clients hammering any unprotected endpoint.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Default limits are deliberately generous. Sensitive endpoints (signup,
# login, demo fact-check) apply stricter limits via @limiter.limit(...) so
# the global default only acts as a last-line safety net against runaway
# clients hammering unprotected endpoints.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5000/day", "600/hour"],
)
