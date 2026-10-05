# Terax — active 175-capability FA3 reconciliation (2026-09-28)

Terax is an **optional** terminal-first native Developer/ADE provider and a security/interaction pattern source. Its existing 17 invariants, including the five P0 invariants, strengthen existing FA3 authorities rather than creating new ones. `FA3-PROVIDER-TERAX-001` remains reference-only until independent provider admission.

## Sources of truth

- Donor entry: `FA3-DONOR-CRYNTA-TERAX-AI-001`; metadata only; no automatic import, install, selection or activation.
- Active capability baseline: `canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json` (175). Historical 143-capability receipts remain historical, not active admission evidence.
- Immutable source: `evidence/reference/terax-v0.8.6.json`; unreleased renderer and control patterns must be pinned to exact commit and classified non-promoting.
- ApplicationIntent / ReuseAssessment: `FA3-TERAX-APPLICATION-INTENT-2026-09-28` / `FA3-TERAX-REUSE-ASSESSMENT-2026-09-28`.
- Hardware Safety Envelope: `FA3-DEC-HARDWARE-SAFETY-2026-09-26`; HRB alone admits workload resources.

## Workload classification

Disabled reference: no provider process, optional accelerator discovery, lease or background polling. The collector observes provider-owned resources only; absence of Terax process alone does **not** prove there are no separately launched helper processes. CPU-only execution: explicit HRB admission, no accelerator lease. Accelerator-required execution: explicit HRB admission and specific lease bound to an actual resource class. WebGPU/Ghostty is UI/display acceleration; selecting a display GPU does not admit AI-compute.

## Safety and coexistence

No unsafe hardware tuning, upstream uninstallation, global shell environment mutation, fixed default port or upstream file takeover. The PR #410 footprint is a proposed reuse source and remains pending until reconciled against current main; the old PR #219 must never widen permanent CI from contents:read to contents:write.

## Evidence truth boundary

17 security/invariant regressions plus hardware admission and coexistence negative tests may yield CI PASS. Any current-host receipt is auxiliary provider evidence only and may never replace the 175 × (positive, negative, rollback) = 525 capability-specific obligations. No CI or fixture-derived receipt yields physical current-host PASS. Missing required physical evidence stays pending; the global promotion guard stays fail-closed.
