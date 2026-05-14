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
for f in HARNESS.md .harness/ENTRYPOINT.md .harness/config.json .harness/workflow.json .harness/skills.json .harness/agents.json .harness/docs.json .harness/rules.json .harness/mcps.json docs/verification.md docs/audit.md progress/current.md; do
  if [ -f "$f" ]; then ok "Exists $f"; else fail "Missing $f"; EXIT_CODE=1; fi
done
{sdd_validation}

echo "── Project checks ─────────────────────────────────────"
{command_text}

if [ $EXIT_CODE -eq 0 ]; then ok "Harness environment ready."; else fail "Harness environment not ready."; fi
exit $EXIT_CODE
"""

    def harness_md(self, workflow: str, decision: Decision) -> str:
        if workflow == "tdd":
            return f"""# Harness

{BEGIN_MARKER}

Universal Harness runtime for any LLM.

Workflow: `tdd`

Reason: {decision.reason}

The source of truth is this file plus `.harness/ENTRYPOINT.md`. Tool-specific files are adapters only.

Load selected skills, agents, docs, rules, and MCP contexts from `.harness/*` and `~/.harness/*` before decisions that match their triggers. MCP entries are context references, not tool-specific server installers.

Use RED -> human checkpoint if expected behavior is ambiguous -> GREEN -> REFACTOR -> mandatory audit.

1. Write or identify a failing test for the behavior.
2. If the expected behavior is ambiguous, stop and ask for human clarification before implementing.
3. Implement the smallest change that passes.
4. Refactor while tests remain green.
5. Run `./init.sh`.
6. Run the focused audit from `docs/audit.md`.
7. Record test and audit evidence in `progress/current.md`.
8. Do not close without a test or written no-test justification.

{END_MARKER}
"""
        return f"""# Harness

{BEGIN_MARKER}

Universal Harness runtime for any LLM.

Workflow: `sdd`

Reason: {decision.reason}

The source of truth is this file plus `.harness/ENTRYPOINT.md`. Tool-specific files are adapters only.

Load selected skills, agents, docs, rules, and MCP contexts from `.harness/*` and `~/.harness/*` before decisions that match their triggers. MCP entries are context references, not tool-specific server installers.

Use strict Spec Driven Development:

`pending -> spec_ready -> human approval -> in_progress -> implementer -> reviewer -> auditor -> done`

## Runtime Roles

- Leader: coordinates, decomposes, and launches subagents. The leader does not implement application code.
- Spec author: writes requirements/design/tasks and stops at `spec_ready`.
- Implementer: implements exactly one approved feature and writes tests.
- Reviewer: reviews only, runs verification, and writes a verdict.
- Auditor: validates context, business rules, code quality, tests, confidence, and go/no-go.

## State Rules

- Work on one feature at a time.
- Keep `progress/current.md` updated during the session.
- Subagents write outputs to files under `progress/` and return only a short reference.
- Move the closure summary to `progress/history.md` before marking work complete.

Do not implement a pending SDD feature until specs exist.
Do not implement a `spec_ready` feature until a human approves it.
Every completed `R<n>` requirement must map to at least one test.
Every `done` feature must have reviewer approval and `progress/audit_<feature>.md` with `GO` or accepted `GO-WITH-RISK`.

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

{END_MARKER}
"""

    @staticmethod
    def adapter_entrypoint(adapter: dict[str, str], workflow: str, decision: Decision) -> str:
        return f"""# {adapter["name"]}

{BEGIN_MARKER}

## Harness Adapter

This file is a tool adapter. The source of truth is `HARNESS.md` and `.harness/ENTRYPOINT.md`.

Before answering, editing, or delegating:

1. Read `HARNESS.md`.
2. Read `.harness/ENTRYPOINT.md`.
3. Read `.harness/config.json`, `.harness/workflow.json`, `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, `.harness/mcps.json`, and `.harness/memory.json` when present.
4. Apply the workflow decided by the universal Harness runtime.
5. Use selected project/global skills, agents, docs, rules, and MCP contexts when their triggers match.

Default installed workflow: `{workflow}`.
Reason: {decision.reason}

Useful command when a shell is available:

```bash
harness inspect --project . --task "<user task>"
```

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
        verification = "# Verification\n\nRun:\n\n```bash\n./init.sh\n```\n\n"
        verification += f"Profile: `{profile}`\nWorkflow: `{workflow}`\n\n"
        if workflow in {"tdd", "sdd"}:
            verification += "Closure requires a completed audit from `docs/audit.md` with `GO`, `GO-WITH-RISK`, or `NO-GO`.\n"
        conventions = """# Conventions

- Prefer existing project patterns.
- Keep changes scoped to the active task.
- Replace obsolete flows instead of preserving outdated behavior by default.
- Use selected skills, agents, docs, rules, and MCP contexts from the harness decision when available.
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
- Do not mark a feature `done` until `./init.sh` is green, review is approved, and `progress/audit_<feature>.md` is `GO` or accepted `GO-WITH-RISK`.
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
2. Run `./init.sh`. If it fails, stop and report the blocker.
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
6. Run `./init.sh`.
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
5. Verify `./init.sh` evidence.
6. Write `progress/audit_<feature>.md`.
7. Do not mark `done`; the leader applies the final state after the audit verdict.

Final response:

`GO -> progress/audit_<feature>.md`

or

`GO-WITH-RISK -> progress/audit_<feature>.md`

or

`NO-GO -> progress/audit_<feature>.md`
"""
        return """# Reviewer Agent

You review only. You do not edit code.

## Protocol

1. Read `HARNESS.md`, `docs/architecture.md`, `docs/conventions.md`, `docs/specs.md`, and `CHECKPOINTS.md`.
2. Inspect modified files and `progress/impl_<feature>.md`.
3. Verify every requirement maps to at least one test.
4. Verify every task is complete or has a documented blocker.
5. Run `./init.sh`.
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
            "init.sh": self.init_sh(decision.profile, workflow),
            ".harness/ENTRYPOINT.md": self.universal_entrypoint(workflow, decision),
            ".harness/config.json": self.project_config(root, workflow, decision),
            ".harness/workflow.json": self.workflow_json(workflow, decision, adapters),
            ".harness/adapters.json": self.adapters_json(adapters),
            ".harness/skills.json": self.empty_skills(),
            ".harness/agents.json": self.empty_capability_registry(),
            ".harness/docs.json": self.empty_capability_registry(),
            ".harness/rules.json": self.empty_capability_registry(),
            ".harness/mcps.json": self.empty_capability_registry(),
            ".harness/memory.json": self.empty_memory(),
            "docs/verification.md": docs_map["docs/verification.md"],
            "docs/audit.md": docs_map["docs/audit.md"],
            "progress/current.md": "# Current Harness Session\n\nStatus: idle\n",
        }
        for adapter in adapters:
            files[adapter["file"]] = self.adapter_entrypoint(adapter, workflow, decision)
        if workflow == "sdd":
            files.update(docs_map)
            files.update(
                {
                    "feature_list.json": self.feature_list(root, decision.repo),
                    "CHECKPOINTS.md": "# CHECKPOINTS\n\n## C1 - Harness complete\n\n- [ ] `HARNESS.md`, `.harness/ENTRYPOINT.md`, `.harness/config.json`, `.harness/workflow.json`, `init.sh`, `feature_list.json`, and `progress/current.md` exist.\n- [ ] `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, and `.harness/mcps.json` exist.\n- [ ] `.harness/agents/leader.md`, `spec_author.md`, `implementer.md`, `reviewer.md`, and `auditor.md` exist.\n- [ ] Tool-specific adapters exist only when requested in `.harness/adapters.json`.\n- [ ] `docs/architecture.md`, `docs/conventions.md`, `docs/specs.md`, `docs/verification.md`, and `docs/audit.md` exist.\n- [ ] `./init.sh` passes.\n\n## C2 - State coherent\n\n- [ ] At most one feature is `in_progress`.\n- [ ] `progress/current.md` describes the active session or is idle.\n- [ ] `progress/history.md` contains completed session summaries.\n\n## C3 - Architecture respected\n\n- [ ] Changes stay within documented project boundaries.\n- [ ] Obsolete behavior is replaced rather than preserved by default.\n- [ ] No unrelated refactors are mixed into the active feature.\n\n## C4 - Verification real\n\n- [ ] Every completed requirement maps to at least one concrete test or check.\n- [ ] `./init.sh` was run and passed.\n- [ ] The reviewer verdict exists in `progress/review_<feature>.md`.\n- [ ] The audit verdict exists in `progress/audit_<feature>.md` and is `GO` or accepted `GO-WITH-RISK`.\n\n## C5 - Session closed cleanly\n\n- [ ] Feature status reflects the true state.\n- [ ] Temporary files and debug leftovers are removed.\n- [ ] Subagent outputs are stored in `progress/`.\n",
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
