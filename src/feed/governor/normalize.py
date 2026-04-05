"""Canonicalize packet bodies so pattern matchers see a stable form."""

import base64
import binascii
import html
import re
import unicodedata
from urllib.parse import unquote

_ZERO_WIDTH = {
    "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff",
    "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
}
_HSPACE_RUN = re.compile(r"[ \t\f\v]+")

# Match base64-looking tokens that are long enough to plausibly hide a payload.
# Minimum 11 non-padding chars so a 12-char token (11 data + 1 '=') is captured.
_BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/]{11,}={0,2}")
_MIN_PRINTABLE_RATIO = 0.85


def _strip_unicode_noise(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text)
    out = []
    for ch in folded:
        if ch in _ZERO_WIDTH:
            continue
        if ch in (" ", "\t", "\f", "\v"):
            out.append(ch)
            continue
        if ch == "\n":
            out.append(ch)
            continue
        if unicodedata.category(ch).startswith("C"):
            continue
        out.append(ch)
    return "".join(out)


def _try_decode_base64(token: str) -> str | None:
    """Return decoded text if *token* base64-decodes to mostly-printable ASCII."""
    try:
        raw = base64.b64decode(token, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not raw:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
    if printable / len(text) < _MIN_PRINTABLE_RATIO:
        return None
    return text


def _reveal_base64(text: str) -> str:
    """Append decoded payloads after any base64-looking tokens so matchers see them."""
    additions: list[str] = []
    for match in _BASE64_TOKEN.finditer(text):
        decoded = _try_decode_base64(match.group())
        if decoded is not None:
            additions.append(decoded)
    if not additions:
        return text
    return text + "\n" + "\n".join(additions)


def canonicalize(body: str) -> str:
    """
    Return a canonical form of *body* suitable for pattern matching.

    Pipeline:
      1. HTML entity decode
      2. Percent-decode (URL encoding)
      3. NFKC unicode fold + strip zero-width/control chars
      4. Collapse horizontal whitespace
      5. Reveal base64 payloads (append decoded form, keep original)
    """
    decoded = html.unescape(body)
    decoded = unquote(decoded)
    cleaned = _strip_unicode_noise(decoded)
    cleaned = _HSPACE_RUN.sub(" ", cleaned)
    return _reveal_base64(cleaned)
