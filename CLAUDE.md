# Claude Harness Entrypoint

When the user invokes harness, use this repository as the workflow runtime.

1. If no project URL, `owner/repo`, alias, or local path was provided, ask for it.
2. Run:
   ```bash
   python3 scripts/harness.py inspect --project <project> --task "<task>"
   ```
3. Read the JSON decision:
   - `simple`: do the task directly; do not install files.
   - `tdd`: run dry-run, apply TDD harness, then use RED -> GREEN -> REFACTOR -> AUDIT.
   - `sdd`: run dry-run, apply SDD harness, then create specs and stop for human approval.
4. If selected skills include `path`, read those skill files before acting.
5. Never hardcode private project paths into this repository.
