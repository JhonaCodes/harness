"""Text and JSON renderers for installed Harness files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import BEGIN_MARKER, DEFAULT_ADAPTERS, END_MARKER
from .models import Decision


class AdapterSelector:
    def parse(self, raw: str) -> list[dict[str, str]]:
        value = raw.strip().lower()
        if value == "none":
            return []
        if value == "all":
            return [dict(item) for item in DEFAULT_ADAPTERS.values()]
        selected: list[dict[str, str]] = []
        for key in [part.strip().lower() for part in raw.split(",") if part.strip()]:
            if key not in DEFAULT_ADAPTERS:
                valid = ", ".join(["all", "none", *DEFAULT_ADAPTERS])
                raise SystemExit(f"Unknown adapter '{key}'. Valid values: {valid}")
            selected.append(dict(DEFAULT_ADAPTERS[key]))
        return selected


class HarnessRenderer:
    def verification_commands(self, profile: str) -> list[str]:
        commands = {
            "rust": ["cargo fmt --check", "cargo check", "cargo test"],
            "flutter": ["flutter analyze", "flutter test"],
            "python": ["pytest || python3 -m unittest discover -s tests -v"],
            "node": ["npm test"],
        }
        return commands.get(profile, ["# add project-specific verification command"])

    def init_sh(self, profile: str, workflow: str) -> str:
        commands = self.verification_commands(profile)
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
    if f.get("sdd") and f.get("status") == "done":
        review_path = os.path.join("progress", f"review_{f['name']}.md")
        audit_path = os.path.join("progress", f"audit_{f['name']}.md")
        missing = [path for path in (review_path, audit_path) if not os.path.isfile(path)]
        if missing:
            print(f"[FAIL] Done feature missing review/audit evidence: {', '.join(missing)}")
            sys.exit(1)
print(f"[OK] feature_list.json valid ({len(features)} features)")
PY
if [ $? -ne 0 ]; then EXIT_CODE=1; fi
'''

        return f"""#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.." || exit 1
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
for f in HARNESS.md .harness/ENTRYPOINT.md .harness/config.json .harness/workflow.json .harness/skills.json .harness/agents.json .harness/docs.json .harness/rules.json .harness/rules/data_storage.md .harness/mcps.json docs/verification.md docs/audit.md progress/current.md; do
  if [ -f "$f" ]; then ok "Exists $f"; else fail "Missing $f"; EXIT_CODE=1; fi
done
{sdd_validation}

echo "── Project checks ─────────────────────────────────────"
{command_text}

if [ $EXIT_CODE -eq 0 ]; then ok "Harness environment ready."; else fail "Harness environment not ready."; fi
exit $EXIT_CODE
"""

    @staticmethod
    def installed_scaffolding(workflow: str) -> str:
        if workflow == "sdd":
            return "tdd+sdd"
        if workflow == "tdd":
            return "tdd"
        return workflow

    def harness_md(self, workflow: str, decision: Decision) -> str:
        scaffolding = self.installed_scaffolding(workflow)
        return f"""# Harness

{BEGIN_MARKER}

Universal Harness runtime for any LLM. This file is the source of truth (with `.harness/ENTRYPOINT.md`). Tool-specific files such as `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` are adapters only.

Installed scaffolding: `{scaffolding}`
Default fallback if `harness inspect` is unavailable: `{workflow}`
Reason: {decision.reason}

## Per-task flow (mandatory)

For every user task, do this in order:

1. **Inspect first.** Run `harness inspect --project . --task "<user task>"` and read the JSON decision. The workflow is decided per-task, not fixed by what is installed.
2. Read `.harness/ENTRYPOINT.md` and the relevant registries in `.harness/{{config,workflow,skills,agents,docs,rules,mcps,memory}}.json`.
3. Apply the workflow the inspection returned:
   - `simple` -> direct work, no persistent state.
   - `tdd` -> follow the TDD steps below.
   - `sdd` -> follow the SDD steps below.
4. Use selected skills/agents/docs/rules/MCP contexts whose triggers match the task. Load global capabilities from `~/.harness/*` and project capabilities from `.harness/*`.
5. Store state, specs, subagent outputs, audit evidence, generated artifacts, and durable memory according to `.harness/rules/data_storage.md`.

## TDD flow

RED -> human checkpoint if ambiguous -> GREEN -> REFACTOR -> mandatory audit.

1. Write or identify a failing test for the behavior.
2. If expected behavior is ambiguous, stop and ask for human clarification before implementing.
3. Implement the smallest change that passes.
4. Refactor while tests remain green.
5. Run `./scripts/init.sh`.
6. Run the focused audit from `docs/audit.md`.
7. Record test and audit evidence in `progress/current.md`.
8. Do not close without a test or a written no-test justification.

## SDD flow

`pending -> spec_ready -> human approval -> in_progress -> implementer -> reviewer -> auditor -> done`

Runtime roles:

- Leader coordinates and launches subagents; does not implement application code.
- Spec author writes requirements/design/tasks and stops at `spec_ready`.
- Implementer implements exactly one approved feature and writes tests.
- Reviewer reviews only, runs verification, and writes a verdict.
- Auditor validates context, business rules, code quality, tests, confidence, go/no-go.

State rules:

- Work on one feature at a time.
- Keep `progress/current.md` updated during the session.
- Subagents write outputs to files under `progress/` and return only a short reference.
- Move the closure summary to `progress/history.md` before marking work complete.

Hard rules:

- Do not implement a pending SDD feature until specs exist.
- Do not implement a `spec_ready` feature until a human approves it.
- Every completed `R<n>` requirement must map to at least one test.
- Every `done` feature must have reviewer approval and `progress/audit_<feature>.md` with `GO` or accepted `GO-WITH-RISK`.

{END_MARKER}
"""

    def project_config(self, root: Path, workflow: str, decision: Decision) -> str:
        data = {
            "schema_version": 1,
            "project": root.name,
            "workflow": workflow,
            "profile": decision.profile,
            "source_of_truth": {
                "contract": "HARNESS.md",
                "entrypoint": ".harness/ENTRYPOINT.md",
                "workflow": ".harness/workflow.json",
                "skills": ".harness/skills.json",
                "agents": ".harness/agents.json",
                "docs": ".harness/docs.json",
                "rules": ".harness/rules.json",
                "data_storage_rule": ".harness/rules/data_storage.md",
                "mcps": ".harness/mcps.json",
                "memory": ".harness/memory.json",
                "adapters": ".harness/adapters.json",
            },
            "rules": {
                "auto_inspect_on_open": True,
                "simple_installs_no_files": True,
                "tool_specific_files_are_adapters": True,
                "human_checkpoint_for_ambiguous_tdd": workflow == "tdd",
                "mandatory_audit_before_closure": workflow in {"tdd", "sdd"},
                "audit_policy": "risk_based",
                "one_feature_at_a_time": workflow == "sdd",
                "human_approval_required_for_spec_ready": workflow == "sdd",
                "review_required_before_done": workflow == "sdd",
                "audit_required_before_done": workflow == "sdd",
            },
        }
        if decision.repo:
            data["repo"] = decision.repo
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    @staticmethod
    def empty_skills() -> str:
        return "[]\n"

    @staticmethod
    def empty_capability_registry() -> str:
        return "[]\n"

    def agent_registry(self, workflow: str) -> str:
        tdd_agents = [
            {
                "name": "tdd-lead",
                "triggers": ["tdd", "red", "green", "refactor", "test_first", "bug", "fix"],
                "description": "TDD coordinator agent for RED -> GREEN -> REFACTOR execution.",
                "path": ".harness/agents/tdd_lead.md",
                "context": "Use for TDD tasks to coordinate failing test reproduction, minimal implementation, refactor, and mandatory audit handoff.",
            },
            {
                "name": "red-test-author",
                "triggers": ["red", "failing_test", "reproduce", "test_first", "regression"],
                "description": "TDD agent that writes or identifies the failing test before implementation.",
                "path": ".harness/agents/red_test_author.md",
                "context": "Use before implementation to prove the bug or missing behavior with a focused failing test.",
            },
            {
                "name": "green-implementer",
                "triggers": ["green", "implement", "minimal_fix", "pass_test"],
                "description": "TDD agent that makes the smallest implementation change needed to pass the failing test.",
                "path": ".harness/agents/green_implementer.md",
                "context": "Use after RED evidence exists to implement the smallest scoped change that passes tests.",
            },
            {
                "name": "refactor-specialist",
                "triggers": ["refactor", "cleanup", "duplication", "maintainability"],
                "description": "TDD agent that refactors only after tests are green.",
                "path": ".harness/agents/refactor_specialist.md",
                "context": "Use after GREEN to improve structure without changing behavior, while keeping verification green.",
            },
        ]
        architecture_audit_agents = [
            {
                "name": "architecture-lead",
                "triggers": ["architecture", "design", "module", "boundary", "layering", "handler", "service", "repository", "contract"],
                "description": "Architecture validation agent for project structure and API contracts.",
                "path": ".harness/agents/architecture_lead.md",
                "context": "Use before implementation or review when module structure, API contracts, boundaries, or architecture decisions are involved.",
            },
            {
                "name": "blueprint-architect",
                "triggers": ["blueprint", "blueprints", "dependency", "coding_rules", "framework_contract", "api_layer"],
                "description": "Blueprint validation agent for MCP-backed architecture and coding-rule checks.",
                "path": ".harness/agents/blueprint_architect.md",
                "context": "Use when implementation or review depends on registered MCP blueprints, dependency rules, coding rules, or framework patterns.",
            },
            {
                "name": "context-auditor",
                "triggers": ["audit", "context", "source_of_truth", "scope", "agents", "skills", "mcp", "sdd"],
                "description": "Audit agent for source of truth, selected Harness entries, and workflow state.",
                "path": ".harness/agents/context_auditor.md",
                "context": "Use during mandatory audit to verify context, skill/MCP selection, scope, and traceability.",
            },
            {
                "name": "business-rule-auditor",
                "triggers": ["audit", "business", "domain", "product", "permission", "ownership", "workflow", "contract"],
                "description": "Audit agent for domain rules, ownership, permissions, and product invariants.",
                "path": ".harness/agents/business_rule_auditor.md",
                "context": "Use during audit when changes affect business behavior, permissions, workflow state, or user-facing contracts.",
            },
            {
                "name": "code-quality-auditor",
                "triggers": ["audit", "code_quality", "correctness", "maintainability", "security", "regression", "dead_code", "layering"],
                "description": "Audit agent for correctness, layering, maintainability, security, and regression risk.",
                "path": ".harness/agents/code_quality_auditor.md",
                "context": "Use during audit to inspect changed files, architecture boundaries, error handling, maintainability, security risk, and dead code.",
            },
            {
                "name": "test-verifier",
                "triggers": ["audit", "test", "tests", "verification", "coverage", "regression", "init"],
                "description": "Audit agent for requirement-to-test mapping and command verification evidence.",
                "path": ".harness/agents/test_verifier.md",
                "context": "Use during audit to map requirements to tests, verify init/check evidence, and report missing regression coverage.",
            },
            {
                "name": "confidence-reporter",
                "triggers": ["audit", "confidence", "risk", "go", "no_go", "go_with_risk", "closure", "final_report"],
                "description": "Final audit agent for confidence score, residual risk, and go/no-go closure.",
                "path": ".harness/agents/confidence_reporter.md",
                "context": "Use at the end of review/audit to combine architecture, context, business, code-quality, and test evidence into a final confidence decision.",
            },
        ]
        entries = [*tdd_agents, *architecture_audit_agents]
        if workflow == "sdd":
            entries = [
                {"name": "leader", "triggers": ["sdd", "feature", "backlog", "coordinate", "decompose", "subagent"], "description": "SDD coordinator agent that decomposes work and launches subagents.", "path": ".harness/agents/leader.md"},
                {"name": "spec-author", "triggers": ["spec", "requirements", "design", "tasks", "spec_ready"], "description": "SDD spec author agent for requirements, design, and task plans.", "path": ".harness/agents/spec_author.md"},
                {"name": "implementer", "triggers": ["implement", "implementation", "in_progress", "code", "feature"], "description": "SDD implementation agent for one approved feature.", "path": ".harness/agents/implementer.md"},
                {"name": "reviewer", "triggers": ["review", "reviewer", "approval", "changes_requested"], "description": "SDD reviewer agent that verifies implementation before audit.", "path": ".harness/agents/reviewer.md"},
                {"name": "auditor", "triggers": ["audit", "auditor", "go", "no_go", "go_with_risk"], "description": "SDD aggregate auditor agent for final mandatory audit.", "path": ".harness/agents/auditor.md"},
                *entries,
            ]
        return json.dumps(entries, indent=2, ensure_ascii=False) + "\n"

    @staticmethod
    def rule_registry() -> str:
        return json.dumps(
            [
                {
                    "name": "data-storage",
                    "triggers": ["storage", "data", "evidence", "progress", "memory", "artifact", "audit", "sdd", "tdd"],
                    "description": "Rules for storing Harness state, evidence, agent outputs, and durable notes.",
                    "path": ".harness/rules/data_storage.md",
                    "context": "Use for every TDD/SDD task to decide where state, specs, audit evidence, generated artifacts, and durable project notes must be stored.",
                }
            ],
            indent=2,
            ensure_ascii=False,
        ) + "\n"

    @staticmethod
    def data_storage_rule() -> str:
        return """# Data Storage Rule

Harness state and evidence must be portable, explicit, and reviewable.

## Canonical Locations

- `feature_list.json`: SDD feature state only.
- `specs/<feature>/`: SDD requirements, design, and tasks only.
- `progress/current.md`: active session state.
- `progress/history.md`: completed session summaries.
- `progress/*_<feature>.md`: subagent outputs, review verdicts, audit verdicts, confidence reports, and verification evidence.
- `.harness/memory.json`: durable project notes that should influence future tasks.
- `.harness/{skills,agents,docs,rules,mcps}.json`: capability registries only.
- `.harness/rules/`: reusable project rules.
- `.harness/mcp-context/`: local descriptions of when MCP sources must be consulted.

## Hard Rules

- Store subagent results in files under `progress/`; chat-only subagent reports are not closure evidence.
- Use relative paths inside Harness registries when the file lives in the repo.
- Do not store secrets, tokens, credentials, private keys, or production personal data in Harness files.
- Do not store machine-local absolute paths unless the entry intentionally points to a user-local global skill outside the repo.
- Do not duplicate long generated artifacts in chat; write them to the canonical file and reference the path.
- Keep specs, progress, audit, and memory separate. Do not use one file as a dumping ground for all state.
- Every completed TDD/SDD task must leave verification evidence and residual risk notes in `progress/`.
"""

    @staticmethod
    def empty_memory() -> str:
        return json.dumps({"schema_version": 1, "entries": {}}, indent=2, ensure_ascii=False) + "\n"

    def workflow_json(self, workflow: str, decision: Decision, adapters: list[dict[str, str]]) -> str:
        data = {
            "schema_version": 1,
            "workflow": workflow,
            "reason": decision.reason,
            "profile": decision.profile,
            "selected_skills": decision.selected_skills,
            "selected_capabilities": decision.selected_capabilities,
            "adapters": adapters,
            "rules": {
                "simple_installs_no_files": workflow == "simple",
                "tdd_human_checkpoint_if_ambiguous": workflow == "tdd",
                "sdd_human_approval_required": workflow == "sdd",
                "review_required_before_done": workflow == "sdd",
                "mandatory_audit_before_closure": workflow in {"tdd", "sdd"},
                "audit_policy": "risk_based",
                "data_storage_rule": ".harness/rules/data_storage.md",
                "audit_output": ["Context status", "Business-rule status", "Code-quality findings", "Test verification", "Confidence report", "Go/No-Go", "Residual risks"],
            },
        }
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    @staticmethod
    def adapters_json(adapters: list[dict[str, str]]) -> str:
        data = {
            "schema_version": 1,
            "source_of_truth": ["HARNESS.md", ".harness/ENTRYPOINT.md"],
            "adapters": adapters,
        }
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def universal_entrypoint(self, workflow: str, decision: Decision) -> str:
        skills = ", ".join(skill["name"] for skill in decision.selected_skills) or "none"
        selected_agents = ", ".join(item["name"] for item in decision.selected_capabilities.get("agent", [])) or "none"
        selected_docs = ", ".join(item["name"] for item in decision.selected_capabilities.get("doc", [])) or "none"
        selected_rules = ", ".join(item["name"] for item in decision.selected_capabilities.get("rule", [])) or "none"
        selected_mcps = ", ".join(item["name"] for item in decision.selected_capabilities.get("mcp", [])) or "none"
        return f"""# Harness Entrypoint

{BEGIN_MARKER}

This is the neutral startup contract for any LLM working in this project.

## Startup

1. Read `HARNESS.md`.
2. Read `.harness/config.json`, `.harness/workflow.json`, `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, `.harness/mcps.json`, and `.harness/memory.json` when present.
3. If available, inspect the task with:
   ```bash
   harness inspect --project . --task "<user task>"
   ```
4. Apply the decided workflow:
   - `simple`: direct work, minimal verification, no persistent state.
   - `tdd`: RED -> human checkpoint if expected behavior is ambiguous -> GREEN -> REFACTOR -> mandatory audit.
   - `sdd`: requirements -> design -> tasks -> human approval -> implementation -> review -> audit.
5. Use matching skills, agents, docs, rules, and MCP contexts from `.harness/*` and `~/.harness/*`.
6. Read durable project memory from `.harness/memory.json` and optional global memory if configured.

Default installed workflow: `{workflow}`.
Reason: {decision.reason}
Selected skills: {skills}.
Selected agents: {selected_agents}.
Selected docs: {selected_docs}.
Selected rules: {selected_rules}.
Selected MCPs: {selected_mcps}.

## Hard Rules

- Tool-specific files are adapters, not the source of truth.
- Do not skip the TDD ambiguity checkpoint when behavior is unclear.
- For SDD, do not skip `spec_ready` human approval.
- Do not mark work `done` without verification, review, and audit evidence.
- Store Harness state and evidence according to `.harness/rules/data_storage.md`.

{END_MARKER}
"""

    @staticmethod
    def adapter_entrypoint(adapter: dict[str, str], workflow: str, decision: Decision) -> str:
        scaffolding = HarnessRenderer.installed_scaffolding(workflow)
        return f"""# {adapter["name"]}

{BEGIN_MARKER}

## Harness (mandatory if installed)

This project uses **Harness** as its main workflow runtime. The presence of `.harness/` in the project root means every task must follow the Harness flow. Other instructions in this file are **subordinate** to Harness output.

### For every user task

1. **Run `harness inspect --project . --task "<user task>"` FIRST.** Read the JSON decision; the workflow is decided per-task, not fixed.
2. Apply the workflow the inspection returned:
   - `simple` -> direct work; no persistent state.
   - `tdd` -> RED -> human checkpoint if ambiguous -> GREEN -> REFACTOR -> mandatory audit.
   - `sdd` -> requirements -> design -> tasks -> human approval -> implementation -> review -> audit.
3. Read `HARNESS.md`, `.harness/ENTRYPOINT.md`, and `.harness/{{config,workflow,skills,agents,docs,rules,mcps,memory}}.json`.
4. Use selected skills/agents/docs/rules/MCP contexts whose triggers match the task. Global capabilities live in `~/.harness/*`; project capabilities live in `.harness/*`.
5. Store evidence under `progress/` per `.harness/rules/data_storage.md`.
6. Do not close work without verification + audit `GO` (or accepted `GO-WITH-RISK`).

Installed scaffolding: `{scaffolding}`
Default fallback if `harness inspect` is unavailable: `{workflow}`
Reason: {decision.reason}

{END_MARKER}
"""

    def audit_doc(self, root: Path, profile: str, workflow: str, decision: Decision) -> str:
        mode = "strict" if workflow == "sdd" else "focused"
        selected_docs = decision.selected_capabilities.get("doc", [])
        selected_rules = decision.selected_capabilities.get("rule", [])
        selected_agents = decision.selected_capabilities.get("agent", [])
        selected_skills = decision.selected_capabilities.get("skill", [])
        selected_mcps = decision.selected_capabilities.get("mcp", [])

        def lines_for(title: str, items: list[dict[str, Any]]) -> str:
            if not items:
                return f"## Selected {title}\n\nNone selected by trigger.\n"
            rows = [f"## Selected {title}\n"]
            for item in items:
                detail = item.get("description") or item.get("path") or "No description"
                if item.get("context"):
                    detail = f"{detail} Context: {item['context']}"
                path = f" Path: `{item['path']}`." if item.get("path") else ""
                rows.append(f"- `{item['name']}`: {detail}.{path}")
            return "\n".join(rows) + "\n"

        capability_sections = "\n".join(
            [
                lines_for("skills", selected_skills),
                lines_for("agents", selected_agents),
                lines_for("docs", selected_docs),
                lines_for("rules", selected_rules),
                lines_for("MCP contexts", selected_mcps),
            ]
        )
        return f"""# Audit

Workflow: `{workflow}`
Mode: `{mode}`
Policy: risk-based mandatory closure gate.

Use this audit after meaningful implementation and before closing TDD/SDD work.

## Required Roles

Execute in order:

1. Context validator: verify source of truth, selected capabilities, project docs, relevant MCP/blueprints, and scope.
2. Business-rule validator: check permissions, workflow states, invariants, domain rules, and user-facing constraints.
3. Code-quality auditor: check correctness, architecture, layering, maintainability, security, and regression risk.
4. Test verifier: map changed behavior to tests/checks, verify commands run, and identify coverage gaps.
5. Confidence reporter: summarize confidence and issue `GO`, `GO-WITH-RISK`, or `NO-GO`.

## Evidence Rules

- Findings require evidence, preferably `file:line`.
- Use severities: `critical`, `high`, `medium`, `low`, `info`.
- Report missing evidence as a gap.
- Do not edit code during audit.

## Required Output

1. Context status
2. Business-rule status
3. Code-quality findings
4. Test verification
5. Confidence report
6. Go/No-Go
7. Residual risks

## Extension Inputs

Harness does not hardcode domain architecture rules. Load and apply the selected skills, agents, docs, rules, and MCP contexts below when their triggers match the task/project context.

{capability_sections}
"""

    def docs(self, root: Path, profile: str, workflow: str, decision: Decision) -> dict[str, str]:
        verification = "# Verification\n\nRun:\n\n```bash\n./scripts/init.sh\n```\n\n"
        verification += f"Profile: `{profile}`\nWorkflow: `{workflow}`\n\n"
        if workflow in {"tdd", "sdd"}:
            verification += "Closure requires a completed audit from `docs/audit.md` with `GO`, `GO-WITH-RISK`, or `NO-GO`.\n"
        conventions = """# Conventions

- Prefer existing project patterns.
- Keep changes scoped to the active task.
- Replace obsolete flows instead of preserving outdated behavior by default.
- Use selected skills, agents, docs, rules, and MCP contexts from the harness decision when available.
- Store state, specs, subagent outputs, audit evidence, and durable notes according to `.harness/rules/data_storage.md`.
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

`pending -> spec_ready -> human approval -> in_progress -> implementer -> reviewer -> auditor -> done`

## Process Rules

- The leader coordinates and does not implement application code.
- The spec author creates specs and stops at `spec_ready`.
- The implementer works on exactly one approved feature.
- The reviewer never edits code; it approves or rejects with concrete evidence.
- The auditor validates context, business rules, code quality, tests, confidence, and go/no-go.
- Subagents write results to files in `progress/` and return only the file reference.
- Do not mark a feature `done` until `./scripts/init.sh` is green, review is approved, and `progress/audit_<feature>.md` is `GO` or accepted `GO-WITH-RISK`.
"""
        result = {
            "docs/verification.md": verification,
            "docs/conventions.md": conventions,
            "docs/architecture.md": architecture,
            "docs/specs.md": specs,
        }
        if workflow in {"tdd", "sdd"}:
            result["docs/audit.md"] = self.audit_doc(root, profile, workflow, decision)
        return result

    @staticmethod
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

    def agent_file(self, role: str) -> str:
        if role == "leader":
            return """# Leader Agent

You coordinate and decompose work. You do not implement application code directly.

## Startup

1. Read `HARNESS.md`, `.harness/ENTRYPOINT.md`, `feature_list.json`, and `progress/current.md`.
2. Run `./scripts/init.sh`. If it fails, stop and report the blocker.
3. Select one feature only.

## Delegation

- If a feature is `pending`, launch or act as spec_author, create specs, set `spec_ready`, then stop for human approval.
- If a feature is `spec_ready`, continue only after explicit human approval.
- If implementation is needed, launch one implementer.
- If investigation is needed, launch 2-3 explorers with narrow questions.
- After implementation, launch one reviewer, then one auditor before anything becomes `done`.

## Anti Telephone Rule

Subagents must write outputs to files under `progress/` and reply only with a reference, for example:

`done -> progress/impl_<feature>.md`

Do not accept long chat-only reports as final subagent output.
"""
        if role == "spec_author":
            return """# Spec Author Agent

You write specs for exactly one pending SDD feature. You do not edit application code or tests.

Create:

- `specs/<feature>/requirements.md`
- `specs/<feature>/design.md`
- `specs/<feature>/tasks.md`

Then set the feature to `spec_ready` and stop for human approval.

Each requirement must be testable and use a stable `R<n>` id.
Your final response is only:

`spec_ready -> specs/<feature>/`
"""
        if role == "implementer":
            return """# Implementer Agent

You implement exactly one approved SDD feature.

## Protocol

1. Read `HARNESS.md`, `.harness/ENTRYPOINT.md`, `docs/architecture.md`, `docs/conventions.md`, and the feature specs.
2. Change the feature to `in_progress`.
3. Record the active feature and short plan in `progress/current.md`.
4. Implement only the approved scope.
5. Add or update tests for each requirement.
6. Run `./scripts/init.sh`.
7. Write `progress/impl_<feature>.md` with files changed, tests run, and requirement-to-test traceability.
8. Do not mark `done`; wait for reviewer approval.

Final response:

`done -> progress/impl_<feature>.md`

or

`blocked -> progress/current.md`
"""
        if role == "auditor":
            return """# Auditor Agent

You audit only. You do not edit code.

## Protocol

1. Read `HARNESS.md`, `.harness/ENTRYPOINT.md`, `docs/audit.md`, `docs/architecture.md`, `docs/conventions.md`, `docs/specs.md`, and `CHECKPOINTS.md`.
2. Inspect modified files, specs, `progress/impl_<feature>.md`, and `progress/review_<feature>.md`.
3. Execute the roles in `docs/audit.md`: Context validator, Business-rule validator, Code-quality auditor, Test verifier, Confidence reporter.
4. Verify traceability: `R<n> -> test/check -> audit verdict`.
5. Verify `./scripts/init.sh` evidence.
6. Write `progress/audit_<feature>.md`.
7. Do not mark `done`; the leader applies the final state after the audit verdict.

Final response:

`GO -> progress/audit_<feature>.md`

or

`GO-WITH-RISK -> progress/audit_<feature>.md`

or

`NO-GO -> progress/audit_<feature>.md`
"""
        if role == "tdd_lead":
            return """# TDD Lead Agent

You coordinate RED -> GREEN -> REFACTOR for focused bugs and behavior changes.

## Protocol

1. Read `HARNESS.md`, `.harness/ENTRYPOINT.md`, `docs/verification.md`, `docs/audit.md`, and `progress/current.md`.
2. Identify the smallest behavior under test.
3. Ensure RED evidence exists before implementation.
4. Hand off to implementation only after the failing test is documented.
5. Run or verify `./scripts/init.sh` after GREEN and after refactor.
6. Store evidence in `progress/current.md` or `progress/tdd_<task>.md`.
7. Trigger mandatory audit before closure.
"""
        if role == "red_test_author":
            return """# Red Test Author Agent

You write or identify the failing test first. You do not implement production code.

## Protocol

1. Read the task, nearest tests, and relevant implementation files.
2. Add or identify the smallest focused test that fails for the target behavior.
3. Run the focused test command and capture the failure.
4. Store RED evidence in `progress/red_<task>.md`.
"""
        if role == "green_implementer":
            return """# Green Implementer Agent

You implement the smallest change needed to pass the RED test.

## Protocol

1. Read RED evidence before editing production code.
2. Keep changes scoped to the failing behavior.
3. Preserve existing architecture and local patterns.
4. Run the focused test and then `./scripts/init.sh` when feasible.
5. Store changed files, tests run, and residual risk in `progress/green_<task>.md`.
"""
        if role == "refactor_specialist":
            return """# Refactor Specialist Agent

You refactor only after tests are green. You do not change behavior.

## Protocol

1. Read GREEN evidence and changed files.
2. Remove duplication or clarify structure only when it lowers maintenance risk.
3. Avoid unrelated refactors.
4. Run the same tests that were green before refactor.
5. Store refactor notes and verification in `progress/refactor_<task>.md`.
"""
        if role == "architecture_lead":
            return """# Architecture Lead Agent

You validate architecture decisions before implementation.

## Protocol

1. Read `HARNESS.md`, `.harness/ENTRYPOINT.md`, `docs/architecture.md`, `docs/conventions.md`, and the active spec or task context.
2. Read `.harness/mcps.json` and use registered blueprint MCP contexts whenever architecture or dependency rules are relevant.
3. Identify affected modules and ownership boundaries.
4. Flag hidden coupling, duplicated abstractions, misplaced business logic, and contract drift.
5. Write findings to `progress/architecture_<feature>.md` when a feature exists.
"""
        if role == "blueprint_architect":
            return """# Blueprint Architect Agent

You validate implementation plans against registered MCP blueprints.

## Protocol

1. Read `.harness/mcps.json` and relevant `.harness/mcp-context/*` files.
2. Determine which blueprints are required for the task.
3. Query the relevant MCP blueprint context before choosing or approving an approach.
4. Map blueprint rules to concrete files or modules.
5. Write findings to `progress/blueprint_<feature>.md` when a feature exists.
"""
        if role == "context_auditor":
            return """# Context Auditor Agent

You audit context only. You do not edit code.

## Protocol

1. Read `HARNESS.md`, `.harness/ENTRYPOINT.md`, `AGENTS.md` when present, `docs/audit.md`, and active progress/spec files.
2. Verify that required skills, agents, docs, rules, and MCP contexts were selected.
3. Verify blueprint MCP context was used when blueprint decisions were involved.
4. Report missing or stale context with evidence.
5. Write findings to `progress/context_audit_<feature>.md` when a feature exists.
"""
        if role == "business_rule_auditor":
            return """# Business Rule Auditor Agent

You audit domain and product rules only. You do not edit code.

## Protocol

1. Read the active spec, `docs/specs.md`, `docs/conventions.md`, `docs/audit.md`, and related implementation files.
2. Map each relevant requirement to code and tests.
3. Verify permissions, ownership checks, workflow state, data invariants, and user-facing constraints.
4. Report missing tests for business-critical behavior.
5. Write findings to `progress/business_audit_<feature>.md` when a feature exists.
"""
        if role == "code_quality_auditor":
            return """# Code Quality Auditor Agent

You audit code quality only. You do not edit code.

## Protocol

1. Read modified files and nearest tests.
2. Verify code follows existing local patterns.
3. Check layering, error handling, maintainability, security risk, and regression risk.
4. Report concrete findings with file and line evidence.
5. Write findings to `progress/code_quality_audit_<feature>.md` when a feature exists.
"""
        if role == "test_verifier":
            return """# Test Verifier Agent

You verify tests and checks only. You do not edit code.

## Protocol

1. Read the active spec or task, changed files, and existing tests.
2. Map each completed requirement to at least one test or explicit check.
3. Run `./scripts/init.sh` unless current evidence was supplied.
4. Report failures, skipped checks, and coverage gaps.
5. Write findings to `progress/test_verification_<feature>.md` when a feature exists.
"""
        if role == "confidence_reporter":
            return """# Confidence Reporter Agent

You produce the final confidence report after review and audits.

## Protocol

1. Read all relevant `progress/*_<feature>.md` files.
2. Summarize unresolved findings by severity.
3. Confirm whether `./scripts/init.sh` passed.
4. Produce a confidence score and final gate decision.
5. Do not mark the feature done; the leader or current operator owns state transitions.
6. Write findings to `progress/confidence_<feature>.md` when a feature exists.
"""
        return """# Reviewer Agent

You review only. You do not edit code.

## Protocol

1. Read `HARNESS.md`, `docs/architecture.md`, `docs/conventions.md`, `docs/specs.md`, and `CHECKPOINTS.md`.
2. Inspect modified files and `progress/impl_<feature>.md`.
3. Verify every requirement maps to at least one test.
4. Verify every task is complete or has a documented blocker.
5. Run `./scripts/init.sh`.
6. Write the verdict to `progress/review_<feature>.md`.
7. Do not mark `done`; audit must run after review.

Final response:

`APPROVED -> progress/review_<feature>.md`

or

`CHANGES_REQUESTED -> progress/review_<feature>.md`
"""

    def files_for(self, root: Path, workflow: str, decision: Decision, adapters: list[dict[str, str]]) -> dict[str, str]:
        if workflow == "simple":
            return {}
        docs_map = self.docs(root, decision.profile, workflow, decision)
        files = {
            "HARNESS.md": self.harness_md(workflow, decision),
            "scripts/init.sh": self.init_sh(decision.profile, workflow),
            ".harness/ENTRYPOINT.md": self.universal_entrypoint(workflow, decision),
            ".harness/config.json": self.project_config(root, workflow, decision),
            ".harness/workflow.json": self.workflow_json(workflow, decision, adapters),
            ".harness/adapters.json": self.adapters_json(adapters),
            ".harness/skills.json": self.empty_skills(),
            ".harness/agents.json": self.agent_registry(workflow),
            ".harness/docs.json": self.empty_capability_registry(),
            ".harness/rules.json": self.rule_registry(),
            ".harness/mcps.json": self.empty_capability_registry(),
            ".harness/memory.json": self.empty_memory(),
            ".harness/rules/data_storage.md": self.data_storage_rule(),
            "docs/verification.md": docs_map["docs/verification.md"],
            "docs/audit.md": docs_map["docs/audit.md"],
            "progress/current.md": "# Current Harness Session\n\nStatus: idle\n",
            ".harness/agents/tdd_lead.md": self.agent_file("tdd_lead"),
            ".harness/agents/red_test_author.md": self.agent_file("red_test_author"),
            ".harness/agents/green_implementer.md": self.agent_file("green_implementer"),
            ".harness/agents/refactor_specialist.md": self.agent_file("refactor_specialist"),
            ".harness/agents/architecture_lead.md": self.agent_file("architecture_lead"),
            ".harness/agents/blueprint_architect.md": self.agent_file("blueprint_architect"),
            ".harness/agents/context_auditor.md": self.agent_file("context_auditor"),
            ".harness/agents/business_rule_auditor.md": self.agent_file("business_rule_auditor"),
            ".harness/agents/code_quality_auditor.md": self.agent_file("code_quality_auditor"),
            ".harness/agents/test_verifier.md": self.agent_file("test_verifier"),
            ".harness/agents/confidence_reporter.md": self.agent_file("confidence_reporter"),
        }
        for adapter in adapters:
            files[adapter["file"]] = self.adapter_entrypoint(adapter, workflow, decision)
        if workflow == "sdd":
            files.update(docs_map)
            files.update(
                {
                    "feature_list.json": self.feature_list(root, decision.repo),
                    "CHECKPOINTS.md": "# CHECKPOINTS\n\n## C1 - Harness complete\n\n- [ ] `HARNESS.md`, `.harness/ENTRYPOINT.md`, `.harness/config.json`, `.harness/workflow.json`, `scripts/init.sh`, `feature_list.json`, and `progress/current.md` exist.\n- [ ] `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, `.harness/rules/data_storage.md`, and `.harness/mcps.json` exist.\n- [ ] `.harness/agents/leader.md`, `spec_author.md`, `implementer.md`, `reviewer.md`, and `auditor.md` exist.\n- [ ] `.harness/agents/tdd_lead.md`, `red_test_author.md`, `green_implementer.md`, and `refactor_specialist.md` exist.\n- [ ] Architecture and audit agents exist in `.harness/agents/` and are registered in `.harness/agents.json`.\n- [ ] Tool-specific adapters exist only when requested in `.harness/adapters.json`.\n- [ ] `docs/architecture.md`, `docs/conventions.md`, `docs/specs.md`, `docs/verification.md`, and `docs/audit.md` exist.\n- [ ] `./scripts/init.sh` passes.\n\n## C2 - State coherent\n\n- [ ] At most one feature is `in_progress`.\n- [ ] `progress/current.md` describes the active session or is idle.\n- [ ] `progress/history.md` contains completed session summaries.\n\n## C3 - Architecture respected\n\n- [ ] Changes stay within documented project boundaries.\n- [ ] Obsolete behavior is replaced rather than preserved by default.\n- [ ] No unrelated refactors are mixed into the active feature.\n\n## C4 - Verification real\n\n- [ ] Every completed requirement maps to at least one concrete test or check.\n- [ ] `./scripts/init.sh` was run and passed.\n- [ ] The reviewer verdict exists in `progress/review_<feature>.md`.\n- [ ] The audit verdict exists in `progress/audit_<feature>.md` and is `GO` or accepted `GO-WITH-RISK`.\n\n## C5 - Session closed cleanly\n\n- [ ] Feature status reflects the true state.\n- [ ] Temporary files and debug leftovers are removed.\n- [ ] Subagent outputs are stored in `progress/` according to `.harness/rules/data_storage.md`.\n",
                    "progress/history.md": "# Harness History\n\n",
                    "specs/.gitkeep": "",
                    ".harness/agents/leader.md": self.agent_file("leader"),
                    ".harness/agents/spec_author.md": self.agent_file("spec_author"),
                    ".harness/agents/implementer.md": self.agent_file("implementer"),
                    ".harness/agents/reviewer.md": self.agent_file("reviewer"),
                    ".harness/agents/auditor.md": self.agent_file("auditor"),
                }
            )
        return files
