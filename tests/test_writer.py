"""Tests for the writer module."""

import pytest
from pathlib import Path
from feed.writer import incorporate, DOMAIN_MAP


def test_writes_to_java_file(tmp_path):
    path = incorporate(tmp_path, 41, "alice", "2026-04-03T08:14:00Z", "java", "Use virtual threads.")
    assert path == tmp_path / "language-guidelines" / "java.md"
    assert path.exists()


def test_writes_to_api_file(tmp_path):
    path = incorporate(tmp_path, 42, "bob", "2026-04-03T09:00:00Z", "api", "Always version APIs.")
    assert path == tmp_path / "general-guidelines" / "specs-and-plans.md"
    assert path.exists()


def test_writes_to_testing_file(tmp_path):
    path = incorporate(tmp_path, 43, "carol", "2026-04-03T10:00:00Z", "testing", "No mocks.")
    assert path == tmp_path / "general-guidelines" / "testing.md"
    assert path.exists()


def test_writes_to_general_file(tmp_path):
    path = incorporate(tmp_path, 44, "dave", "2026-04-03T11:00:00Z", "general", "Be pragmatic.")
    assert path == tmp_path / "CLAUDE.md"
    assert path.exists()


def test_writes_to_python_file(tmp_path):
    path = incorporate(tmp_path, 45, "eve", "2026-04-03T12:00:00Z", "python", "Use dataclasses.")
    assert path == tmp_path / "language-guidelines" / "python.md"
    assert path.exists()


def test_writes_to_golang_file(tmp_path):
    path = incorporate(tmp_path, 46, "frank", "2026-04-03T13:00:00Z", "golang", "Prefer table tests.")
    assert path == tmp_path / "language-guidelines" / "golang.md"
    assert path.exists()


def test_writes_to_observability_file(tmp_path):
    path = incorporate(tmp_path, 47, "grace", "2026-04-03T14:00:00Z", "observability", "Log context IDs.")
    assert path == tmp_path / "general-guidelines" / "observability.md"
    assert path.exists()


def test_creates_missing_directories(tmp_path):
    deep_root = tmp_path / "deep" / "nested"
    path = incorporate(deep_root, 48, "alice", "2026-04-03T15:00:00Z", "python", "content")
    assert path.exists()
    assert path.parent.exists()


def test_appends_does_not_overwrite(tmp_path):
    incorporate(tmp_path, 10, "alice", "2026-04-03T08:00:00Z", "general", "First.")
    incorporate(tmp_path, 11, "bob", "2026-04-03T09:00:00Z", "general", "Second.")
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "First." in content
    assert "Second." in content


def test_returns_file_path(tmp_path):
    result = incorporate(tmp_path, 1, "alice", "2026-04-03T00:00:00Z", "java", "tip")
    assert isinstance(result, Path)


def test_block_format(tmp_path):
    incorporate(tmp_path, 41, "akim.k", "2026-04-03T08:14:00Z", "java", "Prefer virtual threads.")
    content = (tmp_path / "language-guidelines" / "java.md").read_text()
    assert "<!-- feed:#41 · akim.k · 2026-04-03T08:14:00Z -->" in content
    assert "Prefer virtual threads." in content
    assert content.count("---") >= 2


def test_incorporate_dynamic_domain_uses_existing_file(tmp_path):
    """incorporate() writes to an existing file for a domain not in DOMAIN_MAP."""
    target = tmp_path / "language-guidelines" / "nodejs.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Node.js\n")

    path = incorporate(tmp_path, 50, "alice", "2026-04-04T10:00:00Z", "nodejs", "Use ESM imports.")
    assert path == target
    assert "Use ESM imports." in target.read_text()


def test_incorporate_dynamic_domain_creates_in_language_guidelines(tmp_path):
    """incorporate() falls back to language-guidelines/<domain>.md for unknown domains."""
    path = incorporate(tmp_path, 51, "bob", "2026-04-04T11:00:00Z", "rust", "Prefer owned types.")
    assert path == tmp_path / "language-guidelines" / "rust.md"
    assert path.exists()
    assert "Prefer owned types." in path.read_text()


def test_incorporate_dynamic_domain_general_guidelines_takes_priority(tmp_path):
    """If the domain file lives in general-guidelines/, use that over creating a new one."""
    target = tmp_path / "general-guidelines" / "security.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Security\n")

    path = incorporate(tmp_path, 52, "carol", "2026-04-04T12:00:00Z", "security", "Hash passwords.")
    assert path == target
    assert "Hash passwords." in target.read_text()
