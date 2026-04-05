"""Writer module — appends incorporated packets to CLAUDE.md files."""

from pathlib import Path

DOMAIN_MAP: dict[str, str] = {
    "java": "language-guidelines/java.md",
    "python": "language-guidelines/python.md",
    "golang": "language-guidelines/golang.md",
    "api": "general-guidelines/specs-and-plans.md",
    "testing": "general-guidelines/testing.md",
    "observability": "general-guidelines/observability.md",
    "nodejs": "language-guidelines/nodejs.md",
    "general": "CLAUDE.md",
}


def _resolve_domain_path(root: Path, domain: str) -> Path:
    """
    Resolve a domain key to an absolute target path.

    Built-in domains use DOMAIN_MAP. For anything else (files created by
    the dreamer), we scan language-guidelines/ then general-guidelines/
    for an existing file whose stem matches the domain key. If nothing
    exists yet, we default to language-guidelines/<domain>.md.
    """
    if domain in DOMAIN_MAP:
        return root / DOMAIN_MAP[domain]

    for subdir in ("language-guidelines", "general-guidelines"):
        candidate = root / subdir / f"{domain}.md"
        if candidate.exists():
            return candidate

    return root / "language-guidelines" / f"{domain}.md"


def incorporate(
    knowledge_root: str | Path,
    issue_number: int,
    sender: str,
    created_at: str,
    domain: str,
    body: str,
) -> Path:
    """
    Append a formatted packet block to the appropriate CLAUDE.md file.

    Returns the path that was written to.
    """
    root = Path(knowledge_root).expanduser().resolve()
    target = _resolve_domain_path(root, domain)

    target.parent.mkdir(parents=True, exist_ok=True)

    block = (
        f"\n---\n"
        f"<!-- feed:#{issue_number} · {sender} · {created_at} -->\n"
        f"{body}\n"
        f"---\n"
    )

    with target.open("a", encoding="utf-8") as f:
        f.write(block)

    print(f"Incorporated #{issue_number} into {target}")
    return target


def remove(
    knowledge_root: str | Path,
    issue_number: int,
    domain: str,
) -> Path | None:
    """
    Remove the feed block for the given issue number from the appropriate file.

    Returns the path that was modified, or None if not found.
    """
    import re

    root = Path(knowledge_root).expanduser().resolve()
    target = _resolve_domain_path(root, domain)

    if not target.exists():
        return None

    content = target.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\n?---\n<!-- feed:#" + str(issue_number) + r" ·.*?-->\n.*?\n---\n",
        re.DOTALL,
    )
    new_content = pattern.sub("", content)
    if new_content == content:
        return None

    target.write_text(new_content, encoding="utf-8")
    print(f"Removed #{issue_number} from {target}")
    return target
