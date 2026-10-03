# FA3 Universal Capability Access

## Principle

FA3 must not make a user-facing capability depend exclusively on a third-party component whose upstream terms, service access, platform or hardware requirements exclude a user group.

This is a **capability-availability invariant**, not a mechanism for bypassing third-party terms.

A geographically or otherwise restricted donor may remain a research/reference source and may be offered as an optional implementation where lawful and admitted. It must not be the only route to the FA3 capability. The capability requires at least one FA3-native or independently rights-cleared implementation that is not subject to the donor-specific exclusion.

Applicable law still applies. "Universal" here means that **FA3 itself does not introduce a donor-specific exclusion** and does not rely on circumvention to make a restricted dependency appear available.

## Retroactive scope

The policy covers the entire canonical Donor & Reference Registry, not only newly added animation donors. The registry is structurally classified into:

- `INDEX_OR_DISCOVERY_ONLY`;
- `KNOWN_ACCESS_BARRIER_SIGNAL`;
- `ACCESS_RIGHTS_REVIEW_REQUIRED`;
- `NO_KNOWN_ACCESS_BARRIER_SIGNAL`.

The final category is not legal clearance. Exact rights for code, models, weights, data, assets, services and outputs remain separate under License & Rights.

## Restricted donors

A restricted donor is never deleted merely because it is restricted. Useful research and architecture knowledge may remain discoverable, subject to its terms.

Material adoption requires:

1. exact License & Rights/provenance review;
2. a globally usable substitute for the affected FA3 capability;
3. normal Security, Software Coexistence and Hardware Safety admission;
4. Model Router / HRB / provider boundaries where applicable;
5. explicit usage-edge traceability;
6. positive/negative/rollback evidence where runtime changes require Current Host proof.

## Clean FA3 implementation

When legally permitted, FA3 can reproduce a **function**, not restricted source material. The implementation path is:

```
restricted reference
       |
functional capability specification
       |
provenance / rights firewall
       |
independent implementation
       |
rights-cleared components + FA3 code
       |
independent tests and evidence
```

Restricted source code, weights, datasets or prohibited outputs are not copied into this path. VPNs, proxies, foreign hosting, artifact relocation or equivalent techniques are not accepted as a way to evade upstream restrictions.

## Selection

The Engine/Provider Selector may expose optional restricted providers only when they are currently lawful and admitted for the user/context. Provider unavailability must not remove the capability itself. There is no silent fallback: the user sees the available implementation choices.

## Hardware

The pre-existing CPU-only baseline and HRB authority remain unchanged. Optional GPU/NPU/vendor backends may improve performance, but a vendor-locked backend cannot be the only baseline implementation of an FA3 capability.

## Baseline

Capability count: **175**.
Capability delta: **0**.
Architectural authority delta: **0**.
