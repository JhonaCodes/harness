# Harness Entrypoint

<!-- BEGIN HARNESS_MANAGED -->

This is the neutral startup contract for any LLM working in this project.

## Startup

1. Read `HARNESS.md`.
2. Read `.harness/config.json`, `.harness/workflow.json`, `.harness/skills.json`, `.harness/agents.json`, `.harness/docs.json`, `.harness/rules.json`, `.harness/mcps.json`, and `.harness/memory.json` when present.
3. If available, inspect the task with:
   ```bash
   harness inspect --project . --task "<user task>"
   ```
4. Apply the decided workflow:
   - `simple`: direct work, minimal verification, no persistent state.
   - `tdd`: RED -> human checkpoint if expected behavior is ambiguous -> GREEN -> REFACTOR -> mandatory audit.
   - `sdd`: requirements -> design -> tasks -> human approval -> implementation -> review -> audit.
5. Use matching skills, agents, docs, rules, and MCP contexts from `.harness/*` and `~/.harness/*`.
6. Read durable project memory from `.harness/memory.json` and optional global memory if configured.

Default installed workflow: `{{workflow}}`.
Reason: {{reason}}
Selected skills: {{selected_skills}}.
Selected agents: {{selected_agents}}.
Selected docs: {{selected_docs}}.
Selected rules: {{selected_rules}}.
Selected MCPs: {{selected_mcps}}.

## Hard Rules

- Tool-specific files are adapters, not the source of truth.
- Do not skip the TDD ambiguity checkpoint when behavior is unclear.
- For SDD, do not skip `spec_ready` human approval.
- Do not mark work `done` without verification, review, and audit evidence.

<!-- END HARNESS_MANAGED -->
