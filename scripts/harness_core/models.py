"""Data models used by Harness runtime services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RepoContext:
    root: str
    repo: str | None
    profile: str
    has_tests: bool
    has_docs: bool
    has_issues_hint: bool
    has_existing_sdd: bool
    files_sample: list[str]


@dataclass
class Skill:
    name: str
    triggers: list[str]
    description: str = ""
    path: str = ""
    context: str = ""
    kind: str = "skill"


@dataclass
class Decision:
    workflow: str
    profile: str
    reason: str
    selected_skills: list[dict[str, Any]]
    selected_capabilities: dict[str, list[dict[str, Any]]]
    will_install_files: bool
    project_root: str
    repo: str | None
    commands: list[str]
