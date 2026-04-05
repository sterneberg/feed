"""Governor module — risk classification for packets.

Pipeline: canonicalize(body) → weighted signals + shell-AST walk → threshold.
"""

import os
from typing import Literal

from feed.governor.scoring import score_packet

RiskLevel = Literal["clear", "review", "threat"]

_ORG = os.getenv("FEED_GITHUB_ORG", "")


def classify(body: str, sender: str, is_org_member: bool) -> tuple[RiskLevel, list[str]]:
    """
    Classify a packet body. Signature preserved for existing call sites.

    Returns (risk_level, notes).
    """
    return score_packet(body, _ORG, is_org_member)


def get_ruleset() -> list[dict]:
    """Return the active governor ruleset for display in the UI."""
    return [
        {"type": "block", "description": "non-org sender (weight 10)"},
        {"type": "block", "description": "shell pipe to interpreter — regex + AST (weight 10)"},
        {"type": "block", "description": "destructive rm -rf via shell AST (weight 10)"},
        {"type": "block", "description": "script tag in body (weight 10)"},
        {"type": "flag", "description": "external URL in body (weight 2)"},
        {"type": "flag", "description": "imperative language + code block (weight 2)"},
        {"type": "trust", "description": "threat ≥ 10 · review ≥ 4 · clear < 4"},
        {"type": "trust", "description": "body is normalized (unicode, html, base64) before matching"},
    ]
