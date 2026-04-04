"""Shared Pydantic models and packet assembly."""

import os
from pydantic import BaseModel
from feed.github import RawIssue, check_org_membership
from feed.governor import classify
from feed.writer import DOMAIN_MAP

_KNOWN_DOMAINS = set(DOMAIN_MAP.keys())


class Packet(BaseModel):
    id: int
    sequence_number: int
    sender_login: str
    sender_avatar_url: str
    domain: str
    body: str
    created_at: str
    risk_level: str
    threat_notes: list[str]


def extract_domain(labels: list) -> str:
    """Return first matching known domain label, or 'general'."""
    for label in labels:
        name = label.name if hasattr(label, "name") else label.get("name", "")
        if name in _KNOWN_DOMAINS and name != "general":
            return name
    return "general"


async def build_packets(
    raw_issues: list[RawIssue],
    org: str,
    token: str,
) -> list[Packet]:
    """Fetch org membership per unique sender, classify each issue, return Packets."""
    # Cache membership lookups
    membership_cache: dict[str, bool] = {}

    for issue in raw_issues:
        login = issue.user.login
        if login not in membership_cache:
            membership_cache[login] = await check_org_membership(org, login, token)

    packets = []
    for i, issue in enumerate(raw_issues):
        login = issue.user.login
        is_member = membership_cache.get(login, False)
        body = issue.body or ""
        risk_level, threat_notes = classify(body, login, is_member)
        domain = extract_domain(issue.labels)

        packets.append(
            Packet(
                id=issue.id,
                sequence_number=issue.number,
                sender_login=login,
                sender_avatar_url=issue.user.avatar_url,
                domain=domain,
                body=body,
                created_at=issue.created_at,
                risk_level=risk_level,
                threat_notes=threat_notes,
            )
        )

    return packets
