# Harness

<!-- BEGIN HARNESS_MANAGED -->

Universal Harness runtime for any LLM.

Workflow: `{{workflow}}`

Reason: {{reason}}

The source of truth is this file plus `.harness/ENTRYPOINT.md`. Tool-specific files are adapters only.

Use RED -> human checkpoint if expected behavior is ambiguous -> GREEN -> REFACTOR -> mandatory audit.

1. Write or identify a failing test for the behavior.
2. If the expected behavior is ambiguous, stop and ask for human clarification before implementing.
3. Implement the smallest change that passes.
4. Refactor while tests remain green.
5. Run `./init.sh`.
6. Run the focused audit from `docs/audit.md`.
7. Record test and audit evidence in `progress/current.md`.
8. Do not close without a test or written no-test justification.

<!-- END HARNESS_MANAGED -->
