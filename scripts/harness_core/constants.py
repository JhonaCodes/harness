"""Shared constants for the Harness runtime."""

from __future__ import annotations

from pathlib import Path


DEFAULT_CONFIG_DIR = Path("~/.harness").expanduser()
DEFAULT_PROJECT_MAP = DEFAULT_CONFIG_DIR / "projects.json"
DEFAULT_GLOBAL_SKILLS = DEFAULT_CONFIG_DIR / "skills.json"

CAPABILITY_KINDS = {"skill", "agent", "doc", "rule", "mcp"}

BEGIN_MARKER = "<!-- BEGIN HARNESS_MANAGED -->"
END_MARKER = "<!-- END HARNESS_MANAGED -->"

DEFAULT_ADAPTERS: dict[str, dict[str, str]] = {
    "agents": {
        "file": "AGENTS.md",
        "name": "Agents Adapter",
        "description": "Tool entrypoint for agents that read AGENTS.md.",
    },
    "claude": {
        "file": "CLAUDE.md",
        "name": "Claude Adapter",
        "description": "Tool entrypoint for Claude-style project instructions.",
    },
    "gemini": {
        "file": "GEMINI.md",
        "name": "Gemini Adapter",
        "description": "Tool entrypoint for Gemini-style project instructions.",
    },
}
