# confirmation.py
# Server-side confirmation token registry.
# Tokens are generated during preview calls and consumed during execute calls.
# Claude cannot fabricate a valid token - it must come from a preview,
# and the user must provide it back explicitly.

import uuid
import time
from typing import Optional

_pending: dict[str, dict] = {}

TOKEN_TTL_SECONDS = 120


def generate_token(description: str) -> str:
    """Generate a single-use confirmation token and register it server-side."""
    _purge_expired()
    token = uuid.uuid4().hex[:8].upper()
    _pending[token] = {
        "description": description,
        "expires_at": time.time() + TOKEN_TTL_SECONDS,
    }
    return token


def consume_token(token: str) -> Optional[str]:
    """
    Validate and consume a token. Returns the action description on success, None on failure.
    Tokens are single-use and expire after TOKEN_TTL_SECONDS.
    """
    _purge_expired()
    token = token.strip().upper()
    entry = _pending.pop(token, None)
    if entry is None:
        return None
    if time.time() > entry["expires_at"]:
        return None
    return entry["description"]


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, v in _pending.items() if v["expires_at"] < now]
    for k in expired:
        del _pending[k]
