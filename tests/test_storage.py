"""Tests for the storage module."""

import json
import os
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
import tempfile

# Point state at a temp file during tests
import feed.storage as storage_mod


@pytest.fixture(autouse=True)
def tmp_state(tmp_path):
    state_file = tmp_path / "state.json"
    storage_mod.STATE_PATH = state_file
    yield state_file
    storage_mod.STATE_PATH = Path(os.getenv("FEED_STATE_PATH", Path.home() / ".feed" / "state.json"))


def test_load_returns_defaults_when_missing(tmp_state):
    state = storage_mod.load_state()
    assert state.session_stats.incorporated == 0
    assert state.session_stats.filtered == 0
    assert state.session_stats.quarantined == 0
    assert state.governor_rules == []
    # cursor should be roughly 24h ago
    cursor_dt = datetime.strptime(state.cursor, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - cursor_dt
    assert timedelta(hours=23) < delta < timedelta(hours=25)


def test_load_reads_existing_state(tmp_state):
    data = {
        "cursor": "2026-01-01T00:00:00Z",
        "session_stats": {"incorporated": 3, "filtered": 1, "quarantined": 0},
        "governor_rules": [],
    }
    tmp_state.write_text(json.dumps(data))
    state = storage_mod.load_state()
    assert state.cursor == "2026-01-01T00:00:00Z"
    assert state.session_stats.incorporated == 3
    assert state.session_stats.filtered == 1


def test_save_load_round_trips(tmp_state):
    state = storage_mod.load_state()
    state.cursor = "2026-03-15T12:00:00Z"
    state.session_stats.incorporated = 5
    storage_mod.save_state(state)

    loaded = storage_mod.load_state()
    assert loaded.cursor == "2026-03-15T12:00:00Z"
    assert loaded.session_stats.incorporated == 5


def test_advance_cursor_moves_forward(tmp_state):
    state = storage_mod.load_state()
    state.cursor = "2026-01-01T00:00:00Z"
    storage_mod.advance_cursor(state, "2026-01-02T00:00:00Z")
    assert state.cursor == "2026-01-02T00:00:00Z"


def test_advance_cursor_does_not_move_backward(tmp_state):
    state = storage_mod.load_state()
    state.cursor = "2026-01-02T00:00:00Z"
    storage_mod.advance_cursor(state, "2026-01-01T00:00:00Z")
    assert state.cursor == "2026-01-02T00:00:00Z"


def test_advance_cursor_does_not_move_equal(tmp_state):
    state = storage_mod.load_state()
    state.cursor = "2026-01-01T00:00:00Z"
    storage_mod.advance_cursor(state, "2026-01-01T00:00:00Z")
    assert state.cursor == "2026-01-01T00:00:00Z"


def test_increment_stat_incorporated(tmp_state):
    state = storage_mod.load_state()
    storage_mod.increment_stat(state, "incorporated")
    assert state.session_stats.incorporated == 1
    assert state.session_stats.filtered == 0
    assert state.session_stats.quarantined == 0


def test_increment_stat_filtered(tmp_state):
    state = storage_mod.load_state()
    storage_mod.increment_stat(state, "filtered")
    assert state.session_stats.filtered == 1
    assert state.session_stats.incorporated == 0


def test_increment_stat_quarantined(tmp_state):
    state = storage_mod.load_state()
    storage_mod.increment_stat(state, "quarantined")
    assert state.session_stats.quarantined == 1
