#!/usr/bin/env python3
"""Harness runtime for simple, TDD, and SDD project work.

The runtime inspects a project and a task, selects the smallest useful workflow,
selects configured skills, and installs only the files needed by that workflow.
It is intentionally generic: no private project names or local paths are
hardcoded.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_DIR = Path("~/.harness").expanduser()
DEFAULT_PROJECT_MAP = DEFAULT_CONFIG_DIR / "projects.json"
DEFAULT_GLOBAL_SKILLS = DEFAULT_CONFIG_DIR / "skills.json"
BEGIN_MARKER = "<!-- BEGIN HARNESS_MANAGED -->"
END_MARKER = "<!-- END HARNESS_MANAGED -->"


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


@dataclass
class Decision:
    workflow: str
    profile: str
    reason: str
    selected_skills: list[dict[str, Any]]
    will_install_files: bool
    project_root: str
    repo: str | None
    commands: list[str]


def read_json_object(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON at {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def resolve_project(project: str | None, checkout_root: Path, project_map: Path) -> tuple[Path, str | None]:
    if not project:
        if sys.stdin.isatty():
            project = input("Repo URL, owner/name, alias, or local path: ").strip()
        else:
            raise SystemExit("Missing project. Provide --project with a repo URL, owner/name, alias, or local path.")

    aliases = read_json_object(project_map.expanduser(), {})
    if not isinstance(aliases, dict):
        raise SystemExit(f"Project map must be a JSON object: {project_map}")

    if project in aliases:
        return Path(str(aliases[project])).expanduser().resolve(), None

    repo = parse_repo(project)
    if repo:
        target = checkout_root.expanduser() / repo.split("/", 1)[1]
        if not target.exists():
            checkout_root.expanduser().mkdir(parents=True, exist_ok=True)
            subprocess.run(["gh", "repo", "clone", repo, str(target)], check=True)
        return target.resolve(), repo

    return Path(project).expanduser().resolve(), None


def register_alias(alias: str, path: str, project_map: Path) -> None:
    if not alias.strip():
        raise SystemExit("Alias cannot be empty")
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Alias path is not a directory: {root}")
    data = read_json_object(project_map.expanduser(), {})
    if not isinstance(data, dict):
        raise SystemExit(f"Project map must be a JSON object: {project_map}")
    data[alias] = str(root)
    write_json(project_map.expanduser(), data)
    print(json.dumps({"alias": alias, "path": str(root), "project_map": str(project_map.expanduser())}, indent=2))


def discover_files(root: Path, limit: int = 220) -> list[str]:
    ignored = {".git", "target", "build", "dist", ".dart_tool", "node_modules", "__pycache__", ".venv"}
    out: list[str] = []
    for path in root.rglob("*"):
        if len(out) >= limit:
            break
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file():
            out.append(str(path.relative_to(root)))
    return sorted(out)


def detect_profile(root: Path, requested: str) -> str:
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


def inspect_repo(root: Path, repo: str | None, profile: str) -> RepoContext:
    if not root.is_dir():
        raise SystemExit(f"Project root does not exist or is not a directory: {root}")
    files = discover_files(root)
    tests = [f for f in files if re.search(r"(^|/)(tests?|__tests__)/|test_|_test|\\.spec\\.", f, re.I)]
    docs = [f for f in files if f.lower().startswith(("docs/", "documentation/")) or Path(f).name.lower() in {"readme.md", "agents.md"}]
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


def normalize_words(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_+-]+", text.lower()))


def classify_workflow(task: str, context: RepoContext, forced: str) -> tuple[str, str]:
    if forced != "auto":
        return forced, f"Workflow forced by --workflow={forced}."

    words = normalize_words(task)
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


def load_skills(root: Path, global_skills_path: Path) -> list[Skill]:
    raw_items: list[Any] = []
    for path in [global_skills_path.expanduser(), root / ".harness" / "skills.json"]:
        data = read_json_object(path, [])
        if isinstance(data, dict):
            data = data.get("skills", [])
        if not isinstance(data, list):
            raise SystemExit(f"Skills registry must be a list or {{\"skills\": [...]}}: {path}")
        raw_items.extend(data)

    skills: list[Skill] = []
    for item in raw_items:
        if not isinstance(item, dict) or "name" not in item:
            continue
        triggers = item.get("triggers", [])
        if isinstance(triggers, str):
            triggers = [triggers]
        skills.append(
            Skill(
                name=str(item["name"]),
                triggers=[str(x).lower() for x in triggers],
                description=str(item.get("description", "")),
                path=str(item.get("path", "")),
            )
        )
    return skills


def select_skills(task: str, context: RepoContext, skills: list[Skill]) -> list[Skill]:
    haystack = " ".join([task.lower(), context.profile.lower(), " ".join(context.files_sample).lower()])
    selected: list[Skill] = []
    for skill in skills:
        if any(trigger and trigger in haystack for trigger in skill.triggers):
            selected.append(skill)
    return selected


def verification_commands(profile: str) -> list[str]:
    if profile == "rust":
        return ["cargo fmt --check", "cargo check", "cargo test"]
    if profile == "flutter":
        return ["flutter analyze", "flutter test"]
    if profile == "python":
        return ["pytest || python3 -m unittest discover -s tests -v"]
    if profile == "node":
        return ["npm test"]
    return ["# add project-specific verification command"]


def decide(root: Path, repo: str | None, profile: str, task: str, workflow: str, global_skills: Path) -> Decision:
    context = inspect_repo(root, repo, profile)
    selected_workflow, reason = classify_workflow(task, context, workflow)
    skills = select_skills(task, context, load_skills(root, global_skills))
    commands = [
        f"python3 scripts/harness.py run --project {json.dumps(str(root))} --task {json.dumps(task)} --workflow {selected_workflow} --dry-run",
    ]
    if selected_workflow != "simple":
        commands.append("./init.sh")
    return Decision(
        workflow=selected_workflow,
        profile=profile,
        reason=reason,
        selected_skills=[asdict(skill) for skill in skills],
        will_install_files=selected_workflow != "simple",
        project_root=str(root),
        repo=repo,
        commands=commands,
    )


def init_sh(profile: str, workflow: str) -> str:
    commands = verification_commands(profile)
    command_text = "\n".join(f'run_step "{cmd}" {cmd}' for cmd in commands if not cmd.startswith("#"))
    if not command_text:
        command_text = 'warn "No project-specific verification command configured"'

    sdd_validation = ""
    if workflow == "sdd":
        sdd_validation = r'''
python3 - <<'PY'
import json, os, sys
data = json.load(open("feature_list.json", encoding="utf-8"))
features = data.get("features", [])
in_progress = [f for f in features if f.get("status") == "in_progress"]
if len(in_progress) > 1:
    print(f"[FAIL] More than one feature in progress: {len(in_progress)}")
    sys.exit(1)
for f in features:
    if f.get("sdd") and f.get("status") in {"spec_ready", "in_progress", "done"}:
        spec_dir = os.path.join("specs", f["name"])
        missing = [x for x in ("requirements.md", "design.md", "tasks.md") if not os.path.isfile(os.path.join(spec_dir, x))]
        if missing:
            print(f"[FAIL] Missing specs for {f['name']}: {', '.join(missing)}")
            sys.exit(1)
print(f"[OK] feature_list.json valid ({len(features)} features)")
PY
if [ $? -ne 0 ]; then EXIT_CODE=1; fi
'''

    return f"""#!/usr/bin/env bash
set -u
RED='\\033[0;31m'; GREEN='\\033[0;32m'; YELLOW='\\033[0;33m'; NC='\\033[0m'
ok()    {{ printf "${{GREEN}}[OK]${{NC}}    %s\\n" "$1"; }}
warn()  {{ printf "${{YELLOW}}[WARN]${{NC}}  %s\\n" "$1"; }}
fail()  {{ printf "${{RED}}[FAIL]${{NC}}  %s\\n" "$1"; }}
EXIT_CODE=0
run_step() {{
  label="$1"; shift
  if "$@"; then ok "$label"; else fail "$label"; EXIT_CODE=1; fi
}}

echo "── Harness validation ({workflow}/{profile}) ─────────────"
for f in AGENTS.md HARNESS.md docs/verification.md progress/current.md; do
  if [ -f "$f" ]; then ok "Exists $f"; else fail "Missing $f"; EXIT_CODE=1; fi
done
{sdd_validation}

echo "── Project checks ─────────────────────────────────────"
{command_text}

if [ $EXIT_CODE -eq 0 ]; then ok "Harness environment ready."; else fail "Harness environment not ready."; fi
exit $EXIT_CODE
"""


def harness_md(workflow: str, decision: Decision) -> str:
    if workflow == "tdd":
        return f"""# Harness

Workflow: TDD

Reason: {decision.reason}

Use RED -> GREEN -> REFACTOR -> AUDIT.

1. Write or identify a failing test for the behavior.
2. Implement the smallest change that passes.
3. Refactor while tests remain green.
4. Run `./init.sh`.
5. Record evidence in `progress/current.md`.
"""
    return f"""# Harness

Workflow: SDD

Reason: {decision.reason}

Use strict Spec Driven Development:

`pending -> spec_ready -> human approval -> in_progress -> implementer -> reviewer -> done`

Do not implement a pending SDD feature until specs exist.
Do not implement a `spec_ready` feature until a human approves it.
Every completed `R<n>` requirement must map to at least one test.
"""


def managed_section(workflow: str, decision: Decision) -> str:
    skills = ", ".join(skill["name"] for skill in decision.selected_skills) or "none"
    return f"""{BEGIN_MARKER}

## Harness Runtime

Selected workflow: `{workflow}`.
Reason: {decision.reason}
Selected skills: {skills}.

- `simple`: direct work, minimal verification, no persistent harness files.
- `tdd`: RED -> GREEN -> REFACTOR -> AUDIT.
- `sdd`: requirements -> design -> tasks -> human approval -> implementation -> review.
- Run `./init.sh` before closing TDD/SDD work.

{END_MARKER}
"""


def docs(profile: str, workflow: str, decision: Decision) -> dict[str, str]:
    verification = "# Verification\n\nRun:\n\n```bash\n./init.sh\n```\n\n"
    verification += f"Profile: `{profile}`\nWorkflow: `{workflow}`\n"
    conventions = """# Conventions

- Prefer existing project patterns.
- Keep changes scoped to the active task.
- Replace deprecated flows instead of preserving obsolete behavior by default.
- Use selected skills from the harness decision when available.
"""
    architecture = """# Architecture

Document the project's current architecture here. Keep implementation inside existing boundaries.
"""
    specs = """# Spec Driven Development

Each SDD feature uses:

- `requirements.md` with testable `R<n>` requirements.
- `design.md` with implementation decisions.
- `tasks.md` with executable checklist items.

Flow:

`pending -> spec_ready -> human approval -> in_progress -> review -> done`
"""
    return {
        "docs/verification.md": verification,
        "docs/conventions.md": conventions,
        "docs/architecture.md": architecture,
        "docs/specs.md": specs,
    }


def feature_list(root: Path, repo: str | None) -> str:
    data: dict[str, Any] = {
        "project": root.name,
        "description": f"SDD feature backlog for {root.name}.",
        "rules": {
            "one_feature_at_a_time": True,
            "require_tests_to_close": True,
            "require_approved_spec_to_implement": True,
            "valid_status": ["pending", "spec_ready", "in_progress", "done", "blocked"],
        },
        "features": [],
    }
    if repo:
        data["github_repo"] = repo
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def agent_file(role: str) -> str:
    return f"""# {role.replace('_', ' ').title()} Agent

Read `AGENTS.md`, `HARNESS.md`, `feature_list.json` when present, and `progress/current.md`.

Role:
- leader: orchestrate only.
- spec_author: write SDD specs only.
- implementer: implement approved specs and update tests.
- reviewer: review only and write a verdict.

Never skip the human approval gate for `spec_ready` features.
"""


def files_for(root: Path, workflow: str, decision: Decision) -> dict[str, str]:
    if workflow == "simple":
        return {}
    files = {
        "HARNESS.md": harness_md(workflow, decision),
        "init.sh": init_sh(decision.profile, workflow),
        "docs/verification.md": docs(decision.profile, workflow, decision)["docs/verification.md"],
        "progress/current.md": "# Current Harness Session\n\nStatus: idle\n",
    }
    if workflow == "sdd":
        files.update(docs(decision.profile, workflow, decision))
        files.update(
            {
                "feature_list.json": feature_list(root, decision.repo),
                "CHECKPOINTS.md": "# CHECKPOINTS\n\n- [ ] `./init.sh` passes.\n- [ ] Harness state is coherent.\n- [ ] Requirements map to tests for completed SDD features.\n",
                "progress/history.md": "# Harness History\n\n",
                "specs/.gitkeep": "",
                ".claude/agents/leader.md": agent_file("leader"),
                ".claude/agents/spec_author.md": agent_file("spec_author"),
                ".claude/agents/implementer.md": agent_file("implementer"),
                ".claude/agents/reviewer.md": agent_file("reviewer"),
            }
        )
    return files


def write_file(path: Path, content: str, dry_run: bool, actions: list[str], conflicts: list[str]) -> None:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            actions.append(f"unchanged {path}")
            return
        if path.name == ".gitkeep" and current == "":
            actions.append(f"unchanged {path}")
            return
        conflicts.append(f"exists {path}")
        return
    actions.append(f"write {path}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if path.name == "init.sh":
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def merge_agents(path: Path, workflow: str, decision: Decision, dry_run: bool, actions: list[str]) -> None:
    section = managed_section(workflow, decision)
    if not path.exists():
        actions.append(f"write {path}")
        if not dry_run:
            path.write_text("# Repository Guidelines\n\n" + section, encoding="utf-8")
        return
    current = path.read_text(encoding="utf-8")
    if BEGIN_MARKER in current and END_MARKER in current:
        before = current.split(BEGIN_MARKER)[0].rstrip()
        after = current.split(END_MARKER, 1)[1].lstrip()
        merged = before + "\n\n" + section + ("\n" + after if after else "")
        actions.append(f"refresh managed section {path}")
    else:
        merged = current.rstrip() + "\n\n" + section
        actions.append(f"append managed section {path}")
    if not dry_run:
        path.write_text(merged, encoding="utf-8")


def write_report(root: Path, decision: Decision, actions: list[str], conflicts: list[str], dry_run: bool) -> None:
    payload = {
        "dry_run": dry_run,
        "decision": asdict(decision),
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


def apply_decision(root: Path, decision: Decision, dry_run: bool) -> int:
    actions: list[str] = []
    conflicts: list[str] = []
    if decision.workflow == "simple":
        actions.append("simple workflow selected; no harness files installed")
        write_report(root, decision, actions, conflicts, dry_run)
        return 0

    merge_agents(root / "AGENTS.md", decision.workflow, decision, dry_run, actions)
    for rel, content in files_for(root, decision.workflow, decision).items():
        write_file(root / rel, content, dry_run, actions, conflicts)
    write_report(root, decision, actions, conflicts, dry_run)
    return 1 if conflicts else 0


def command_run(args: argparse.Namespace) -> int:
    root, repo = resolve_project(args.project, Path(args.checkout_root), Path(args.project_map))
    profile = detect_profile(root, args.profile)
    decision = decide(root, repo, profile, args.task, args.workflow, Path(args.global_skills))
    print(json.dumps(asdict(decision), indent=2, ensure_ascii=False))
    return apply_decision(root, decision, args.dry_run)


def command_inspect(args: argparse.Namespace) -> int:
    root, repo = resolve_project(args.project, Path(args.checkout_root), Path(args.project_map))
    profile = detect_profile(root, args.profile)
    context = inspect_repo(root, repo, profile)
    decision = decide(root, repo, profile, args.task, args.workflow, Path(args.global_skills))
    print(json.dumps({"context": asdict(context), "decision": asdict(decision)}, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harness runtime for simple, TDD, and SDD workflows.")
    parser.add_argument("--project-map", default=str(DEFAULT_PROJECT_MAP), help="Alias map JSON. Default: ~/.harness/projects.json")
    parser.add_argument("--global-skills", default=str(DEFAULT_GLOBAL_SKILLS), help="Global skills registry JSON. Default: ~/.harness/skills.json")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-map", default=str(DEFAULT_PROJECT_MAP), help="Alias map JSON. Default: ~/.harness/projects.json")
        p.add_argument("--global-skills", default=str(DEFAULT_GLOBAL_SKILLS), help="Global skills registry JSON. Default: ~/.harness/skills.json")

    def add_common(p: argparse.ArgumentParser) -> None:
        add_config(p)
        p.add_argument("--project", help="Local path, alias, GitHub owner/name, or GitHub URL")
        p.add_argument("--task", required=True, help="Natural-language task to evaluate")
        p.add_argument("--checkout-root", default="~/Projects", help="Where to clone GitHub repos when --project is remote")
        p.add_argument("--workflow", choices=["auto", "simple", "tdd", "sdd"], default="auto")
        p.add_argument("--profile", choices=["auto", "rust", "flutter", "python", "node", "generic"], default="auto")

    run = sub.add_parser("run", help="Inspect, decide, select skills, and apply the selected workflow.")
    add_common(run)
    run.add_argument("--dry-run", action="store_true")

    inspect_cmd = sub.add_parser("inspect", help="Inspect and decide without applying files.")
    add_common(inspect_cmd)

    register = sub.add_parser("register", help="Register a user-local project alias.")
    add_config(register)
    register.add_argument("--alias", required=True)
    register.add_argument("--path", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "register":
        register_alias(args.alias, args.path, Path(args.project_map))
        return 0
    if args.command == "inspect":
        return command_inspect(args)
    if args.command == "run":
        return command_run(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
