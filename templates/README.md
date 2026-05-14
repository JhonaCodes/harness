# Harness Templates

These templates document the files Harness can install into a target project.

Runtime generation still injects project-specific values such as workflow,
profile, selected capabilities, repository name, and adapter list. Placeholders
use `{{name}}` syntax so future renderers can replace them deterministically.

Template groups:

- `HARNESS.*.md`: workflow contracts.
- `init.sh`: verification entrypoint.
- `.harness/*`: universal runtime state.
- `.harness/agents/*`: universal SDD roles.
- `docs/*`: verification, audit, conventions, architecture, and specs.
- `progress/*`: session state.
- `adapters/*`: tool-specific entrypoints that point back to the universal contract.
- `feature_list.json` and `CHECKPOINTS.md`: SDD backlog and closure gates.
