# Gemini Harness Adapter

This file is a tool adapter. The universal source of truth is the Harness runtime itself and, inside an applied project, `HARNESS.md` plus `.harness/ENTRYPOINT.md`.

If the user did not provide a project, ask for one of:

- GitHub URL
- `owner/repo`
- local path
- registered alias

Workflow:

```bash
python3 scripts/harness.py inspect --project <project> --task "<task>"
python3 scripts/harness.py run --project <project> --task "<task>" --adapters all --dry-run
python3 scripts/harness.py run --project <project> --task "<task>" --adapters all
```

Do not install TDD or SDD state when the decision is `simple`.
Read selected skill paths from the decision output when present.

When the target project already contains harness files, first read:

- `HARNESS.md`
- `.harness/ENTRYPOINT.md`
- `.harness/config.json`
- `.harness/workflow.json`
- `.harness/skills.json`
- `.harness/memory.json`

For SDD:

- Coordinate as leader.
- Use separate spec author, implementer, and reviewer roles.
- Keep subagent outputs in `progress/`.
- Work on one feature at a time.
- Stop at `spec_ready` until human approval is explicit.
