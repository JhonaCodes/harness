# Harness

Portable runtime for Codex, Claude, Gemini, or any LLM agent that needs to decide how much process a project task requires.

Harness evaluates the project and task, selects configured skills, then chooses:

- `simple`: no persistent files, direct work.
- `tdd`: RED -> GREEN -> REFACTOR -> AUDIT.
- `sdd`: requirements -> design -> tasks -> human approval -> implementation -> review.

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

## LLM Entrypoints

- Codex: `SKILL.md`
- Claude: `CLAUDE.md`
- Gemini: `GEMINI.md`

All three point to the same runtime: `scripts/harness.py`.
