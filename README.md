# Harness

Portable runtime for Codex, Claude, Gemini, or any LLM agent that needs to decide how much process a project task requires.

Harness evaluates the project and task, selects configured skills, then chooses:

- `simple`: no persistent files, direct work.
- `tdd`: RED -> GREEN -> REFACTOR -> AUDIT.
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

When TDD or SDD is selected, harness installs auto-adoption entrypoints in the target project:

- `AGENTS.md` for Codex-compatible agents.
- `CLAUDE.md` for Claude.
- `GEMINI.md` for Gemini.
- `HARNESS.md` as the shared runtime contract.
- `.harness/config.json`, `.harness/skills.json`, `.harness/memory.json`.

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
- `progress/current.md` is live session state.
- `progress/history.md` is append-only session history.
- If blocked, document the blocker in `progress/current.md` and stop.

## LLM Entrypoints

- Codex: `SKILL.md`
- Claude: `CLAUDE.md`
- Gemini: `GEMINI.md`

All three point to the same runtime: `scripts/harness.py`.
