# FA3 Skill Fabric 1.2 — Agent Skills ecosystem expansion

Date: 2026-09-24

## Decision

The existing `FA3-SKILL-FABRIC-001` remains the only Skill Fabric profile. This change does not create a skill execution, authorization, security, workflow, model-routing, MCP, secrets, evidence, memory or resource authority.

The external Agent Skills ecosystem is treated as a compatibility and research surface. Discovery never implies installation, admission, activation or execution permission.

## Materialized layers

1. **Agent Skills compatibility.** Standard `SKILL.md` packages can be parsed from an immutable snapshot. The original bytes and source digest remain provenance. A compatible parse is emitted only as `UNTRUSTED_CANDIDATE`.
2. **FA3 normalization.** FA3 keeps its stricter requirements: version, trigger, guardrails, acceptance checks, explicit permissions, dependencies, distribution classification, security review and evaluation.
3. **Security inspection.** Static inspection is mandatory under `FA3-SCS-001`. Optional external or model-assisted scanners are evidence providers only and cannot grant admission or permissions.
4. **Routing evaluation.** Evaluation covers positive, negative, adversarial, routing-positive, routing-negative, non-selection and minimal-composition cases. Selected skills must remain a subset of the deterministic eligible set.
5. **Skill improvement candidates.** Observed evidence may produce an offline candidate, but an admitted skill is immutable. A changed version or digest must pass held-out validation, regression evaluation, security reinspection and a completely new Skill Package Admission.
6. **External Skill Radar.** Catalogs and skill repositories are pinned reference sources only. No automatic download, installation, activation or release bundling is permitted.

## Compatibility boundary

The Agent Skills specification's experimental `allowed-tools` field is parsed as metadata only. It is never interpreted as an FA3 authorization receipt. Executable assets in `scripts/` remain inert data until a separate canonical action path authorizes execution.

## Security boundary

The native baseline inspects instruction override, prompt injection, credential access, exfiltration, privilege escalation, shell execution, network bootstrap, path escape, MCP/tool poisoning, memory poisoning, obfuscated execution and self-modifying agent-instruction patterns.

An optional SkillSpector-style scanner may later be admitted as a provider. Provider output is evidence input only; `FA3-SCS-001` and the existing Skill Package Admission policy remain authoritative.

## Improvement boundary

SkillOpt-derived ideas are limited to an offline candidate loop:

`admitted skill -> observations -> candidate -> regression/security/held-out validation -> new admission`.

There is no live self-edit, no in-place update and no automatic promotion.

## Hardware Audit

The compatibility parser, normalizer, static security inspection and deterministic routing evaluator are CPU-only and vendor-neutral. No GPU/NPU is required. Any optional model-assisted semantic review or optimization must use the existing Model Router and HRB. Exact CPU/GPU/SKU assumptions are forbidden.

## Coexistence

FA3 does not install, replace, shadow or globally configure upstream Agent Skills tools, SkillSpector, SkillOpt, Claude/Copilot harnesses or independent skill repositories. External tools can coexist with FA3; FA3 artifacts remain namespaced and admission-controlled.
