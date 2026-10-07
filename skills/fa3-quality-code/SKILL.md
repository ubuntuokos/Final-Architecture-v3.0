---
name: fa3-quality-code
description: Task-scoped FA3 source-quality review for generic generated-code noise, weak comments and non-deterministic automation patterns.
version: 1.0.0
trigger: quality.code
---

# FA3 Quality Code

## use_when
Use for newly generated or materially changed source code, scripts and developer automation.

## inputs
- The bounded source artifact or diff.
- Existing project coding conventions.
- The applicable canonical contracts and executable tests.

## procedure
1. Review comments for useful intent, invariants and non-obvious rationale.
2. Flag decorative section banners, generation-origin comments and vague maintenance notes.
3. Review fixed sleeps and similar timing shortcuts as quality locks.
4. Preserve executable semantics unless the task explicitly includes a code correction.
5. Rely on tests and canonical gates for correctness evidence.

## guardrails
- Never remove or weaken a test, gate, security check or evidence boundary to make code appear cleaner.
- Never treat comment cleanup as runtime correctness evidence.
- Do not introduce dependencies, network access or execution authority.
- Project coding conventions outrank generic stylistic preference.

## pitfalls
- Deleting comments that explain important invariants.
- Performing unrelated refactors during quality cleanup.
- Equating fewer comments with better code.

## acceptance_checks
- No blocking CODE findings remain.
- Remaining comments explain useful intent rather than restating syntax.
- Quality cleanup does not change authority, feature scope or verified behavior.
