# Audit Workflow

Use after meaningful implementation. This is a closure gate for TDD and SDD work, not an optional polish pass.

## Policy

- `simple`: no persistent audit state; use the smallest relevant verification.
- `tdd`: focused mandatory audit before closure.
- `sdd`: strict mandatory audit before any feature becomes `done`.
- Full/exhaustive audit is reserved for explicit audit/full-analysis tasks, high-risk SDD, or project/profile signals that require it.

## Roles

Execute these roles in order:

1. Context validator: confirm source of truth, selected skills, project docs, MCP/blueprints when relevant, and intended scope.
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

## Flutter Strict Audit Signals

When the project is Flutter/Dart or selected skills indicate Flutter/ReactiveNotifier, include:

- architecture and module boundaries;
- ReactiveNotifier usage when present;
- widget extraction, hardcoded values, const usage, rebuild scope;
- models, repositories, Result/error patterns;
- tests, performance, security, and scoring.

Do not require reading every `.dart` file unless the task explicitly asks for full audit/full analysis or the SDD feature is high risk.
