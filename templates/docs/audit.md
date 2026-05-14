# Audit

Workflow: `{{workflow}}`
Mode: `{{audit_mode}}`
Policy: risk-based mandatory closure gate.

Use this audit after meaningful implementation and before closing TDD/SDD work.

## Required Roles

Execute in order:

1. Context validator: verify source of truth, selected capabilities, project docs, relevant MCP/blueprints, and scope.
2. Business-rule validator: check permissions, workflow states, invariants, domain rules, and user-facing constraints.
3. Code-quality auditor: check correctness, architecture, layering, maintainability, security, and regression risk.
4. Test verifier: map changed behavior to tests/checks, verify commands run, and identify coverage gaps.
5. Confidence reporter: summarize confidence and issue `GO`, `GO-WITH-RISK`, or `NO-GO`.

## Evidence Rules

- Findings require evidence, preferably `file:line`.
- Use severities: `critical`, `high`, `medium`, `low`, `info`.
- Report missing evidence as a gap.
- Do not edit code during audit.

## Required Output

1. Context status
2. Business-rule status
3. Code-quality findings
4. Test verification
5. Confidence report
6. Go/No-Go
7. Residual risks

## Extension Inputs

Harness does not hardcode domain architecture rules. Load and apply selected skills, agents, docs, and rules when their triggers match the task/project context.

{{capability_sections}}
