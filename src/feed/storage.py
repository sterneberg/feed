"""Storage module — manages ~/.feed/state.json."""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pydantic import BaseModel, Field


class StoredPacket(BaseModel):
    id: int
    sequence_number: int
    sender_login: str
    sender_avatar_url: str
    domain: str
    body: str
    created_at: str
    risk_level: str
    threat_notes: list[str] = []


class SessionStats(BaseModel):
    incorporated: int = 0
    filtered: int = 0
    quarantined: int = 0


class State(BaseModel):
    cursor: str = Field(
        default_factory=lambda: (
            datetime.now(timezone.utc) - timedelta(hours=24)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    incorporated_packets: list[StoredPacket] = Field(default_factory=list)
    filtered_packets: list[StoredPacket] = Field(default_factory=list)
    session_stats: SessionStats = Field(default_factory=SessionStats)
    governor_rules: list = Field(default_factory=list)


STATE_PATH = Path(os.getenv("FEED_STATE_PATH", Path.home() / ".feed" / "state.json"))


def load_state() -> State:
    if not STATE_PATH.exists():
        return State()
    try:
        data = json.loads(STATE_PATH.read_text())
        return State(**data)
    except Exception:
        return State()


def save_state(state: State) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=STATE_PATH.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(state.model_dump(), tmp, indent=2)
        tmp.close()
        Path(tmp.name).replace(STATE_PATH)
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise


def advance_cursor(state: State, timestamp: str) -> None:
    """Update cursor only if timestamp is strictly newer."""
    if timestamp > state.cursor:
        state.cursor = timestamp


def increment_stat(state: State, stat: str) -> None:
    """Increment a session counter by name: 'incorporated', 'filtered', or 'quarantined'."""
    setattr(state.session_stats, stat, getattr(state.session_stats, stat) + 1)
