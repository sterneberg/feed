"""Parse fenced code blocks with bashlex and flag dangerous AST shapes."""

import re

import bashlex

_FENCE = re.compile(r"```[^\n]*\n(.*?)\n```", re.DOTALL)

_INTERPRETERS = {"bash", "sh", "zsh", "ksh", "python", "python3", "node", "perl", "ruby"}
_RECURSIVE_FLAGS = {"-r", "-R", "--recursive"}
_FORCE_FLAGS = {"-f", "--force"}


def extract_code_blocks(body: str) -> list[str]:
    """Return the inner text of every closed ``` fenced block."""
    return _FENCE.findall(body)


def _command_words(node) -> list[str]:
    """Flatten a bashlex 'command' node into its literal word parts."""
    words: list[str] = []
    for part in getattr(node, "parts", []):
        if part.kind == "word":
            words.append(part.word)
    return words


def _is_destructive_rm(words: list[str]) -> bool:
    if not words or words[0] != "rm":
        return False
    flags: set[str] = set()
    for w in words[1:]:
        if w.startswith("--"):
            flags.add(w)
        elif w.startswith("-") and len(w) > 1:
            # combined short flags like -rf, -fr
            for c in w[1:]:
                flags.add(f"-{c}")
    recursive = bool(flags & _RECURSIVE_FLAGS)
    force = bool(flags & _FORCE_FLAGS)
    return recursive and force


def _walk_commands(node, out: list):
    """Collect every bashlex 'command' node under *node*."""
    if getattr(node, "kind", None) == "command":
        out.append(node)
    for child in getattr(node, "parts", []) or []:
        _walk_commands(child, out)
    for child in getattr(node, "list", []) or []:
        _walk_commands(child, out)


def _pipeline_has_interpreter_rhs(node) -> bool:
    """Return True if a pipeline node's last command is an interpreter."""
    if getattr(node, "kind", None) != "pipeline":
        return False
    commands: list = []
    for child in getattr(node, "parts", []):
        if getattr(child, "kind", None) == "command":
            commands.append(child)
    if len(commands) < 2:
        return False
    rhs_words = _command_words(commands[-1])
    return bool(rhs_words) and rhs_words[0] in _INTERPRETERS


def _find_pipelines(node, out: list):
    if getattr(node, "kind", None) == "pipeline":
        out.append(node)
    for child in getattr(node, "parts", []) or []:
        _find_pipelines(child, out)
    for child in getattr(node, "list", []) or []:
        _find_pipelines(child, out)


def find_shell_threats(body: str) -> list[str]:
    """Return threat notes for dangerous shell constructs inside fenced blocks."""
    notes: list[str] = []
    for block in extract_code_blocks(body):
        try:
            trees = bashlex.parse(block)
        except Exception:
            # Unparseable — fall through without a note; regex signals still apply
            continue
        for tree in trees:
            pipelines: list = []
            _find_pipelines(tree, pipelines)
            for pipe in pipelines:
                if _pipeline_has_interpreter_rhs(pipe):
                    note = "pipe to interpreter"
                    if note not in notes:
                        notes.append(note)
            commands: list = []
            _walk_commands(tree, commands)
            for cmd in commands:
                if _is_destructive_rm(_command_words(cmd)):
                    note = "destructive rm -rf"
                    if note not in notes:
                        notes.append(note)
    return notes
