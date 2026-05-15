# Harness

Install or inspect the universal harness runtime for the current project.

## Arguments

$ARGUMENTS

## Intent

Use this command when the user says things like:

- "install harness in this project"
- "apply harness here"
- "prepare this repo with harness"
- "use harness for this task: ..."

## Protocol

1. Resolve the project:
   - If `$ARGUMENTS` includes `--project`, a local path, `owner/repo`, or a GitHub URL, use that.
   - Otherwise the current working directory `.` is used implicitly.
2. Resolve the task:
   - Use `$ARGUMENTS` as the task text.
   - If the user only asked to install/apply harness, prefer `harness init` (covered below).
3. Find the CLI:
   - Prefer `harness` on PATH.
   - Fallback to `$HOME/.local/bin/harness`.
   - If neither exists, tell the user to install from the repo with `./install.sh`.
4. **Install in the current project (recommended):**
   ```bash
   harness init                       # installs SDD superset (includes TDD), all default adapters
   harness init --workflow tdd        # only TDD scaffolding
   harness init --detect-all-llms     # also inject the Harness block into .cursorrules/.windsurfrules/.junie/guidelines.md/.roo/rules/harness.md if present
   ```
   `harness init` runs from inside the project, defaults `--project .`, and creates `scripts/init.sh` (not at the project root).
5. **Inspect a specific task** (decide between simple/tdd/sdd per task):
   ```bash
   harness inspect --project . --task "<task>"
   ```
6. **Apply with an explicit task** when the user passed one:
   ```bash
   harness run --project . --task "<task>" --dry-run
   harness run --project . --task "<task>"
   ```
7. After applying, tell the user which workflow was selected and which files were installed.

## Registry CLI (simplified)

After install, register skills/agents/docs/rules/mcps with a short syntax:

```bash
# positional: name, path; --triggers auto-derived from name when omitted
harness agent add rn-expert agent:rn-expert
harness mcp add server-mcp mcp:server-mcp --context "Use before architecture decisions"
harness rule add ui-audit /path/to/SKILL.md --triggers widget,ui

# batch from YAML/JSON
harness import .harness/imports.yaml
```

`--project` defaults to `.` for all registry commands.

## Rules

- Do not hardcode local project aliases.
- Do not create tool-specific agent folders; use `.harness/agents/*`.
- Treat `HARNESS.md` and `.harness/ENTRYPOINT.md` as the source of truth after install.
- Tool-specific files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) are adapters only.
- The adapter block instructs every LLM to run `harness inspect` FIRST per task; do not bypass it.
