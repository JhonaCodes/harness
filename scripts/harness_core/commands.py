"""Command handlers for the Harness CLI."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .apply import HarnessApplication
from .capabilities import MemoryStore, ProjectRegistry
from .constants import CAPABILITY_KINDS
from .decisioning import WorkflowDecider
from .inspection import RepositoryInspector
from .projects import AliasRegistry, ProfileDetector, ProjectResolver


class HarnessCommands:
    def __init__(self, decider: WorkflowDecider | None = None, application: HarnessApplication | None = None) -> None:
        self.decider = decider or WorkflowDecider()
        self.application = application or HarnessApplication()

    @staticmethod
    def resolver(args: argparse.Namespace) -> ProjectResolver:
        return ProjectResolver(Path(args.checkout_root), Path(args.project_map))

    @staticmethod
    def triggers_from_name(name: str) -> str:
        tokens = [tok for tok in name.replace("-", "_").split("_") if tok]
        seen: list[str] = []
        for tok in [name.lower(), *tokens]:
            if tok and tok not in seen:
                seen.append(tok)
        return ",".join(seen)

    def register(self, args: argparse.Namespace) -> int:
        payload = AliasRegistry(Path(args.project_map)).register(args.alias, args.path)
        print(json.dumps(payload, indent=2))
        return 0

    def _resolve_registry_args(self, args: argparse.Namespace, kind: str) -> tuple[str, str, str, str, str]:
        name = args.name or getattr(args, "name_pos", None)
        path = args.path or getattr(args, "path_pos", None)
        if not name:
            raise SystemExit(f"{kind} add requires a name (positional or --name).")
        if not path:
            raise SystemExit(f"{kind} add requires a path (positional or --path).")
        triggers = args.triggers if args.triggers is not None else self.triggers_from_name(name)
        description = args.description or ""
        context = getattr(args, "context", "") or ""
        if getattr(args, "_require_context", False) and not context.strip():
            raise SystemExit(f"{kind} add requires --context (this registry type stores context).")
        return name, triggers, path, description, context

    def registry_add(self, args: argparse.Namespace, kind: str) -> int:
        root = self.resolver(args).resolve_existing_root(args.project)
        name, triggers, path, description, context = self._resolve_registry_args(args, kind)
        payload = ProjectRegistry(root, kind).add(name, triggers, path, description, context)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    def registry_list(self, args: argparse.Namespace, kind: str) -> int:
        root = self.resolver(args).resolve_existing_root(args.project)
        print(json.dumps(ProjectRegistry(root, kind).list(), indent=2, ensure_ascii=False))
        return 0

    def bulk_import(self, args: argparse.Namespace) -> int:
        source = Path(args.file).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"Import file not found: {source}")
        raw = source.read_text(encoding="utf-8")
        entries: object
        if source.suffix in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:
                raise SystemExit(
                    "PyYAML is required to import YAML files. Install with `pip install pyyaml` or convert to JSON."
                ) from exc
            entries = yaml.safe_load(raw)
        else:
            entries = json.loads(raw)
        if not isinstance(entries, list):
            raise SystemExit("Import file must contain a list of entries.")
        root = self.resolver(args).resolve_existing_root(args.project)
        results: list[dict[str, object]] = []
        for idx, item in enumerate(entries):
            if not isinstance(item, dict):
                raise SystemExit(f"Entry #{idx} must be an object.")
            kind = str(item.get("kind", "")).strip().lower()
            if kind not in CAPABILITY_KINDS:
                raise SystemExit(f"Entry #{idx} has invalid or missing `kind`: {kind!r}. Valid: {sorted(CAPABILITY_KINDS)}")
            name = str(item.get("name", "")).strip()
            path = str(item.get("path", "")).strip()
            if not name or not path:
                raise SystemExit(f"Entry #{idx} ({kind}) requires `name` and `path`.")
            triggers_raw = item.get("triggers", "")
            if isinstance(triggers_raw, list):
                triggers = ",".join(str(t) for t in triggers_raw)
            else:
                triggers = str(triggers_raw or self.triggers_from_name(name))
            description = str(item.get("description", "") or "")
            context = str(item.get("context", "") or "")
            if kind == "mcp" and not context.strip():
                raise SystemExit(f"Entry #{idx} (mcp) requires `context`.")
            payload = ProjectRegistry(root, kind).add(name, triggers, path, description, context)
            results.append(payload)
        print(json.dumps({"imported": len(results), "entries": results}, indent=2, ensure_ascii=False))
        return 0

    def memory_add(self, args: argparse.Namespace) -> int:
        root = self.resolver(args).resolve_existing_root(args.project)
        payload = MemoryStore(root).add(args.key, args.value)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    def memory_list(self, args: argparse.Namespace) -> int:
        root = self.resolver(args).resolve_existing_root(args.project)
        print(json.dumps(MemoryStore(root).list(), indent=2, ensure_ascii=False))
        return 0

    def run(self, args: argparse.Namespace) -> int:
        root, repo = self.resolver(args).resolve(args.project)
        profile = ProfileDetector.detect(root, args.profile)
        decision = self.decider.decide(root, repo, profile, args.task, args.workflow, Path(args.global_skills))
        print(json.dumps(asdict(decision), indent=2, ensure_ascii=False))
        return self.application.apply(
            root,
            decision,
            args.dry_run,
            args.adapters,
            detect_all_llms=getattr(args, "detect_all_llms", False),
        )

    def inspect(self, args: argparse.Namespace) -> int:
        root, repo = self.resolver(args).resolve(args.project)
        profile = ProfileDetector.detect(root, args.profile)
        context = RepositoryInspector().inspect(root, repo, profile)
        decision = self.decider.decide(root, repo, profile, args.task, args.workflow, Path(args.global_skills))
        print(json.dumps({"context": asdict(context), "decision": asdict(decision)}, indent=2, ensure_ascii=False))
        return 0
