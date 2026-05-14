# Harness

<!-- BEGIN HARNESS_MANAGED -->

Universal Harness runtime for any LLM.

Workflow: `{{workflow}}`

Reason: {{reason}}

The source of truth is this file plus `.harness/ENTRYPOINT.md`. Tool-specific files are adapters only.

Load selected skills, agents, docs, rules, and MCP contexts from `.harness/*` and `~/.harness/*` before decisions that match their triggers. MCP entries are context references, not tool-specific server installers.

Store state, specs, subagent outputs, audit evidence, generated artifacts, and durable memory according to `.harness/rules/data_storage.md`.

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
