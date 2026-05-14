# Harness

<!-- BEGIN HARNESS_MANAGED -->

Universal Harness runtime for any LLM.

Workflow: `{{workflow}}`

Reason: {{reason}}

The source of truth is this file plus `.harness/ENTRYPOINT.md`. Tool-specific files are adapters only.

Load selected skills, agents, docs, rules, and MCP contexts from `.harness/*` and `~/.harness/*` before decisions that match their triggers. MCP entries are context references, not tool-specific server installers.

Use strict Spec Driven Development:

`pending -> spec_ready -> human approval -> in_progress -> implementer -> reviewer -> auditor -> done`

## Runtime Roles

- Leader: coordinates, decomposes, and launches subagents. The leader does not implement application code.
- Spec author: writes requirements/design/tasks and stops at `spec_ready`.
- Implementer: implements exactly one approved feature and writes tests.
- Reviewer: reviews only, runs verification, and writes a verdict.
- Auditor: validates context, business rules, code quality, tests, confidence, and go/no-go.

## State Rules

- Work on one feature at a time.
- Keep `progress/current.md` updated during the session.
- Subagents write outputs to files under `progress/` and return only a short reference.
- Move the closure summary to `progress/history.md` before marking work complete.
- Do not implement a pending SDD feature until specs exist.
- Do not implement a `spec_ready` feature until a human approves it.
- Every completed `R<n>` requirement must map to at least one test.
- Every `done` feature must have reviewer approval and `progress/audit_<feature>.md` with `GO` or accepted `GO-WITH-RISK`.

<!-- END HARNESS_MANAGED -->
