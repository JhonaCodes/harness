"""Project alias, repository, and profile resolution."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from .io import JsonStore


class ProjectResolver:
    def __init__(self, checkout_root: Path, project_map: Path) -> None:
        self.checkout_root = checkout_root
        self.project_map = project_map

    @staticmethod
    def parse_repo(value: str) -> str | None:
        patterns = [
            r"^https://github\.com/([^/\s]+/[^/\s#?]+?)(?:\.git)?/?(?:[?#].*)?$",
            r"^git@github\.com:([^/\s]+/[^/\s#?]+?)(?:\.git)?$",
            r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        ]
        for pattern in patterns:
            match = re.match(pattern, value)
            if match:
                repo = match.group(1) if match.groups() else value
                return repo.removesuffix(".git")
        return None

    def resolve(self, project: str | None) -> tuple[Path, str | None]:
        if not project:
            if sys.stdin.isatty():
                project = input("Repo URL, owner/name, alias, or local path: ").strip()
            else:
                raise SystemExit("Missing project. Provide --project with a repo URL, owner/name, alias, or local path.")

        aliases = JsonStore.read_object(self.project_map.expanduser(), {})
        if not isinstance(aliases, dict):
            raise SystemExit(f"Project map must be a JSON object: {self.project_map}")

        if project in aliases:
            return Path(str(aliases[project])).expanduser().resolve(), None

        repo = self.parse_repo(project)
        if repo:
            target = self.checkout_root.expanduser() / repo.split("/", 1)[1]
            if not target.exists():
                self.checkout_root.expanduser().mkdir(parents=True, exist_ok=True)
                subprocess.run(["gh", "repo", "clone", repo, str(target)], check=True)
            return target.resolve(), repo

        return Path(project).expanduser().resolve(), None

    def resolve_existing_root(self, project: str | None) -> Path:
        root, _ = self.resolve(project)
        if not root.is_dir():
            raise SystemExit(f"Project root does not exist or is not a directory: {root}")
        return root


class AliasRegistry:
    def __init__(self, project_map: Path) -> None:
        self.project_map = project_map

    def register(self, alias: str, path: str) -> dict[str, str]:
        if not alias.strip():
            raise SystemExit("Alias cannot be empty")
        root = Path(path).expanduser().resolve()
        if not root.is_dir():
            raise SystemExit(f"Alias path is not a directory: {root}")
        data = JsonStore.read_object(self.project_map.expanduser(), {})
        if not isinstance(data, dict):
            raise SystemExit(f"Project map must be a JSON object: {self.project_map}")
        data[alias] = str(root)
        JsonStore.write(self.project_map.expanduser(), data)
        return {"alias": alias, "path": str(root), "project_map": str(self.project_map.expanduser())}


class ProfileDetector:
    @staticmethod
    def detect(root: Path, requested: str) -> str:
        if requested != "auto":
            return requested
        if (root / "Cargo.toml").exists():
            return "rust"
        if (root / "pubspec.yaml").exists():
            return "flutter"
        if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
            return "python"
        if (root / "package.json").exists():
            return "node"
        return "generic"

