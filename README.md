# Harness

Universal Harness runtime for any LLM that needs to decide how much process a project task requires.

`HARNESS.md` and `.harness/ENTRYPOINT.md` are the source of truth inside a target project. Tool-specific files such as `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are optional adapters that point back to that universal contract.

Harness evaluates the project and task, selects configured skills/agents/docs/rules, then chooses:

- `simple`: no persistent files, direct work.
- `tdd`: RED -> human checkpoint if expected behavior is ambiguous -> GREEN -> REFACTOR -> mandatory audit.
- `sdd`: requirements -> design -> tasks -> human approval -> implementation -> review -> audit.

For SDD work, harness installs an agent process:

- leader coordinates and does not implement application code;
- spec_author writes requirements/design/tasks and stops for approval;
- implementer handles exactly one approved feature and writes tests;
- reviewer approves or rejects without editing code;
- auditor validates context, business rules, code quality, tests, confidence, and go/no-go;
- subagents write outputs to `progress/` and return only file references.

## Install

```bash
./install.sh
```

This installs a shared runtime under `~/.harness/harness` and the `harness` CLI under `~/.local/bin/harness`.
When run in an interactive terminal, the installer asks which LLM entrypoints to install. You can select multiple targets:

- `codex`: Codex skill.
- `claude`: Claude Code slash command.
- `gemini`: Gemini global context.
- `opencode`: OpenCode global instructions.
- `none`: runtime and CLI only.

For scripted installs, pass targets explicitly:

```bash
./install.sh --targets codex,claude,gemini,opencode
./install.sh --targets none
HARNESS_TARGETS=codex,opencode ./install.sh
```

The runtime is universal. LLM-specific files only teach each tool how to discover and invoke Harness.

Detailed guide: [Instalar Harness En Cualquier LLM](docs/install-any-llm.md).

## Repository Structure

The CLI converges in `scripts/main.py`. `scripts/harness.py` is only a backward-compatible wrapper.

Runtime code is split by context under `scripts/harness_core/`:

- `cli.py`: argparse assembly and command dispatch.
- `commands.py`: command handlers.
- `projects.py`: aliases, repo resolution, and profile detection.
- `inspection.py`: repository inspection and workflow classification.
- `decisioning.py`: workflow decision model.
- `capabilities.py`: skills, agents, docs, rules, and memory registries.
- `rendering.py`: installed file rendering.
- `apply.py`: managed file writes and apply reports.
- `models.py`, `constants.py`, `io.py`: shared models, constants, and JSON persistence.

Installable file templates live in `templates/`, mirroring the files Harness can write into a target project.

## Use

From any shell:

```bash
harness inspect --project /path/to/project --task "fix failing login test"
harness run --project /path/to/project --task "fix failing login test" --dry-run
harness run --project /path/to/project --task "fix failing login test"
```

From Codex after install, invoke the `harness` skill:

```text
usa harness para instalar harness en este proyecto
```

From Claude Code after install, use the slash command:

```text
/harness instala harness en este proyecto
```

From Gemini or OpenCode after installing those targets, tell the model:

```text
instala harness en este proyecto
```

If a tool does not support a global entrypoint, use the CLI directly or tell the model to read this repo's `README.md`; after harness is applied to a project, all LLMs should read `HARNESS.md` and `.harness/ENTRYPOINT.md`.

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
- `.harness/config.json`, `.harness/workflow.json`, `.harness/adapters.json`, `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, `.harness/memory.json`.
- `.harness/agents/*` for universal SDD role definitions when SDD is selected.
- `docs/audit.md` for the mandatory TDD/SDD closure gate.
- Optional adapter files such as `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`, depending on `--adapters`.

When `simple` is selected, harness installs nothing.

## Registries

Global registries live in `~/.harness/{skills,agents,docs,rules}.json`; project registries live in `.harness/{skills,agents,docs,rules}.json`.

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

Harness selects entries by task text, project profile, and file context. The core does not hardcode framework architecture rules; register project-specific rules/docs/agents/skills and let triggers activate them.

Manage project registries without editing JSON manually:

```bash
harness skill add --project api \
  --name backend-api \
  --triggers api,endpoint,auth,database \
  --path /path/to/SKILL.md

harness skill list --project api

harness rule add --project api --name api-layering --triggers api,repository,service --path /path/to/rules.md
harness doc add --project api --name api-contract --triggers contract,endpoint --path /path/to/openapi.md
harness agent add --project api --name security-auditor --triggers security,auth --path /path/to/agent.md
```

Manage project memory:

```bash
harness memory add --project api --key api_style --value "Use /v1 endpoints only"
harness memory list --project api
```

## Process Rules

- One feature at a time.
- No `done` without green verification, reviewer approval, and audit `GO` or accepted `GO-WITH-RISK`.
- TDD pauses for human clarification when expected behavior is ambiguous.
- TDD closure requires a test or explicit no-test justification plus audit report.
- `progress/current.md` is live session state.
- `progress/history.md` is append-only session history.
- If blocked, document the blocker in `progress/current.md` and stop.

## LLM Adoption

Any LLM can adopt harness by reading `HARNESS.md` and `.harness/ENTRYPOINT.md` in the target project.

SDD role definitions live only under `.harness/agents/*`.

Adapters are tool entrypoints only. New adapters can be added through `.harness/adapters.json` without changing the core runtime.
