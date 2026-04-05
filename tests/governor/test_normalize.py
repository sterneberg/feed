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


def test_html_entities_are_decoded():
    assert canonicalize("&lt;script&gt;alert(1)&lt;/script&gt;") == "<script>alert(1)</script>"


def test_percent_encoding_is_decoded():
    assert canonicalize("rm%20-rf%20/tmp") == "rm -rf /tmp"


def test_long_base64_blob_is_decoded_and_appended():
    # "rm -rf /" base64-encoded
    import base64
    blob = base64.b64encode(b"rm -rf /").decode()
    assert len(blob) >= 12
    out = canonicalize(f"See payload: {blob}")
    assert "rm -rf /" in out


def test_short_words_are_not_treated_as_base64():
    # "hello" is technically base64-valid but too short to risk false-decode
    out = canonicalize("hello world")
    assert out == "hello world"


def test_non_decodable_base64ish_is_left_alone():
    # Valid base64 charset but decodes to binary garbage
    out = canonicalize("aaaa bbbb cccc dddd")
    assert "aaaa" in out  # original preserved
