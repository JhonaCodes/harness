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
   - Otherwise use the current working directory: `.`.
2. Resolve the task:
   - Use `$ARGUMENTS` as the task text.
   - If the user only asked to install/apply harness, use: `prepare this project with harness`.
3. Find the CLI:
   - Prefer `harness`.
   - Fallback to `$HOME/.local/bin/harness`.
   - If neither exists, tell the user to install from the repo with `./install.sh`.
4. Run inspect first:
   ```bash
   harness inspect --project <project> --task "<task>"
   ```
5. Run dry-run:
   ```bash
   harness run --project <project> --task "<task>" --dry-run
   ```
6. If the user asked to install/apply harness, run the real apply:
   ```bash
   harness run --project <project> --task "<task>"
   ```
7. After applying, tell the user which workflow was selected and which files were installed.

## Rules

- Do not hardcode local project aliases.
- Do not create tool-specific agent folders; use `.harness/agents/*`.
- Treat `HARNESS.md` and `.harness/ENTRYPOINT.md` as the source of truth after install.
- Tool-specific files are adapters only.
