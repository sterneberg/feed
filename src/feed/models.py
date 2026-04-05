"""Shared Pydantic models and packet assembly."""

import re
from pathlib import Path
from pydantic import BaseModel
from feed.github import RawIssue, check_org_membership
from feed.governor import classify as governor_classify
from feed.classifier import classify as classify_domain, load_corpus


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
    quarantined_by: str | None = None


def extract_team_brain(body: str) -> str:
    """Return only the content under the '## Team Brain' section, stripped."""
    match = re.search(r"^##\s+Team Brain\s*$", body, re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""
    after = body[match.end():]
    next_heading = re.search(r"^#{1,2}\s", after, re.MULTILINE)
    if next_heading:
        after = after[: next_heading.start()]
    return after.strip()


def _extract_quarantined_by(labels: list) -> str | None:
    """If a 'quarantined:username' label exists, return the username."""
    for label in labels:
        name = label.name if hasattr(label, "name") else label.get("name", "")
        if name.startswith("quarantined:"):
            return name.split(":", 1)[1]
    return None


async def build_packets(
    raw_issues: list[RawIssue],
    org: str,
    token: str,
    knowledge_root: str | Path,
) -> list[Packet]:
    """Fetch org membership per unique sender, classify each issue, return Packets."""
    membership_cache: dict[str, bool] = {}

    for issue in raw_issues:
        login = issue.user.login
        if login not in membership_cache:
            membership_cache[login] = await check_org_membership(org, login, token)

    # Load the domain corpus once per batch — re-reading the knowledge
    # base files for every packet would be wasteful.
    corpus = load_corpus(knowledge_root)

    packets = []
    for issue in raw_issues:
        # Skip issues already incorporated or filtered globally. These
        # are *state* labels, not category labels — the feed still uses
        # them for lifecycle tracking.
        label_names = {
            (l.name if hasattr(l, "name") else l.get("name", ""))
            for l in issue.labels
        }
        if "incorporated" in label_names or "filtered" in label_names:
            continue

        login = issue.user.login
        is_member = membership_cache.get(login, False)
        raw_body = issue.body or ""
        body = extract_team_brain(raw_body) or raw_body
        risk_level, threat_notes = governor_classify(body, login, is_member)
        domain = classify_domain(body, corpus)
        quarantined_by = _extract_quarantined_by(issue.labels)

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
                quarantined_by=quarantined_by,
            )
        )

    return packets
