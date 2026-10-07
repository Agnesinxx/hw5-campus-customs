"""Append-only audit logging for agent activity."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_TRAIL_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"


def append_audit_event(
    *,
    agent: str,
    action: str,
    detail: str,
    delegation_to: str | None = None,
    mcp_tool: str | None = None,
) -> None:
    """Append an event while preserving all prior JSON-array entries."""
    AUDIT_TRAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if AUDIT_TRAIL_PATH.exists():
        events = json.loads(AUDIT_TRAIL_PATH.read_text(encoding="utf-8"))
    else:
        events = []

    events.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "action": action,
            "detail": detail,
            "delegation_to": delegation_to,
            "mcp_tool": mcp_tool,
        }
    )
    AUDIT_TRAIL_PATH.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
