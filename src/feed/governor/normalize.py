"""Canonicalize packet bodies so pattern matchers see a stable form."""

import re
import unicodedata

# Zero-width and directional formatting characters we strip outright.
_ZERO_WIDTH = {
    "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff",
    "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
}

# Collapse runs of horizontal whitespace (spaces, tabs) but preserve newlines.
_HSPACE_RUN = re.compile(r"[ \t\f\v]+")


def canonicalize(body: str) -> str:
    """
    Return a canonical form of *body* suitable for pattern matching.

    - NFKC unicode folding (fullwidth → ASCII, compatibility forms)
    - Strip zero-width / bidi control characters
    - Strip ASCII control characters except newline
    - Collapse horizontal whitespace runs to a single space
    """
    folded = unicodedata.normalize("NFKC", body)
    cleaned_chars = []
    for ch in folded:
        if ch in _ZERO_WIDTH:
            continue
        if ch in (" ", "\t", "\f", "\v"):
            cleaned_chars.append(ch)
            continue
        if ch == "\n":
            cleaned_chars.append(ch)
            continue
        if unicodedata.category(ch).startswith("C"):
            continue  # other control chars
        cleaned_chars.append(ch)
    cleaned = "".join(cleaned_chars)
    return _HSPACE_RUN.sub(" ", cleaned)
