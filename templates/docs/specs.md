# Spec Driven Development

Each SDD feature uses:

- `requirements.md` with testable `R<n>` requirements.
- `design.md` with implementation decisions.
- `tasks.md` with executable checklist items.

Flow:

`pending -> spec_ready -> human approval -> in_progress -> implementer -> reviewer -> auditor -> done`

## Process Rules

- The leader coordinates and does not implement application code.
- The spec author creates specs and stops at `spec_ready`.
- The implementer works on exactly one approved feature.
- The reviewer never edits code; it approves or rejects with concrete evidence.
- The auditor validates context, business rules, code quality, tests, confidence, and go/no-go.
- Subagents write results to files in `progress/` and return only the file reference.
- Do not mark a feature `done` until `./init.sh` is green, review is approved, and `progress/audit_<feature>.md` is `GO` or accepted `GO-WITH-RISK`.
