# Install Harness In Any LLM

Harness has two installation layers:

1. Universal runtime: installs the `harness` CLI and a local runtime copy.
2. Tool entrypoints: installs a small instruction or command so each LLM tool knows how to invoke Harness.

The universal runtime is always installed. Tool entrypoints are optional, and you can select multiple targets.

## Interactive Install

From the `harness` repository:

```bash
./install.sh
```

The installer asks:

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

## Non-Interactive Install

For scripts, CI, or reproducible installs:

```bash
./install.sh --targets codex,claude,gemini,opencode
./install.sh --targets codex,opencode
./install.sh --targets manual
./install.sh --targets none
HARNESS_TARGETS=codex,claude ./install.sh
```

`none` installs only the runtime and CLI. Use it when a tool has no global instruction mechanism or when you want to invoke Harness manually.

## What Each Target Installs

- `codex`: installs the `harness` skill in the Codex skills directory.
- `claude`: installs the `/harness` command for Claude Code.
- `gemini`: adds a managed Harness section to Gemini global context.
- `opencode`: adds a managed Harness section to OpenCode global instructions.
- `manual`: installs runtime/CLI and prints setup instructions for any LLM.
- `none`: installs no LLM entrypoints.

Tool-specific files only point back to the universal runtime. The source of truth remains `HARNESS.md` and `.harness/ENTRYPOINT.md` inside each prepared project.

## Invoke Harness From Each LLM

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
Read the harness repository README and use the `harness` CLI.
First run:
harness inspect --project <path|url|owner/repo> --task "<task>"
Then, if the project should be prepared:
harness run --project <path|url|owner/repo> --task "<task>"
```

Manual target:

```bash
./install.sh --targets manual
```

This prints a ready-to-copy prompt that tells any LLM how to call `harness inspect`, `harness run --dry-run`, and `harness run`.

## Recommended Flow

1. Install Harness once on your machine:

   ```bash
   ./install.sh
   ```

2. Select the LLM tools you use.

3. Open any project in your LLM tool.

4. Ask:

   ```text
   install harness in this project
   ```

5. Harness inspects the task and automatically decides:

   - `simple`: installs nothing in the project.
   - `tdd`: installs minimum runtime, verification, and audit files.
   - `sdd`: installs full runtime, specs, backlog, roles, and audit files.

## If The LLM Does Not Detect Harness

Use the CLI directly:

```bash
harness inspect --project /path/to/project --task "describe the task"
harness run --project /path/to/project --task "describe the task" --dry-run
harness run --project /path/to/project --task "describe the task"
```

If `harness` is not in `PATH`, use:

```bash
$HOME/.local/bin/harness inspect --project /path/to/project --task "describe the task"
```

## Important Rule

No matter which LLM you use, after Harness is applied to a project the LLM must read:

- `HARNESS.md`
- `.harness/ENTRYPOINT.md`
- `.harness/config.json`
- `.harness/workflow.json`
- `.harness/skills.json`
- `.harness/mcps.json`
- `.harness/memory.json`

Those files are the universal contract. Tool-specific files for Codex, Claude, Gemini, or OpenCode only help the tool start.
