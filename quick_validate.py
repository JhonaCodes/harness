#!/usr/bin/env python3
"""Quick repository validation for the universal harness runtime."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


PRIVATE_PATTERNS = [
    "Aulamas",
    "JhonacodeProjects",
    "/Volumes/Data/Private/Projects/JhonacodeProjects",
    "/Users/jhonacode",
    "aulamas_api",
    "nui-app",
    "connect_migration",
]


REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "install.sh",
    "scripts/harness.py",
    "workflows/simple.md",
    "workflows/tdd.md",
    "workflows/sdd.md",
    "workflows/audit.md",
    "tests/test_harness.py",
]


def check_required(root: Path, errors: list[str]) -> None:
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")


def check_skill_frontmatter(root: Path, errors: list[str]) -> None:
    skill = root / "SKILL.md"
    if not skill.exists():
        return
    text = skill.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append("SKILL.md missing frontmatter")
        return
    parts = text.split("---", 2)
    if len(parts) < 3:
        errors.append("SKILL.md frontmatter is not closed")
        return
    meta = parts[1]
    if not re.search(r"^name:\s*harness\s*$", meta, re.M):
        errors.append("SKILL.md frontmatter missing name: harness")
    if not re.search(r"^description:\s*.+$", meta, re.M):
        errors.append("SKILL.md frontmatter missing description")


def check_python(root: Path, errors: list[str]) -> None:
    for rel in ["scripts/harness.py", "quick_validate.py"]:
        path = root / rel
        if not path.exists():
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{rel} syntax error: {exc}")


def check_private_refs(root: Path, errors: list[str]) -> None:
    ignored = {".git", "__pycache__"}
    for path in root.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.name == "quick_validate.py":
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in PRIVATE_PATTERNS:
            if pattern in text:
                errors.append(f"private reference '{pattern}' in {path.relative_to(root)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Quick validate the harness repository.")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    errors: list[str] = []
    check_required(root, errors)
    check_skill_frontmatter(root, errors)
    check_python(root, errors)
    check_private_refs(root, errors)
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("[OK] harness quick validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
