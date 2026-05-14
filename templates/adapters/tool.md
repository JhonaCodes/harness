# {{adapter_name}}

<!-- BEGIN HARNESS_MANAGED -->

## Harness Adapter

This file is a tool adapter. The source of truth is `HARNESS.md` and `.harness/ENTRYPOINT.md`.

Before answering, editing, or delegating:

1. Read `HARNESS.md`.
2. Read `.harness/ENTRYPOINT.md`.
3. Read `.harness/config.json`, `.harness/workflow.json`, `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, and `.harness/memory.json` when present.
4. Apply the workflow decided by the universal Harness runtime.
5. Use selected project/global skills, agents, docs, and rules when their triggers match.

Default installed workflow: `{{workflow}}`.
Reason: {{reason}}

Useful command when a shell is available:

```bash
harness inspect --project . --task "<user task>"
```

<!-- END HARNESS_MANAGED -->
