"""Tests for shell code block extraction and AST-based threat detection."""

from feed.governor.shell_ast import extract_code_blocks, find_shell_threats


def test_extract_no_blocks():
    assert extract_code_blocks("plain prose, no fences") == []


def test_extract_single_fenced_block():
    body = "intro\n```\nrm -rf /tmp\n```\ntail"
    assert extract_code_blocks(body) == ["rm -rf /tmp"]


def test_extract_ignores_language_tag():
    body = "```bash\necho hi\n```"
    assert extract_code_blocks(body) == ["echo hi"]


def test_extract_multiple_blocks():
    body = "```\na\n```\nmid\n```sh\nb\n```"
    assert extract_code_blocks(body) == ["a", "b"]


def test_unclosed_fence_is_ignored():
    body = "```\nrm -rf /\nno closing fence"
    assert extract_code_blocks(body) == []
