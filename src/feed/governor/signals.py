"""Individual signal detectors. Each returns (weight, note_or_none)."""

import re

Signal = tuple[int, str | None]

_SCRIPT_TAG = re.compile(r"<script[\s>]", re.IGNORECASE)
_PIPE_INTERPRETER = re.compile(r"\|\s*(bash|sh|zsh|python3?|node|perl|ruby)\b")
_EXTERNAL_URL = re.compile(r"https?://[^\s]+")
_IMPERATIVE = re.compile(r"\b(do not|never|always run|execute)\b", re.IGNORECASE)
_CODE_FENCE = re.compile(r"```")


def non_org_sender(is_org_member: bool) -> Signal:
    if not is_org_member:
        return 10, "non-org sender"
    return 0, None


def script_tag(body: str) -> Signal:
    if _SCRIPT_TAG.search(body):
        return 10, "script tag in body"
    return 0, None


def regex_pipe_to_interpreter(body: str) -> Signal:
    """Prose-level fallback; the shell-AST module handles fenced blocks precisely."""
    if _PIPE_INTERPRETER.search(body):
        return 10, "shell pipe to interpreter"
    return 0, None


def external_url(body: str, org: str) -> Signal:
    allowed_prefix = f"https://github.com/{org}" if org else None
    for match in _EXTERNAL_URL.finditer(body):
        url = match.group()
        if allowed_prefix and url.startswith(allowed_prefix):
            continue
        return 2, "contains external URL"
    return 0, None


def imperative_with_code_block(body: str) -> Signal:
    if _IMPERATIVE.search(body) and _CODE_FENCE.search(body):
        return 2, "imperative + code block"
    return 0, None
