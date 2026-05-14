# SDD Workflow

Use for issue backlogs, API/product contracts, architecture, multi-module changes, and work requiring human-approved specs.

1. Create requirements.
2. Create design.
3. Create tasks.
4. Stop for human approval.
5. Implement only after approval.
6. Review traceability from requirements to tests.
7. Audit before `done`.

## Roles

- Leader: decomposes and coordinates; does not implement application code.
- Spec author: writes specs only and stops at `spec_ready`.
- Implementer: implements exactly one approved feature and writes tests.
- Reviewer: reviews only and writes a verdict.
- Auditor: validates context, business rules, code quality, tests, confidence, and go/no-go.

## State

- One feature at a time.
- `progress/current.md` tracks active work.
- Subagent outputs are written to `progress/`.
- `progress/history.md` receives completed session summaries.
- Do not mark `done` without green verification, reviewer approval, and audit `GO` or accepted `GO-WITH-RISK`.
- Every completed requirement must trace `R<n> -> test/check -> audit verdict`.
