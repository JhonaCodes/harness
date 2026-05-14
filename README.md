# Harness

Universal Harness runtime for any LLM that needs to decide how much process a project task requires.

`HARNESS.md` and `.harness/ENTRYPOINT.md` are the source of truth inside a target project. Tool-specific files such as `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are optional adapters that point back to that universal contract.

Harness evaluates the project and task, selects configured skills, then chooses:

- `simple`: no persistent files, direct work.
- `tdd`: RED -> human checkpoint if expected behavior is ambiguous -> GREEN -> REFACTOR -> AUDIT.
- `sdd`: requirements -> design -> tasks -> human approval -> implementation -> review.

For SDD work, harness installs an agent process:

- leader coordinates and does not implement application code;
- spec_author writes requirements/design/tasks and stops for approval;
- implementer handles exactly one approved feature and writes tests;
- reviewer approves or rejects without editing code;
- subagents write outputs to `progress/` and return only file references.

## Install

```bash
./install.sh
```

This installs a shared runtime under `~/.harness/harness` and, when possible, installs the Codex skill under `~/.codex/skills/harness`.

## Use

```bash
harness inspect --project /path/to/project --task "fix failing login test"
harness run --project /path/to/project --task "fix failing login test" --dry-run
harness run --project /path/to/project --task "fix failing login test"
```

Register local aliases without hardcoding private paths in the repo:

```bash
harness register --alias api --path /path/to/project
harness run --project api --task "review current issues and implement them"
```

Use a GitHub repo directly:

```bash
harness run --project owner/repo --task "triage issues and set up SDD"
```

Choose adapters explicitly when needed:

```bash
harness run --project /path/to/project --task "fix failing login test" --adapters all
harness run --project /path/to/project --task "fix failing login test" --adapters agents,claude,gemini
harness run --project /path/to/project --task "fix failing login test" --adapters none
```

Default is `--adapters all` for broad tool coverage.

When TDD or SDD is selected, harness installs the universal runtime in the target project:

- `HARNESS.md` as the runtime contract.
- `.harness/ENTRYPOINT.md` as the neutral startup instructions.
- `.harness/config.json`, `.harness/workflow.json`, `.harness/adapters.json`, `.harness/skills.json`, `.harness/memory.json`.
- `.harness/agents/*` for universal SDD role definitions when SDD is selected.
- Optional adapter files such as `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`, depending on `--adapters`.

When `simple` is selected, harness installs nothing.

## Skills

Global skills live in `~/.harness/skills.json`; project skills live in `.harness/skills.json`.

```json
[
  {
    "name": "backend-api",
    "triggers": ["api", "endpoint", "auth", "database"],
    "description": "Backend API implementation rules",
    "path": "/path/to/SKILL.md"
  }
]
```

Harness selects skills by task text, project profile, and file context.

Manage project skills without editing JSON manually:

```bash
harness skill add --project api \
  --name backend-api \
  --triggers api,endpoint,auth,database \
  --path /path/to/SKILL.md

harness skill list --project api
```

Manage project memory:

```bash
harness memory add --project api --key api_style --value "Use /v1 endpoints only"
harness memory list --project api
```

## Process Rules

- One feature at a time.
- No `done` without green verification.
- TDD pauses for human clarification when expected behavior is ambiguous.
- `progress/current.md` is live session state.
- `progress/history.md` is append-only session history.
- If blocked, document the blocker in `progress/current.md` and stop.

## LLM Adoption

Any LLM can adopt harness by reading `HARNESS.md` and `.harness/ENTRYPOINT.md` in the target project.

SDD role definitions live only under `.harness/agents/*`.

Adapters are tool entrypoints only. New adapters can be added through `.harness/adapters.json` without changing the core runtime.
