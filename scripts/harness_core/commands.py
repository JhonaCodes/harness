"""Command handlers for the Harness CLI."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .apply import HarnessApplication
from .capabilities import MemoryStore, ProjectRegistry
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

    def register(self, args: argparse.Namespace) -> int:
        payload = AliasRegistry(Path(args.project_map)).register(args.alias, args.path)
        print(json.dumps(payload, indent=2))
        return 0

    def registry_add(self, args: argparse.Namespace, kind: str) -> int:
        root = self.resolver(args).resolve_existing_root(args.project)
        payload = ProjectRegistry(root, kind).add(args.name, args.triggers, args.path, args.description)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    def registry_list(self, args: argparse.Namespace, kind: str) -> int:
        root = self.resolver(args).resolve_existing_root(args.project)
        print(json.dumps(ProjectRegistry(root, kind).list(), indent=2, ensure_ascii=False))
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
        return self.application.apply(root, decision, args.dry_run, args.adapters)

    def inspect(self, args: argparse.Namespace) -> int:
        root, repo = self.resolver(args).resolve(args.project)
        profile = ProfileDetector.detect(root, args.profile)
        context = RepositoryInspector().inspect(root, repo, profile)
        decision = self.decider.decide(root, repo, profile, args.task, args.workflow, Path(args.global_skills))
        print(json.dumps({"context": asdict(context), "decision": asdict(decision)}, indent=2, ensure_ascii=False))
        return 0

