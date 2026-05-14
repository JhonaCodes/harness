# Gemini Harness Entrypoint

Use `scripts/harness.py` as the source of truth for project workflow decisions.

If the user did not provide a project, ask for one of:

- GitHub URL
- `owner/repo`
- local path
- registered alias

Workflow:

```bash
python3 scripts/harness.py inspect --project <project> --task "<task>"
python3 scripts/harness.py run --project <project> --task "<task>" --dry-run
python3 scripts/harness.py run --project <project> --task "<task>"
```

Do not install TDD or SDD state when the decision is `simple`.
Read selected skill paths from the decision output when present.
