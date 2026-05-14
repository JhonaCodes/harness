# CHECKPOINTS

## C1 - Harness complete

- [ ] `HARNESS.md`, `.harness/ENTRYPOINT.md`, `.harness/config.json`, `.harness/workflow.json`, `init.sh`, `feature_list.json`, and `progress/current.md` exist.
- [ ] `.harness/agents/leader.md`, `spec_author.md`, `implementer.md`, `reviewer.md`, and `auditor.md` exist.
- [ ] Tool-specific adapters exist only when requested in `.harness/adapters.json`.
- [ ] `docs/architecture.md`, `docs/conventions.md`, `docs/specs.md`, `docs/verification.md`, and `docs/audit.md` exist.
- [ ] `./init.sh` passes.

## C2 - State coherent

- [ ] At most one feature is `in_progress`.
- [ ] `progress/current.md` describes the active session or is idle.
- [ ] `progress/history.md` contains completed session summaries.

## C3 - Architecture respected

- [ ] Changes stay within documented project boundaries.
- [ ] Obsolete behavior is replaced rather than preserved by default.
- [ ] No unrelated refactors are mixed into the active feature.

## C4 - Verification real

- [ ] Every completed requirement maps to at least one concrete test or check.
- [ ] `./init.sh` was run and passed.
- [ ] The reviewer verdict exists in `progress/review_<feature>.md`.
- [ ] The audit verdict exists in `progress/audit_<feature>.md` and is `GO` or accepted `GO-WITH-RISK`.

## C5 - Session closed cleanly

- [ ] Feature status reflects the true state.
- [ ] Temporary files and debug leftovers are removed.
- [ ] Subagent outputs are stored in `progress/`.
