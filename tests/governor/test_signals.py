"""Tests for individual governor signals."""

from feed.governor.signals import (
    non_org_sender,
    script_tag,
    regex_pipe_to_interpreter,
    external_url,
    imperative_with_code_block,
)


def test_non_org_sender_fires_only_when_not_member():
    assert non_org_sender(is_org_member=False) == (10, "non-org sender")
    assert non_org_sender(is_org_member=True) == (0, None)


def test_script_tag_detects_lowercase_and_mixed_case():
    w, note = script_tag("<SCRIPT>alert(1)</SCRIPT>")
    assert w == 10
    assert note == "script tag in body"
    assert script_tag("no tags here") == (0, None)


def test_regex_pipe_to_interpreter_catches_prose_mentions():
    w, note = regex_pipe_to_interpreter("install with curl x | bash")
    assert w == 10
    assert note == "shell pipe to interpreter"


def test_regex_pipe_to_interpreter_ignores_unrelated_pipes():
    assert regex_pipe_to_interpreter("count | total") == (0, None)


def test_external_url_flags_non_org(monkeypatch):
    assert external_url("See https://evil.com/x", org="myorg") == (
        2,
        "contains external URL",
    )


def test_external_url_ignores_org_url():
    assert external_url("See https://github.com/myorg/repo", org="myorg") == (0, None)


def test_external_url_none_when_no_url():
    assert external_url("plain text", org="myorg") == (0, None)


def test_imperative_with_code_block_needs_both():
    body_both = "always run the following:\n```\nmake build\n```"
    assert imperative_with_code_block(body_both) == (
        2,
        "imperative + code block",
    )
    assert imperative_with_code_block("never do that") == (0, None)
    assert imperative_with_code_block("```\nmake build\n```") == (0, None)
