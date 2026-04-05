"""Tests for packet assembly and content-based domain classification."""

import pytest
from unittest.mock import AsyncMock, patch
from feed.models import build_packets, Packet
from feed.github import RawIssue, IssueLabel, IssueUser


def make_labels(*names):
    return [IssueLabel(name=n) for n in names]


def make_issue(number=1, labels=None, login="alice", body="Some content."):
    return RawIssue(
        id=number,
        number=number,
        title="Test issue",
        body=body,
        user=IssueUser(login=login, avatar_url="https://example.com/avatar.png"),
        labels=labels or [],
        created_at="2026-04-03T08:00:00Z",
    )


@pytest.mark.asyncio
async def test_build_packets_classifies_java_from_body(tmp_path):
    issue = make_issue(
        number=41,
        labels=make_labels("memory"),
        body="In Spring Boot, prefer constructor injection so beans stay testable with JUnit and Mockito.",
    )

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=True)):
        packets = await build_packets([issue], "myorg", "token", tmp_path)

    assert len(packets) == 1
    p = packets[0]
    assert isinstance(p, Packet)
    assert p.sequence_number == 41
    assert p.domain == "java"
    assert p.sender_login == "alice"
    assert p.risk_level == "clear"


@pytest.mark.asyncio
async def test_build_packets_classifies_python_from_body(tmp_path):
    issue = make_issue(
        number=42,
        labels=make_labels("memory"),
        body="FastAPI handlers should be async def; use Pydantic for request validation and uvicorn to serve.",
    )

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=True)):
        packets = await build_packets([issue], "myorg", "token", tmp_path)

    assert packets[0].domain == "python"


@pytest.mark.asyncio
async def test_build_packets_ignores_category_labels(tmp_path):
    """Category labels like 'java' must no longer influence routing."""
    issue = make_issue(
        number=43,
        # Label says java, body screams python — body should win.
        labels=make_labels("memory", "java"),
        body="Use pytest fixtures with async def and asyncio; avoid mocking internal helpers.",
    )

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=True)):
        packets = await build_packets([issue], "myorg", "token", tmp_path)

    assert packets[0].domain != "java"


@pytest.mark.asyncio
async def test_build_packets_ambiguous_body_falls_back_to_general(tmp_path):
    issue = make_issue(
        number=44,
        labels=make_labels("memory"),
        body="Be kind in reviews. Ask questions before proposing rewrites.",
    )

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=True)):
        packets = await build_packets([issue], "myorg", "token", tmp_path)

    assert packets[0].domain == "general"


@pytest.mark.asyncio
async def test_build_packets_caches_membership_lookup(tmp_path):
    issues = [
        make_issue(number=1, body="Goroutines and channels."),
        make_issue(number=2, body="Pytest fixtures and asyncio."),
    ]
    mock_check = AsyncMock(return_value=True)

    with patch("feed.models.check_org_membership", new=mock_check):
        await build_packets(issues, "myorg", "token", tmp_path)

    # Same sender "alice" — membership should only be checked once.
    assert mock_check.call_count == 1


@pytest.mark.asyncio
async def test_build_packets_non_member_gets_threat(tmp_path):
    issue = make_issue(
        number=99,
        login="outsider",
        body="Use virtual threads in Spring Boot.",
    )

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=False)):
        packets = await build_packets([issue], "myorg", "token", tmp_path)

    assert packets[0].risk_level == "threat"
    assert "non-org sender" in packets[0].threat_notes


@pytest.mark.asyncio
async def test_build_packets_skips_incorporated_state_label(tmp_path):
    """`incorporated` is a state label, not a category — still must suppress the packet."""
    issue = make_issue(
        number=50,
        labels=make_labels("memory", "incorporated"),
        body="Use virtual threads.",
    )

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=True)):
        packets = await build_packets([issue], "myorg", "token", tmp_path)

    assert packets == []
