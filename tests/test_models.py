"""Tests for packet assembly and domain extraction."""

import pytest
from unittest.mock import AsyncMock, patch
from feed.models import extract_domain, build_packets, Packet
from feed.github import RawIssue, IssueLabel, IssueUser


def make_labels(*names):
    return [IssueLabel(name=n) for n in names]


def make_issue(number=1, labels=None, login="alice"):
    return RawIssue(
        id=number,
        number=number,
        title="Test issue",
        body="Some content.",
        user=IssueUser(login=login, avatar_url="https://example.com/avatar.png"),
        labels=labels or [],
        created_at="2026-04-03T08:00:00Z",
    )


def test_domain_java():
    labels = make_labels("memory", "java")
    assert extract_domain(labels) == "java"


def test_domain_no_known_label_returns_general():
    labels = make_labels("memory", "unknown-tag")
    assert extract_domain(labels) == "general"


def test_domain_empty_labels_returns_general():
    assert extract_domain([]) == "general"


def test_domain_multiple_labels_picks_first_known():
    labels = make_labels("memory", "python", "java")
    assert extract_domain(labels) == "python"


def test_domain_general_label_returns_general():
    labels = make_labels("memory", "general")
    assert extract_domain(labels) == "general"


@pytest.mark.asyncio
async def test_build_packets_returns_packet_list():
    issue = make_issue(number=41, labels=make_labels("memory", "java"))

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=True)):
        packets = await build_packets([issue], "myorg", "token")

    assert len(packets) == 1
    p = packets[0]
    assert isinstance(p, Packet)
    assert p.sequence_number == 41
    assert p.domain == "java"
    assert p.sender_login == "alice"
    assert p.risk_level == "clear"


@pytest.mark.asyncio
async def test_build_packets_caches_membership_lookup():
    issues = [
        make_issue(number=1, labels=make_labels("java")),
        make_issue(number=2, labels=make_labels("python")),
    ]
    mock_check = AsyncMock(return_value=True)

    with patch("feed.models.check_org_membership", new=mock_check):
        await build_packets(issues, "myorg", "token")

    # Same sender "alice" — membership should only be checked once
    assert mock_check.call_count == 1


@pytest.mark.asyncio
async def test_build_packets_non_member_gets_threat():
    issue = make_issue(number=99, labels=make_labels("java"), login="outsider")

    with patch("feed.models.check_org_membership", new=AsyncMock(return_value=False)):
        packets = await build_packets([issue], "myorg", "token")

    assert packets[0].risk_level == "threat"
    assert "non-org sender" in packets[0].threat_notes
