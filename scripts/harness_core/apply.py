"""Apply Harness decisions to project files."""

from __future__ import annotations

import json
import stat
from dataclasses import asdict
from pathlib import Path

from .constants import BEGIN_MARKER, END_MARKER, EXTRA_LLM_ADAPTERS
from .models import Decision
from .rendering import AdapterSelector, HarnessRenderer


class ManagedFileWriter:
    def write(self, path: Path, content: str, dry_run: bool, actions: list[str], conflicts: list[str]) -> None:
        if path.exists():
            current = path.read_text(encoding="utf-8")
            if current == content:
                actions.append(f"unchanged {path}")
                return
            if path.name in {"skills.json", "agents.json", "docs.json", "rules.json", "mcps.json", "memory.json"}:
                actions.append(f"preserve registry {path}")
                return
            if BEGIN_MARKER in current and END_MARKER in current and BEGIN_MARKER in content and END_MARKER in content:
                before = current.split(BEGIN_MARKER)[0].rstrip()
                after = current.split(END_MARKER, 1)[1].lstrip()
                new_heading = self._first_heading(content)
                while new_heading and before.rstrip().endswith(new_heading):
                    before = before.rstrip()[: -len(new_heading)].rstrip()
                merged = (before + "\n\n" if before else "") + content.strip() + ("\n\n" + after if after else "") + "\n"
                actions.append(f"refresh managed file {path}")
                if not dry_run:
                    path.write_text(merged, encoding="utf-8")
                return
            if BEGIN_MARKER in content and END_MARKER in content:
                new_heading = self._first_heading(content)
                if new_heading and new_heading in current:
                    idx = current.index(new_heading)
                    before = current[:idx].rstrip()
                    merged = (before + "\n\n" if before else "") + content.strip() + "\n"
                    actions.append(f"refresh adapter heading {path}")
                else:
                    merged = self._insert_at_top(current, content)
                    actions.append(f"integrate harness into {path}")
                if not dry_run:
                    path.write_text(merged, encoding="utf-8")
                return
            if path.name == ".gitkeep" and current == "":
                actions.append(f"unchanged {path}")
                return
            # Harness-generated file (no markers, no user registry): overwrite.
            actions.append(f"overwrite {path}")
            if not dry_run:
                path.write_text(content, encoding="utf-8")
            return
        actions.append(f"write {path}")
        if dry_run:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if path.name == "init.sh":
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    @staticmethod
    def _first_heading(content: str) -> str:
        for line in content.strip().splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped
        return ""

    @staticmethod
    def _insert_at_top(current: str, content: str) -> str:
        lines = current.splitlines(keepends=True)
        if lines and lines[0].lstrip().startswith("# "):
            tail = "".join(lines[1:]).lstrip()
            return lines[0].rstrip() + "\n\n" + content.strip() + "\n\n" + tail
        return content.strip() + "\n\n" + current.lstrip()


class ApplyReporter:
    def write_report(
        self,
        root: Path,
        decision: Decision,
        actions: list[str],
        conflicts: list[str],
        dry_run: bool,
        adapters: list[dict[str, str]],
    ) -> None:
        payload = {
            "dry_run": dry_run,
            "decision": asdict(decision),
            "adapters": adapters,
            "actions": actions,
            "conflicts": conflicts,
        }
        text = "# Harness Apply Report\n\n```json\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n```\n"
        if dry_run or decision.workflow == "simple":
            print(text)
            return
        target = root / "progress" / "harness_apply_report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


class HarnessApplication:
    def __init__(
        self,
        renderer: HarnessRenderer | None = None,
        adapter_selector: AdapterSelector | None = None,
        writer: ManagedFileWriter | None = None,
        reporter: ApplyReporter | None = None,
    ) -> None:
        self.renderer = renderer or HarnessRenderer()
        self.adapter_selector = adapter_selector or AdapterSelector()
        self.writer = writer or ManagedFileWriter()
        self.reporter = reporter or ApplyReporter()

    def apply(self, root: Path, decision: Decision, dry_run: bool, adapters_raw: str, detect_all_llms: bool = False) -> int:
        adapters = self.adapter_selector.parse(adapters_raw)
        actions: list[str] = []
        conflicts: list[str] = []
        if decision.workflow == "simple":
            actions.append("simple workflow selected; no harness files installed")
            self.reporter.write_report(root, decision, actions, conflicts, dry_run, adapters)
            return 0

        for rel, content in self.renderer.files_for(root, decision.workflow, decision, adapters).items():
            self.writer.write(root / rel, content, dry_run, actions, conflicts)

        if detect_all_llms:
            for entry in EXTRA_LLM_ADAPTERS.values():
                target = root / entry["file"]
                if not target.exists():
                    continue
                content = self.renderer.adapter_entrypoint(entry, decision.workflow, decision)
                self.writer.write(target, content, dry_run, actions, conflicts)

        self.reporter.write_report(root, decision, actions, conflicts, dry_run, adapters)
        return 1 if conflicts else 0
