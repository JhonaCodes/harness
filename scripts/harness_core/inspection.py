"""Repository inspection and workflow classification."""

from __future__ import annotations

import re
from pathlib import Path

from .models import RepoContext


class RepositoryInspector:
    ignored_dirs = {".git", "target", "build", "dist", ".dart_tool", "node_modules", "__pycache__", ".venv"}

    def __init__(self, limit: int = 220) -> None:
        self.limit = limit

    def discover_files(self, root: Path) -> list[str]:
        out: list[str] = []
        for path in root.rglob("*"):
            if len(out) >= self.limit:
                break
            if any(part in self.ignored_dirs for part in path.parts):
                continue
            if path.is_file():
                out.append(str(path.relative_to(root)))
        return sorted(out)

    def inspect(self, root: Path, repo: str | None, profile: str) -> RepoContext:
        if not root.is_dir():
            raise SystemExit(f"Project root does not exist or is not a directory: {root}")
        files = self.discover_files(root)
        tests = [f for f in files if re.search(r"(^|/)(tests?|__tests__)/|test_|_test|\\.spec\\.", f, re.I)]
        docs = [
            f
            for f in files
            if f.lower().startswith(("docs/", "documentation/")) or Path(f).name.lower() in {"readme.md", "agents.md"}
        ]
        issues_hint = bool(repo or any(name in files for name in [".github/ISSUE_TEMPLATE.md", ".github/ISSUE_TEMPLATE/config.yml"]))
        existing_sdd = (root / "feature_list.json").exists() or (root / "specs").exists()
        return RepoContext(
            root=str(root),
            repo=repo,
            profile=profile,
            has_tests=bool(tests),
            has_docs=bool(docs),
            has_issues_hint=issues_hint,
            has_existing_sdd=existing_sdd,
            files_sample=files[:80],
        )


class WorkflowClassifier:
    @staticmethod
    def normalize_words(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9_+-]+", text.lower()))

    def classify(self, task: str, context: RepoContext, forced: str) -> tuple[str, str]:
        if forced != "auto":
            return forced, f"Workflow forced by --workflow={forced}."

        words = self.normalize_words(task)
        task_lower = task.lower()

        sdd_terms = {
            "sdd", "spec", "specs", "backlog", "roadmap", "issues", "github", "contract",
            "architecture", "multi", "module", "modules", "epic", "requirements", "design",
            "tasks", "approval", "product", "api", "migrate", "migration",
        }
        tdd_terms = {
            "bug", "fix", "failing", "test", "tests", "regression", "endpoint", "validation",
            "refactor", "behavior", "issue", "error", "crash",
        }
        simple_terms = {"explain", "summary", "resumen", "review", "inspect", "read", "status", "command"}

        if context.has_existing_sdd:
            return "sdd", "The project already has SDD state (`feature_list.json` or `specs/`)."
        if len(words & sdd_terms) >= 2 or "one by one" in task_lower or "uno a uno" in task_lower:
            return "sdd", "The task references backlog/spec/API/product or multi-step issue work."
        if context.has_issues_hint and ("issues" in words or "issue" in words):
            return "sdd", "The task is issue-driven and the project has repository issue context."
        if words & tdd_terms:
            return "tdd", "The task changes behavior or mentions bugs/tests/endpoints."
        if words & simple_terms or len(task.strip()) < 80:
            return "simple", "The task is small or informational; no repo-level harness is needed."
        if context.has_tests:
            return "tdd", "The repository has tests and the task is not clearly simple."
        return "simple", "No signal requires persistent TDD/SDD state."

