---
name: harness
description: Runtime that evaluates a project task, selects relevant skills, and decides whether to use simple, TDD, or SDD workflow. Use when the user invokes harness, wants repo automation, issue-driven work, TDD/SDD selection, project workflow setup, or a portable workflow for Codex, Claude, Gemini, or another LLM.
---

# Harness

Use this skill as the entrypoint for project work. The harness evaluates the project and task, selects relevant skills/capabilities, decides `simple`, `tdd`, or `sdd`, and installs only the minimum files needed.

## Decision Rule

- `simple`: use for small questions, one-off edits, obvious fixes, or work that does not need repo-level process. Do not install files.
- `tdd`: use for bugs, focused behavior changes, or small features where tests should drive implementation.
- `sdd`: use for multi-issue backlogs, product/API contracts, cross-module work, human-approved specs, or when the user explicitly asks for SDD.
- `auto`: inspect the request and repo, then choose one of the above. Default to `simple` unless the work clearly benefits from persistent workflow state.

## If The Project Is Missing

If the user does not provide a GitHub URL, repo name, local path, or known alias, ask for one concise input:

> Enviame el URL del repo, `owner/name`, o la ruta local del proyecto donde quieres aplicar el harness.

Do not guess a random project.

## Commands

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
  --dry-run
```

Apply:

```bash
python3 <this-skill>/scripts/harness.py run \
  --project <path|alias|owner/repo|url> \
  --task "<task>"
```

Register a user-local alias:

```bash
python3 <this-skill>/scripts/harness.py register --alias api --path /path/to/project
```

## What Gets Installed

- `simple`: no files; writes only a dry-run/report message when requested.
- `tdd`: auto-adoption entrypoints (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`), `HARNESS.md`, `.harness/config.json`, `.harness/skills.json`, `.harness/memory.json`, `docs/verification.md`, `init.sh`, `progress/current.md`.
- `sdd`: TDD files plus `feature_list.json`, `CHECKPOINTS.md`, `docs/specs.md`, `docs/architecture.md`, `docs/conventions.md`, `progress/history.md`, `specs/.gitkeep`, and `.claude/agents/{leader,spec_author,implementer,reviewer}.md`.

## Safety

- Always dry-run before applying.
- Existing files are not blindly overwritten.
- Managed sections use markers.
- Conflicts are written to `progress/harness_apply_report.md`.
- SDD remains strict: `pending -> spec_ready -> human approval -> in_progress -> review -> done`.

## Skills Registry

Harness reads optional skill registries from:

- `~/.harness/skills.json`
- `<project>/.harness/skills.json`

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
harness memory add --project <project> --key rule --value "project-specific note"
harness memory list --project <project>
```
