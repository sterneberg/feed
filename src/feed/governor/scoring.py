"""Aggregate normalization + AST + signal detectors into a risk level."""

from typing import Literal

from feed.governor import signals
from feed.governor.normalize import canonicalize
from feed.governor.shell_ast import find_shell_threats

RiskLevel = Literal["clear", "review", "threat"]

_THREAT_THRESHOLD = 10
_REVIEW_THRESHOLD = 4

# Fixed weight for every shell-AST hit
_AST_WEIGHT = 10


def score_packet(
    body: str, org: str, is_org_member: bool
) -> tuple[RiskLevel, list[str]]:
    """
    Return (risk_level, notes) for *body*.

    Pipeline: canonicalize → collect weighted signals → threshold the total.
    """
    canonical = canonicalize(body)

    total = 0
    notes: list[str] = []

    def add(weight: int, note: str | None) -> None:
        nonlocal total
        if weight <= 0 or note is None:
            return
        total += weight
        if note not in notes:
            notes.append(note)

    add(*signals.non_org_sender(is_org_member))
    add(*signals.script_tag(canonical))
    add(*signals.regex_pipe_to_interpreter(canonical))
    add(*signals.rm_rf_prose(canonical))
    add(*signals.curl_wget_external(canonical, org))
    add(*signals.external_url(canonical, org))
    add(*signals.imperative_with_code_block(canonical))

    for ast_note in find_shell_threats(canonical):
        add(_AST_WEIGHT, ast_note)

    if total >= _THREAT_THRESHOLD:
        return "threat", notes
    if total >= _REVIEW_THRESHOLD:
        return "review", notes
    return "clear", notes
