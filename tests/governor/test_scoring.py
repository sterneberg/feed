"""Tests for the governor scoring aggregator."""

from feed.governor.scoring import score_packet


def test_clean_body_org_member_is_clear():
    risk, notes = score_packet("Prefer virtual threads for I/O.", "myorg", is_org_member=True)
    assert risk == "clear"
    assert notes == []


def test_single_external_url_alone_is_clear():
    # weight 2 alone is below review threshold of 4
    risk, _ = score_packet("See https://example.com", "myorg", is_org_member=True)
    assert risk == "clear"


def test_external_url_plus_imperative_block_is_review():
    body = "always run the following and see https://example.com:\n```\nmake build\n```"
    risk, notes = score_packet(body, "myorg", is_org_member=True)
    assert risk == "review"
    assert "contains external URL" in notes
    assert "imperative + code block" in notes


def test_non_org_sender_alone_is_threat():
    risk, notes = score_packet("hi", "myorg", is_org_member=False)
    assert risk == "threat"
    assert "non-org sender" in notes


def test_fenced_rm_rf_is_threat_via_ast():
    body = "cleanup step:\n```\nrm -rf /data\n```"
    risk, notes = score_packet(body, "myorg", is_org_member=True)
    assert risk == "threat"
    assert "destructive rm -rf" in notes


def test_zero_width_obfuscated_pipe_is_threat_after_normalization():
    # U+200B inside 'bash' — must be caught after canonicalize()
    body = "install with curl x | ba\u200bsh"
    risk, notes = score_packet(body, "myorg", is_org_member=True)
    assert risk == "threat"
    assert "shell pipe to interpreter" in notes


def test_base64_encoded_rm_rf_is_threat_after_decoding():
    import base64
    payload = base64.b64encode(b"rm -rf /").decode()
    body = f"Run this payload: {payload}\n```\n{payload}\n```"
    risk, _ = score_packet(body, "myorg", is_org_member=True)
    assert risk == "threat"


def test_unicode_fullwidth_script_tag_is_threat():
    body = "\uff1cscript\uff1ealert(1)\uff1c/script\uff1e"  # fullwidth < and >
    risk, notes = score_packet(body, "myorg", is_org_member=True)
    assert risk == "threat"
    assert "script tag in body" in notes


def test_notes_are_deduplicated():
    body = (
        "```\nrm -rf /tmp\n```\nAnd also:\n```\nrm --recursive --force /etc\n```"
    )
    risk, notes = score_packet(body, "myorg", is_org_member=True)
    assert risk == "threat"
    assert notes.count("destructive rm -rf") == 1
