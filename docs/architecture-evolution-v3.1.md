# FA3 architecture evolution — federated lifecycle and measured admission

Date: 2026-09-14

This document explains the architecture contracts implemented by `FA3-DEC-ARCHITECTURE-EVOLUTION-2026-09-14`. It is explanatory documentation only; canonical JSON records and executable gates remain authoritative.

## 1. Capability composition

FA3 keeps one centralized trust root while allowing domain-specific lifecycle projections (Satellites) to version and validate independently. Satellites never own identity, authorization, secrets, HRB, evidence, supply-chain or promotion authority.

Capability cardinality is release-scoped. The active count is resolved from `canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json`; neither a permanent global `143` nor a new fixed Core count is an architectural invariant.

## 2. Hardware portability

Portable admission is split into three records:

1. **Host Attestation** proves which exact host executed a workload or qualification.
2. **Compute Profile** describes measured, multidimensional resource capability.
3. **Workload Resource Envelope** declares the minimum/maximum dimensions required by a workload.

CU/TU-style aggregate scores may be exposed for diagnostics or GUI presentation, but they cannot authorize production admission. Missing required dimensions fail closed, and surplus performance in one dimension cannot compensate for a failed requirement in another dimension.

## 3. Upstream dependency qualification

The governing rule is:

> Range selects; digest proves.

A semantic-version range may discover a candidate. Production identity requires immutable source, artifact, SBOM and provenance identifiers. Qualification progresses through an ordered state machine; staging cannot claim current-host execution and cannot write or authorize production state.

Risk-tiered promotion does not weaken the common prerequisites:

- `AUTO` may remove human approval only for narrowly defined low-risk changes;
- `REVIEW` requires maintainer approval;
- `CRITICAL` requires multiple distinct approvals;
- all tiers still require current-host qualification and Acceptance PASS before production promotion.

## 4. OCI execution

OCI is an optional hermetic build/execution transport, not a new FA3 authority. Production containers are rootless, digest-pinned, read-only, no-new-privileges, capability-dropped and default to `Network=none`. Accelerator access must be materialized from an HRB lease; static CUDA ordinals are not an entitlement mechanism.

For PyTorch3D, the OCI path preserves the existing exact upstream revision and source-build policy. A prequalified source archive is SHA-256 verified inside the build, and the qualification receipt binds that digest to the accepted upstream revision. Wheel, SBOM and provenance identities remain required.

## 5. FFmpeg zero-copy candidate

FA3 records upstream commit `09bf8dab5b8f5c9d1c9280af4dec7f84e8c0fe8b` as the candidate for Torch DNN CUDA frame-to-tensor zero-copy. The claim is intentionally narrow: this does not assert a fully GPU-resident decode/colorspace/inference/encode path.

A temporary exact-upstream backport may be qualified if needed. A permanent FA3 FFmpeg fork is forbidden, and any temporary backport must be retired when an equivalent stable upstream release passes the same gates.

## 6. Evidence boundary

This architecture change adds no capability and no architectural authority. Reference CI may prove policy, schema, state-machine and fail-closed behavior, but it cannot synthesize `CURRENT_HOST_PRODUCTION_E2E_PASS`.

PyTorch3D OCI execution remains `PENDING_CURRENT_HOST` until a real admitted host produces valid execution evidence. The same boundary applies to dependency promotion: staging qualification is never production authority.

## 7. Executable verification

The dedicated reference checks are:

```bash
PYTHONPATH=src python -m unittest tests.test_architecture_evolution -v
PYTHONPATH=src python src/fa3_architecture_evolution_gate.py --root .
PYTHONPATH=src python src/fa3_capability_count_dehardcode_gate.py --root .
PYTHONPATH=src python src/fa3_pytorch3d_gate.py
PYTHONPATH=src python src/fa3_release_projection_gate.py
```

Global closure is still controlled by the permanent canonical/promotion workflow. A green domain gate is not a substitute for the global gate.
