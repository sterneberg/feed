"""Writer module — appends incorporated packets to CLAUDE.md files."""

from pathlib import Path

DOMAIN_MAP: dict[str, str] = {
    "java": "language-guidelines/java.md",
    "python": "language-guidelines/python.md",
    "golang": "language-guidelines/golang.md",
    "api": "general-guidelines/specs-and-plans.md",
    "testing": "general-guidelines/testing.md",
    "observability": "general-guidelines/observability.md",
    "general": "CLAUDE.md",
}


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
    relative = DOMAIN_MAP.get(domain, DOMAIN_MAP["general"])
    target = root / relative

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
