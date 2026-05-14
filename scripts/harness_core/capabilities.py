"""Capability registry loading and selection."""

from __future__ import annotations

from pathlib import Path

from .constants import CAPABILITY_KINDS
from .io import JsonStore
from .models import RepoContext, Skill


class CapabilityRegistry:
    def __init__(self, global_skills_path: Path) -> None:
        self.global_skills_path = global_skills_path

    @staticmethod
    def project_path(root: Path, kind: str) -> Path:
        return root / ".harness" / f"{kind}s.json"

    def global_path(self, kind: str) -> Path:
        if kind == "skill":
            return self.global_skills_path.expanduser()
        return self.global_skills_path.expanduser().parent / f"{kind}s.json"

    def load(self, root: Path, kind: str) -> list[Skill]:
        raw_items: list[object] = []
        plural = f"{kind}s"
        for path in [self.global_path(kind), self.project_path(root, kind)]:
            data = JsonStore.read_object(path, [])
            if isinstance(data, dict):
                data = data.get(plural, [])
            if not isinstance(data, list):
                raise SystemExit(f"{kind.title()} registry must be a list or {{\"{plural}\": [...]}}: {path}")
            raw_items.extend(data)

        capabilities: list[Skill] = []
        for item in raw_items:
            if not isinstance(item, dict) or "name" not in item:
                continue
            triggers = item.get("triggers", [])
            if isinstance(triggers, str):
                triggers = [triggers]
            capabilities.append(
                Skill(
                    name=str(item["name"]),
                    triggers=[str(x).lower() for x in triggers],
                    description=str(item.get("description", "")),
                    path=str(item.get("path", "")),
                    context=str(item.get("context", "")),
                    kind=kind,
                )
            )
        return capabilities

    @staticmethod
    def select(task: str, context: RepoContext, capabilities: list[Skill]) -> list[Skill]:
        haystack = " ".join([task.lower(), context.profile.lower(), " ".join(context.files_sample).lower()])
        return [item for item in capabilities if any(trigger and trigger in haystack for trigger in item.triggers)]

    def select_all(self, task: str, context: RepoContext) -> dict[str, list[Skill]]:
        root = Path(context.root)
        return {
            kind: self.select(task, context, self.load(root, kind))
            for kind in sorted(CAPABILITY_KINDS)
        }


class ProjectRegistry:
    def __init__(self, root: Path, kind: str) -> None:
        if kind not in CAPABILITY_KINDS:
            raise SystemExit(f"Unknown registry kind: {kind}")
        self.root = root
        self.kind = kind
        self.path = CapabilityRegistry.project_path(root, kind)

    @staticmethod
    def parse_triggers(raw: str) -> list[str]:
        return [item.strip().lower() for item in raw.split(",") if item.strip()]

    def add(self, name: str, triggers: str, path: str, description: str = "", context: str = "") -> dict[str, object]:
        if self.kind == "mcp" and not context.strip():
            raise SystemExit("MCP registry entries require --context")
        data = JsonStore.read_object(self.path, [])
        if isinstance(data, dict):
            data = data.get(f"{self.kind}s", [])
        if not isinstance(data, list):
            raise SystemExit(f"{self.kind.title()} registry must be a list: {self.path}")
        entry = {
            "name": name,
            "triggers": self.parse_triggers(triggers),
            "description": description or "",
            "path": path,
        }
        if context:
            entry["context"] = context
        data = [item for item in data if not (isinstance(item, dict) and item.get("name") == name)]
        data.append(entry)
        JsonStore.write(self.path, data)
        return {"project": str(self.root), self.kind: entry}

    def list(self) -> object:
        return JsonStore.read_object(self.path, [])


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".harness" / "memory.json"

    def add(self, key: str, value: str) -> dict[str, str]:
        data = JsonStore.read_object(self.path, {"schema_version": 1, "entries": {}})
        if not isinstance(data, dict):
            raise SystemExit(f"Memory must be a JSON object: {self.path}")
        entries = data.setdefault("entries", {})
        if not isinstance(entries, dict):
            raise SystemExit(f"Memory entries must be a JSON object: {self.path}")
        entries[key] = value
        JsonStore.write(self.path, data)
        return {"project": str(self.root), "key": key, "value": value}

    def list(self) -> object:
        return JsonStore.read_object(self.path, {"schema_version": 1, "entries": {}})
