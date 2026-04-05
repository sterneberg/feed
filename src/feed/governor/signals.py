"""Individual signal detectors. Each returns (weight, note_or_none)."""

import re

Signal = tuple[int, str | None]

_SCRIPT_TAG = re.compile(r"<script[\s>]", re.IGNORECASE)
_PIPE_INTERPRETER = re.compile(r"\|\s*(bash|sh|zsh|python3?|node|perl|ruby)\b")
_EXTERNAL_URL = re.compile(r"https?://[^\s]+")
_IMPERATIVE = re.compile(r"\b(do not|never|always run|execute)\b", re.IGNORECASE)
_CODE_FENCE = re.compile(r"```")
_RM_RF_PROSE = re.compile(
    r"\brm\s+(?:-[a-zA-Z]*[rR][a-zA-Z]*[fF][a-zA-Z]*"
    r"|-[a-zA-Z]*[fF][a-zA-Z]*[rR][a-zA-Z]*"
    r"|--recursive\s+--force|--force\s+--recursive)\b"
)
_CURL_EXTERNAL = re.compile(r"\b(?:curl|wget)\s+https?://", re.IGNORECASE)


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


def rm_rf_prose(body: str) -> Signal:
    """Prose-level fallback for bare 'rm -rf' mentions outside fences."""
    if _RM_RF_PROSE.search(body):
        return 10, "destructive rm -rf"
    return 0, None


def curl_wget_external(body: str, org: str) -> Signal:
    """Fetching an external URL with curl/wget is a strong threat signal."""
    match = _CURL_EXTERNAL.search(body)
    if not match:
        return 0, None
    # cheap check: does the matched URL belong to the org?
    if org and f"https://github.com/{org}" in body[match.start() : match.end() + 200]:
        return 0, None
    return 10, "curl/wget fetch of external URL"
