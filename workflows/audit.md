# Audit Workflow

Use after meaningful implementation. This is a closure gate for TDD and SDD work, not an optional polish pass.

## Policy

- `simple`: no persistent audit state; use the smallest relevant verification.
- `tdd`: focused mandatory audit before closure.
- `sdd`: strict mandatory audit before any feature becomes `done`.
- Full/exhaustive audit is reserved for explicit audit/full-analysis tasks, high-risk SDD, or project/profile signals that require it.

## Roles

Execute these roles in order:

1. Context validator: confirm source of truth, selected capabilities, project docs, MCP/blueprints when relevant, and intended scope.
2. Business-rule validator: check permissions, workflow states, invariants, domain rules, and user-facing constraints.
3. Code-quality auditor: review correctness, architecture, layering, maintainability, security, and regression risk.
4. Test verifier: map changed behavior to tests/checks, identify missing coverage, and verify command evidence.
5. Confidence reporter: produce final scores, residual risks, and a `GO`, `GO-WITH-RISK`, or `NO-GO` signal.

## Evidence Rules

- Findings must be evidence-based, preferably with `file:line`.
- Use severities: `critical`, `high`, `medium`, `low`, `info`.
- No false positives: verify before flagging.
- If evidence is missing, report it as a gap instead of inventing confidence.
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

Harness does not hardcode project architecture, framework rules, or domain-specific audit rules.

- Register skills for specialized execution guidance.
- Register agents for role-specific behavior.
- Register docs for source-of-truth references.
- Register rules for architecture, domain, security, testing, or framework constraints.

The audit must load and apply registered entries whose triggers match the task, project profile, or files touched. Exhaustive framework-specific audits should come from registered rules/docs/skills, not from the harness core.
