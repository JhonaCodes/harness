# Claude Harness Adapter

This file is a compatibility adapter. The universal source of truth is the Harness runtime itself and, inside an applied project, `HARNESS.md` plus `.harness/ENTRYPOINT.md`.

1. If no project URL, `owner/repo`, alias, or local path was provided, ask for it.
2. Run:
   ```bash
   python3 scripts/harness.py inspect --project <project> --task "<task>"
   ```
3. Read the JSON decision:
   - `simple`: do the task directly; do not install files.
   - `tdd`: run dry-run, apply TDD harness, then use RED -> human checkpoint if behavior is ambiguous -> GREEN -> REFACTOR -> AUDIT.
   - `sdd`: run dry-run, apply SDD harness, then create specs and stop for human approval.
4. If selected skills include `path`, read those skill files before acting.
5. Never hardcode private project paths into this repository.

When working inside a project where harness has already been applied, first read:

- `HARNESS.md`
- `.harness/ENTRYPOINT.md`
- `.harness/config.json`
- `.harness/workflow.json`
- `.harness/skills.json`
- `.harness/memory.json`

## Subagent Rules For SDD

- Act as leader by default.
- The leader coordinates and does not edit application code directly.
- Use spec_author for specs, implementer for code/tests, reviewer for approval.
- Keep one feature active at a time.
- Instruct subagents to write outputs under `progress/` and reply only with the file reference.
- Do not mark work done until verification is green and reviewer output exists.
