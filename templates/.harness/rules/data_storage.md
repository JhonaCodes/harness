# Data Storage Rule

Harness state and evidence must be portable, explicit, and reviewable.

## Canonical Locations

- `feature_list.json`: SDD feature state only.
- `specs/<feature>/`: SDD requirements, design, and tasks only.
- `progress/current.md`: active session state.
- `progress/history.md`: completed session summaries.
- `progress/*_<feature>.md`: subagent outputs, review verdicts, audit verdicts, confidence reports, and verification evidence.
- `.harness/memory.json`: durable project notes that should influence future tasks.
- `.harness/{skills,agents,docs,rules,mcps}.json`: capability registries only.
- `.harness/rules/`: reusable project rules.
- `.harness/mcp-context/`: local descriptions of when MCP sources must be consulted.

## Hard Rules

- Store subagent results in files under `progress/`; chat-only subagent reports are not closure evidence.
- Use relative paths inside Harness registries when the file lives in the repo.
- Do not store secrets, tokens, credentials, private keys, or production personal data in Harness files.
- Do not store machine-local absolute paths unless the entry intentionally points to a user-local global skill outside the repo.
- Do not duplicate long generated artifacts in chat; write them to the canonical file and reference the path.
- Keep specs, progress, audit, and memory separate. Do not use one file as a dumping ground for all state.
- Every completed TDD/SDD task must leave verification evidence and residual risk notes in `progress/`.
