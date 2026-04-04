"""
PMIA CryptoValidator — HMAC-SHA256 signing and verification.

Implements §5 of skills/inter-agent-protocol.md:
    - MessageTampered  (bad signature) : no retry → immediate SECURITY_VIOLATION
    - MessageExpired   (TTL exceeded)  : retry with re-sign (max 3, backoff 2 s)
    - MALFORMED_MESSAGE (bad structure): retry protocol §4

The signing key defaults to the PIV_OAC_PMIA_SECRET env var.
In production this MUST be injected via secret management (MCP when available).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import replace
from datetime import datetime, timezone, timedelta

from piv_oac.exceptions import PIVOACError

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MessageTampered(PIVOACError):
    """HMAC signature mismatch — immediate SECURITY_VIOLATION, no retry."""

    def __init__(self, agent_id: str = "unknown") -> None:
        super().__init__(f"PMIA message signature invalid — agent: {agent_id}")
        self.agent_id = agent_id


class MessageExpired(PIVOACError):
    """Message TTL exceeded — re-sign and retry (max 3 attempts)."""

    def __init__(self, age_seconds: float, ttl_seconds: float) -> None:
        super().__init__(
            f"PMIA message expired: age={age_seconds:.1f}s ttl={ttl_seconds:.1f}s"
        )
        self.age_seconds = age_seconds
        self.ttl_seconds = ttl_seconds


# ---------------------------------------------------------------------------
# CryptoValidator
# ---------------------------------------------------------------------------

_DEFAULT_SECRET = os.environ.get("PIV_OAC_PMIA_SECRET", "piv-oac-dev-insecure-key")
_DEFAULT_TTL_SECONDS = 300.0  # 5 minutes


class CryptoValidator:
    """
    Signs and verifies PMIA message envelopes.

    Parameters
    ----------
    secret:
        HMAC key. Defaults to PIV_OAC_PMIA_SECRET env var.
        Must be set to a strong random value in production.
    ttl_seconds:
        How long a signed message remains valid. Defaults to 300 s.
    """

    def __init__(
        self,
        secret: str | None = None,
        ttl_seconds: float = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self._secret = (secret or _DEFAULT_SECRET).encode()
        self._ttl = ttl_seconds

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def sign(self, message_json: str) -> str:
        """
        Compute HMAC-SHA256 of *message_json* and return the hex digest.

        The caller is responsible for embedding this into the ``signature``
        field of the message before transmission.
        """
        return hmac.new(self._secret, message_json.encode(), hashlib.sha256).hexdigest()

    def verify(self, message_json: str, expected_signature: str) -> None:
        """
        Verify the signature and TTL of *message_json*.

        Raises
        ------
        MessageTampered
            If the HMAC does not match.
        MessageExpired
            If the ``timestamp`` field indicates the message is too old.
        """
        # Strip signature field before recomputing digest
        canonical = self._canonical_payload(message_json)
        computed = self.sign(canonical)
        if not hmac.compare_digest(computed, expected_signature):
            try:
                data = json.loads(message_json)
                agent_id = data.get("agent_id") or data.get("from_agent", "unknown")
            except Exception:
                agent_id = "unknown"
            raise MessageTampered(agent_id=agent_id)

        # TTL check
        try:
            data = json.loads(message_json)
            ts = data.get("timestamp", "")
            if ts:
                sent = datetime.fromisoformat(ts)
                age = (datetime.now(timezone.utc) - sent).total_seconds()
                if age > self._ttl:
                    raise MessageExpired(age_seconds=age, ttl_seconds=self._ttl)
        except (ValueError, TypeError):
            pass  # malformed timestamp is handled by schema validation, not here

    def sign_message(self, message_json: str) -> str:
        """
        Compute HMAC over the canonical payload (signature field excluded).
        Returns a new JSON string with ``signature`` populated.
        """
        canonical = self._canonical_payload(message_json)
        sig = self.sign(canonical)
        data = json.loads(message_json)
        data["signature"] = sig
        return json.dumps(data, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _canonical_payload(message_json: str) -> str:
        """Return message JSON with the ``signature`` field removed for signing."""
        try:
            data = json.loads(message_json)
        except json.JSONDecodeError:
            return message_json
        data.pop("signature", None)
        return json.dumps(data, sort_keys=True, ensure_ascii=False)
