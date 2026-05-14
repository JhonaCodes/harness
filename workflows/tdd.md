# TDD Workflow

Use for bugs, regressions, focused behavior changes, and small features.

1. RED: reproduce or specify behavior with a failing test.
2. HUMAN CHECKPOINT: if expected behavior is ambiguous, stop and ask for clarification.
3. GREEN: implement the smallest passing change.
4. REFACTOR: clean up while preserving behavior.
5. AUDIT: run mandatory focused audit before closure.

## Closure Rules

- Do not close TDD work without a failing-before/passing-after test, unless a written justification explains why a test is not applicable.
- Link every functional change to a test, check, or explicit verification note.
- Run `./init.sh`.
- Write audit evidence to `progress/current.md` or a task-specific audit note.
- Final status must include `GO`, `GO-WITH-RISK`, or `NO-GO`.
