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
        {
            "group": "blocked",
            "label": "\u25a0 Blocked \u2014 cannot be incorporated (each match scores 10)",
            "rules": [
                "Non-org sender",
                "Shell pipe to interpreter",
                "Destructive rm command",
                "Script tag in body",
            ],
        },
        {
            "group": "flagged",
            "label": "\u25b2 Flagged \u2014 requires your decision (each match scores 2)",
            "rules": [
                "External URL in body",
                "Imperative language + code block",
            ],
        },
        {
            "group": "scoring",
            "label": "\u25cf Scoring",
            "rules": [
                "Score \u2265 10 blocks the memory from being incorporated",
                "Score \u2265 4 flags the memory for review",
            ],
        },
    ]
