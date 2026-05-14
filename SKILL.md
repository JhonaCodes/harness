---
name: harness
description: Universal runtime that evaluates a project task, selects relevant skills, and decides whether to use simple, TDD, or SDD workflow. Use when the user invokes harness, wants repo automation, issue-driven work, TDD/SDD selection, project workflow setup, or an LLM-agnostic workflow.
---

# Harness

Use this skill as the entrypoint for project work. The harness evaluates the project and task, selects relevant skills/agents/docs/rules, decides `simple`, `tdd`, or `sdd`, and installs only the minimum files needed.

## Decision Rule

- `simple`: use for small questions, one-off edits, obvious fixes, or work that does not need repo-level process. Do not install files.
- `tdd`: use for bugs, focused behavior changes, or small features where tests should drive implementation; pause for human clarification when expected behavior is ambiguous and close with mandatory audit.
- `sdd`: use for multi-issue backlogs, product/API contracts, cross-module work, human-approved specs, or when the user explicitly asks for SDD.
- `auto`: inspect the request and repo, then choose one of the above. Default to `simple` unless the work clearly benefits from persistent workflow state.

## If The Project Is Missing

If the user does not provide a GitHub URL, repo name, local path, or known alias, ask for one concise input:

> Send the repo URL, `owner/name`, or local project path where Harness should be applied.

Do not guess a random project.

## Commands

Install the runtime from the repository:

```bash
./install.sh
```

Interactive installs ask which LLM entrypoints to install. Scripted installs can select multiple targets:

```bash
./install.sh --targets codex,claude,gemini,opencode
./install.sh --targets manual
./install.sh --targets none
HARNESS_TARGETS=codex,opencode ./install.sh
```

Inspect first:

```bash
python3 <this-skill>/scripts/harness.py inspect \
  --project <path|alias|owner/repo|url> \
  --task "<task>"
```

Run with dry-run before applying:

```bash
python3 <this-skill>/scripts/harness.py run \
  --project <path|alias|owner/repo|url> \
  --task "<task>" \
  --adapters all \
  --dry-run
```

Apply:

```bash
python3 <this-skill>/scripts/harness.py run \
  --project <path|alias|owner/repo|url> \
  --task "<task>" \
  --adapters all
```

After repository install, Codex can invoke this skill by name:

```text
use harness to install harness in this project
```

Claude Code uses the installed slash command:

```text
/harness install harness in this project
```

Gemini and OpenCode use their installed global instructions. After install, ask:

```text
install harness in this project
```

Register a user-local alias:

```bash
python3 <this-skill>/scripts/harness.py register --alias api --path /path/to/project
```

## What Gets Installed

- `simple`: no files; writes only a dry-run/report message when requested.
- `tdd`: universal runtime (`HARNESS.md`, `.harness/ENTRYPOINT.md`, `.harness/config.json`, `.harness/workflow.json`, `.harness/adapters.json`, `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, `.harness/mcps.json`, `.harness/memory.json`), `docs/verification.md`, `docs/audit.md`, `init.sh`, `progress/current.md`, plus optional adapters from `--adapters`.
- `sdd`: TDD files plus `feature_list.json`, `CHECKPOINTS.md`, `docs/specs.md`, `docs/architecture.md`, `docs/conventions.md`, `progress/history.md`, `specs/.gitkeep`, and universal roles in `.harness/agents/{leader,spec_author,implementer,reviewer,auditor}.md`.

Adapter options:

- `--adapters all`: install built-in tool adapters.
- `--adapters agents,claude,gemini`: install only selected adapters.
- `--adapters none`: install no tool-specific adapter files.

`HARNESS.md` and `.harness/ENTRYPOINT.md` are always the source of truth. Tool-specific files are adapters only.

## Safety

- Always dry-run before applying.
- Existing files are not blindly overwritten.
- Managed sections use markers.
- Conflicts are written to `progress/harness_apply_report.md`.
- TDD requires test evidence or a written no-test justification, then audit.
- SDD remains strict: `pending -> spec_ready -> human approval -> in_progress -> review -> audit -> done`.
- SDD `done` requires reviewer approval plus audit `GO` or accepted `GO-WITH-RISK`.

## Registries

Harness reads optional registries from:

- `~/.harness/{skills,agents,docs,rules,mcps}.json`
- `<project>/.harness/{skills,agents,docs,rules,mcps}.json`

Each entry:

```json
{
  "name": "backend-api",
  "triggers": ["api", "endpoint", "auth", "database"],
  "description": "Backend API implementation rules",
  "path": "/path/to/SKILL.md"
}
```

Use commands instead of editing JSON manually:

```bash
harness skill add --project <project> --name backend-api --triggers api,endpoint,auth --path /path/to/SKILL.md
harness skill list --project <project>
harness agent add --project <project> --name security-auditor --triggers security,auth --path /path/to/agent.md
harness doc add --project <project> --name api-contract --triggers api,contract --path /path/to/doc.md
harness rule add --project <project> --name api-layering --triggers api,repository --path /path/to/rules.md
harness mcp add --project <project> --name server-mcp --triggers architecture,blueprint --path /path/to/mcp-context.md --context "Use before implementation decisions that depend on architecture."
harness memory add --project <project> --key rule --value "project-specific note"
harness memory list --project <project>
```

Do not hardcode framework architecture rules in harness. Register specialized audit, framework, security, product, architecture rules/docs/agents, or MCP contexts with triggers; harness references them when they match task text, profile, and file context.
