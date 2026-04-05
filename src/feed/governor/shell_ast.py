"""Parse fenced code blocks with bashlex and flag dangerous AST shapes."""

import re

_FENCE = re.compile(r"```[^\n]*\n(.*?)\n```", re.DOTALL)


def extract_code_blocks(body: str) -> list[str]:
    """Return the inner text of every closed ``` fenced block."""
    return _FENCE.findall(body)


def find_shell_threats(body: str) -> list[str]:
    """Return a list of threat notes for dangerous shell constructs in fenced blocks."""
    return []  # filled in by the next task
