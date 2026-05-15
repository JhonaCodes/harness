"""Shared constants for the Harness runtime."""

from __future__ import annotations

from pathlib import Path


__version__ = "0.1.0"

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

# Known LLM/agent rule files that harness scans for at install time.
# When --detect-all-llms is passed, harness injects a managed Harness block
# into any of these files that already exist in the project.
EXTRA_LLM_ADAPTERS: dict[str, dict[str, str]] = {
    "cursor-legacy": {
        "file": ".cursorrules",
        "name": "Cursor Rules Adapter",
        "description": "Cursor legacy rules file.",
    },
    "cursor": {
        "file": ".cursor/rules/harness.mdc",
        "name": "Cursor Rules Adapter",
        "description": "Cursor modern rules entry.",
    },
    "windsurf": {
        "file": ".windsurfrules",
        "name": "Windsurf Rules Adapter",
        "description": "Windsurf rules file.",
    },
    "junie": {
        "file": ".junie/guidelines.md",
        "name": "Junie Guidelines Adapter",
        "description": "JetBrains Junie guidelines.",
    },
    "roo": {
        "file": ".roo/rules/harness.md",
        "name": "Roo Rules Adapter",
        "description": "Roo Code rules entry.",
    },
}
