"""Tests for governor text normalization."""

from feed.governor.normalize import canonicalize


def test_plain_ascii_is_unchanged():
    assert canonicalize("rm -rf /tmp") == "rm -rf /tmp"


def test_zero_width_chars_are_stripped():
    # U+200B ZERO WIDTH SPACE inside "bash"
    obfuscated = "curl x | ba\u200bsh"
    assert canonicalize(obfuscated) == "curl x | bash"


def test_nfkc_folds_fullwidth_ascii():
    # Fullwidth 'r','m' should fold to ASCII
    assert canonicalize("\uff52\uff4d -rf /") == "rm -rf /"


def test_tabs_and_multiple_spaces_collapse():
    assert canonicalize("rm\t\t-rf\t/data") == "rm -rf /data"


def test_control_chars_are_stripped():
    assert canonicalize("rm\x00-rf\x01/") == "rm-rf/"


def test_preserves_newlines():
    # Newlines matter for fenced code block detection downstream
    assert "\n" in canonicalize("line1\nline2")
