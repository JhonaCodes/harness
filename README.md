# Harness

Universal Harness runtime for any LLM that needs to decide how much process a project task requires.

Harness inspects a project and a task, selects configured skills/agents/docs/rules, then chooses the smallest useful workflow:

- `simple`: direct work, no persistent files.
- `tdd`: RED -> human checkpoint when behavior is ambiguous -> GREEN -> REFACTOR -> mandatory audit.
- `sdd`: requirements -> design -> tasks -> human approval -> implementation -> review -> audit.

`HARNESS.md` and `.harness/ENTRYPOINT.md` are the source of truth inside a prepared project. Tool-specific files such as `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are only adapters that point back to that universal contract.

## Install

Install Harness once on your machine:

```bash
./install.sh
```

The installer always installs:

- global runtime: `~/.harness/harness`
- global CLI: `~/.local/bin/harness`

When run in an interactive terminal, it asks which LLM entrypoints to install:

```text
Where should Harness install LLM entrypoints?

  1) codex      Codex skill
  2) claude     Claude Code slash command
  3) gemini     Gemini global context
  4) opencode   OpenCode global instructions
  5) none       Runtime and CLI only
  6) manual     Runtime, CLI, and manual setup instructions
```

You can answer with numbers or names:

```text
1,2,4
codex,claude,opencode
manual
all
none
```

Non-interactive installs:

```bash
./install.sh --targets all
./install.sh --targets codex,claude
./install.sh --targets codex,opencode
./install.sh --targets manual
./install.sh --targets none
HARNESS_TARGETS=codex,opencode ./install.sh
```

If `harness` is not found after install, add `~/.local/bin` to your `PATH` or call it directly:

```bash
$HOME/.local/bin/harness --help
```

Extended install guide: [Install Harness In Any LLM](docs/install-any-llm.md).

## Install Targets

Targets install discovery entrypoints for LLM tools. They do not change the universal runtime.

| Target | What it installs | How you use it |
| --- | --- | --- |
| `codex` | Global Codex skill at `$CODEX_HOME/skills/harness` | Ask Codex to use `harness` |
| `claude` | Claude Code command at `$CLAUDE_HOME/commands/harness.md` | Run `/harness ...` |
| `gemini` | Managed Harness section in `$GEMINI_HOME/GEMINI.md` | Ask Gemini to install/apply Harness |
| `opencode` | Managed Harness section in `$OPENCODE_HOME/AGENTS.md` | Ask OpenCode to install/apply Harness |
| `manual` | No entrypoint; prints setup instructions | Copy the instructions into any LLM |
| `none` | No LLM entrypoint | Use the CLI directly |

Default paths are based on your home directory:

- `CODEX_HOME`: defaults to `~/.codex`
- `CLAUDE_HOME`: defaults to `~/.claude`
- `GEMINI_HOME`: defaults to `~/.gemini`
- `OPENCODE_HOME`: defaults to `~/.config/opencode`

## Use From An LLM

After installing the target for your tool, open a project and ask the LLM to apply Harness.

Codex:

```text
use harness to install harness in this project
```

Claude Code:

```text
/harness install harness in this project
```

Gemini:

```text
install harness in this project
```

OpenCode:

```text
install harness in this project
```

Any other LLM:

```text
Use the Harness CLI.
First run:
harness inspect --project <path|url|owner/repo> --task "<task>"

Then, if Harness should prepare the project, run:
harness run --project <path|url|owner/repo> --task "<task>"

After Harness is applied, read HARNESS.md and .harness/ENTRYPOINT.md.
```

If the LLM does not detect Harness automatically, use the CLI directly from a terminal.

You can also install with manual instructions:

```bash
./install.sh --targets manual
```

This installs the runtime and CLI, then prints a ready-to-copy prompt for any LLM.

## Use From CLI

Inspect a project without writing files:

```bash
harness inspect --project /path/to/project --task "fix failing login test"
```

Dry-run the selected workflow:

```bash
harness run --project /path/to/project --task "fix failing login test" --dry-run
```

Apply the selected workflow:

```bash
harness run --project /path/to/project --task "fix failing login test"
```

Use a GitHub repository:

```bash
harness run --project owner/repo --task "triage issues and set up SDD"
```

Register a local alias:

```bash
harness register --alias api --path /path/to/project
harness run --project api --task "review current issues and implement them"
```

## Apply Harness To A Project

`harness run` decides whether the task needs `simple`, `tdd`, or `sdd`.

For `simple`, Harness writes no project files.

For `tdd`, Harness installs the minimum project runtime:

- `HARNESS.md`
- `.harness/ENTRYPOINT.md`
- `.harness/config.json`
- `.harness/workflow.json`
- `.harness/skills.json`
- `.harness/agents.json`
- `.harness/docs.json`
- `.harness/rules.json`
- `.harness/mcps.json`
- `.harness/memory.json`
- `docs/verification.md`
- `docs/audit.md`
- `init.sh`
- `progress/current.md`

For `sdd`, Harness installs the TDD runtime plus:

- `feature_list.json`
- `CHECKPOINTS.md`
- `docs/specs.md`
- `docs/architecture.md`
- `docs/conventions.md`
- `progress/history.md`
- `specs/.gitkeep`
- `.harness/agents/*`

Project adapters can be selected independently:

```bash
harness run --project /path/to/project --task "fix failing login test" --adapters all
harness run --project /path/to/project --task "fix failing login test" --adapters agents,claude,gemini
harness run --project /path/to/project --task "fix failing login test" --adapters none
```

Default is `--adapters all`.

## Global Vs Project Runtime

Global install:

- Lives under `~/.harness/harness`.
- Provides the `harness` CLI.
- Optionally installs LLM entrypoints so tools can discover Harness.
- Is installed once per machine.

Project application:

- Happens when you run `harness run --project ...`.
- Writes `HARNESS.md` and `.harness/*` into the target project only when the task needs TDD or SDD.
- Makes any LLM read the same project contract.
- Keeps tool-specific files as adapters only.

This distinction matters: installing Harness globally does not modify your projects. Applying Harness to a project does.

## Registries And Memory

Harness can select user-defined skills, agents, docs, rules, and MCP contexts by trigger.

MCP support in this version is a universal context registry. Harness records which MCP context/config reference an LLM should read and when to use it. It does not write tool-specific MCP server configuration files for Codex, Claude, Gemini, or OpenCode.

Global registries:

```text
~/.harness/skills.json
~/.harness/agents.json
~/.harness/docs.json
~/.harness/rules.json
~/.harness/mcps.json
```

Project registries:

```text
.harness/skills.json
.harness/agents.json
.harness/docs.json
.harness/rules.json
.harness/mcps.json
```

Example entry:

```json
{
  "name": "backend-api",
  "triggers": ["api", "endpoint", "auth", "database"],
  "description": "Backend API implementation rules",
  "path": "/path/to/SKILL.md"
}
```

Manage project registries:

```bash
harness skill add --project api --name backend-api --triggers api,endpoint,auth --path /path/to/SKILL.md
harness skill list --project api

harness agent add --project api --name security-auditor --triggers security,auth --path /path/to/agent.md
harness doc add --project api --name api-contract --triggers api,contract --path /path/to/openapi.md
harness rule add --project api --name api-layering --triggers api,repository --path /path/to/rules.md
harness mcp add --project api --name server-mcp --triggers architecture,blueprint --path /path/to/mcp-context.md --context "Use before implementation decisions that depend on project architecture."
```

Manage project memory:

```bash
harness memory add --project api --key api_style --value "Use /v1 endpoints only"
harness memory list --project api
```

## Process Rules

- One feature at a time.
- TDD requires a test or an explicit no-test justification.
- TDD pauses when expected behavior is ambiguous.
- SDD does not implement `spec_ready` work before human approval.
- No `done` without verification, reviewer approval, and audit `GO` or accepted `GO-WITH-RISK`.
- Subagent outputs go under `progress/` and should return only file references.

## Repository Structure

The CLI converges in `scripts/main.py`. `scripts/harness.py` is only a backward-compatible wrapper.

Runtime code is split by context under `scripts/harness_core/`:

- `cli.py`: argparse assembly and command dispatch.
- `commands.py`: command handlers.
- `projects.py`: aliases, repo resolution, and profile detection.
- `inspection.py`: repository inspection and workflow classification.
- `decisioning.py`: workflow decision model.
- `capabilities.py`: skills, agents, docs, rules, MCP contexts, and memory registries.
- `rendering.py`: installed file rendering.
- `apply.py`: managed file writes and apply reports.
- `models.py`, `constants.py`, `io.py`: shared models, constants, and JSON persistence.

Installable file templates live in `templates/`, mirroring the files Harness can write into a target project.
