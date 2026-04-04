"""
piv_oac.pmia — Protocolo de Mensaje Inter-Agente (PMIA).

Public surface
--------------
PMIABus             — in-process asyncio message bus
CryptoValidator     — HMAC-SHA256 signing and verification
GateVerdictMessage  — verdict from a control gate agent
EscalationMessage   — escalation to orchestrator or human
CrossAlertMessage   — lateral alert between control agents
CheckpointReqMessage — preventive checkpoint request
MalformedMessageResponse — returned on invalid message structure
MessageTampered     — raised on HMAC mismatch (no retry)
MessageExpired      — raised on TTL exceeded (retry with re-sign)
CROSS_ALERT_AUTHORIZED — frozenset of agents that may emit CROSS_ALERT
"""

from piv_oac.pmia.bus import PMIABus
from piv_oac.pmia.crypto import CryptoValidator, MessageTampered, MessageExpired
from piv_oac.pmia.message import (
    GateVerdictMessage,
    EscalationMessage,
    CrossAlertMessage,
    CheckpointReqMessage,
    MalformedMessageResponse,
    IssueEntry,
    ControlEnvironmentState,
    CROSS_ALERT_AUTHORIZED,
    MAX_TOKENS_PER_MESSAGE,
)

__all__ = [
    "PMIABus",
    "CryptoValidator",
    "MessageTampered",
    "MessageExpired",
    "GateVerdictMessage",
    "EscalationMessage",
    "CrossAlertMessage",
    "CheckpointReqMessage",
    "MalformedMessageResponse",
    "IssueEntry",
    "ControlEnvironmentState",
    "CROSS_ALERT_AUTHORIZED",
    "MAX_TOKENS_PER_MESSAGE",
]
