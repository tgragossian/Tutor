"""Docs check: Markdown files stay <= 100 lines and relative links resolve."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_LINES = 100
SKIP_DIRS = {".git", ".venv", "node_modules", ".superpowers", "test-results", ".claude"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INLINE_CODE = re.compile(r"`+[^`]*`+")
FENCE = re.compile(r"^\s*(```|~~~)")


def _md_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.md") if not SKIP_DIRS.intersection(p.relative_to(root).parts[:-1])
    )


def _links(text: str) -> list[str]:
    found: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        found.extend(LINK.findall(INLINE_CODE.sub("", line)))
    return found


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for path in _md_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        n_lines = len(text.splitlines())
        if n_lines > MAX_LINES:
            problems.append(f"{rel}: {n_lines} lines (max {MAX_LINES})")
        for target in _links(text):
            if re.match(r"(https?:|mailto:)", target, re.IGNORECASE):
                continue
            file_part = target.split("#", 1)[0]
            if not file_part:
                continue
            if not (path.parent / file_part).exists():
                problems.append(f"{rel}: broken link {target}")
    return problems


def main() -> int:
    problems = check(Path.cwd())
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
