"""Governor module — risk classification for packets."""

import os
import re
from typing import Literal

RiskLevel = Literal["clear", "review", "threat"]

_ORG = os.getenv("FEED_GITHUB_ORG", "")

# Patterns that trigger THREAT
_THREAT_PATTERNS = [
    (re.compile(r"\|\s*(bash|sh|zsh)\b"), "command injection detected"),
    (re.compile(r"\brm\s+-rf\b"), "command injection detected"),
    (re.compile(r"<script[\s>]", re.IGNORECASE), "command injection detected"),
    (re.compile(r"\b(curl|wget)\s+https?://", re.IGNORECASE), "command injection detected"),
]

# Patterns that trigger REVIEW
_IMPERATIVE_KEYWORDS = re.compile(
    r"\b(do not|never|always run|execute)\b", re.IGNORECASE
)
_CODE_BLOCK = re.compile(r"```")
_EXTERNAL_URL = re.compile(r"https?://[^\s]+")


def _is_external_url(url: str, org: str) -> bool:
    """Return True if URL is not a github.com/{org} URL."""
    if not org:
        return True
    allowed_prefix = f"https://github.com/{org}"
    return not url.startswith(allowed_prefix)


def classify(body: str, sender: str, is_org_member: bool) -> tuple[RiskLevel, list[str]]:
    """
    Classify a packet body.

    Returns (risk_level, threat_notes).
    Highest severity wins: threat > review > clear.
    """
    notes: list[str] = []
    risk: RiskLevel = "clear"

    def upgrade(level: RiskLevel, note: str):
        nonlocal risk
        if note not in notes:
            notes.append(note)
        severity = {"clear": 0, "review": 1, "threat": 2}
        if severity[level] > severity[risk]:
            risk = level

    # Rule 1: non-org sender
    if not is_org_member:
        upgrade("threat", "non-org sender")

    # Rule 2: threat body patterns
    for pattern, note in _THREAT_PATTERNS:
        if pattern.search(body):
            upgrade("threat", note)

    # Rule 3: external URLs
    org = _ORG
    for match in _EXTERNAL_URL.finditer(body):
        url = match.group()
        if _is_external_url(url, org):
            upgrade("review", "contains external URL")
            break

    # Rule 4: imperative language + code block
    if _IMPERATIVE_KEYWORDS.search(body) and _CODE_BLOCK.search(body):
        upgrade("review", "contains executable instructions, verify intent")

    return risk, notes


def get_ruleset() -> list[dict]:
    """Return the active governor ruleset for display in the UI."""
    return [
        {"type": "block", "description": "non-org sender"},
        {"type": "block", "description": "shell pipe: | bash / | sh / | zsh"},
        {"type": "block", "description": "destructive command: rm -rf"},
        {"type": "block", "description": "script injection: <script>"},
        {"type": "block", "description": "curl/wget to external URL"},
        {"type": "flag", "description": "external URL in body"},
        {"type": "flag", "description": "imperative language + code block"},
        {"type": "trust", "description": "org member, no suspicious content"},
    ]
