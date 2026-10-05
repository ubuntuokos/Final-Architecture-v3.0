---
name: fa3-quality-copy
description: Task-scoped FA3 quality review for generated copy, labels, publishing text and user-facing claims.
version: 1.0.0
trigger: quality.copy
---

# FA3 Quality Copy

## use_when
Use for new or materially changed user-facing prose, labels, marketing text, publishing copy, CTAs and generated descriptions.

## inputs
- The bounded text artifact or changed text.
- Available product facts and evidence.
- The application tone or publishing contract when one exists.

## procedure
1. Apply the canonical CORE quality rules.
2. Remove placeholder prose and unsupported absolute claims.
3. Prefer concrete statements over generic hype and mechanical AI phrasing.
4. Verify that metrics, ratings, benchmarks and provider/model claims have evidence.
5. Review CTAs and labels for useful, action-specific language.
6. Emit blocking findings and quality-lock warnings without changing product facts.

## guardrails
- Do not fabricate evidence, metrics, capabilities, providers, models or customer claims.
- Do not convert stylistic preference into canonical policy.
- Do not create a new product promise or feature scope.
- This skill grants no publishing, model, tool or mutation authority.

## pitfalls
- Replacing one generic slogan with another.
- Treating fluent prose as evidence for a factual claim.
- Using superlatives without an auditable basis.

## acceptance_checks
- No blocking CORE or COPY findings remain.
- Claims are supported by available evidence or are clearly non-factual opinion/description.
- Text remains consistent with the application-specific tone contract.
