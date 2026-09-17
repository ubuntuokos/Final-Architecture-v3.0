# FA3 Tools Fabric + ConvertX integration

## Canonical decision

ConvertX is **not** an FA3 architectural root and is **not** a replacement for specialized conversion providers. Generic file conversion is canonicalized as `FA3-FILE-CONVERSION-001`; ConvertX is a replaceable long-tail provider under `FA3-PROVIDER-CONVERTX-001`.

Current state:

- capability/profile: `FA3-FILE-CONVERSION-001` — P1 OPTIONAL;
- provider: `FA3-PROVIDER-CONVERTX-001` — P2 `QUARANTINED`;
- production machine execution: **disabled**;
- candidate validation: permitted only through the FA3-owned pinned adapter path;
- XeLaTeX: **DENY**;
- current-host runtime evidence: `PENDING_REAL_HOST_EXECUTION`.

## Tools surface

`FA3-TOOLS-FABRIC-001` provides task-first navigation in the Control Center. The Conversion intent routes to the canonical file-conversion profile. The GUI has no execution authority and cannot bypass provider policy.

The Control Center exposes ConvertX status but deliberately provides no quarantine-bypassing install, direct `/convert`, or production execution action.

## Provider precedence

Specialized FA3 providers keep precedence for domains they own. ConvertX is intended for long-tail/fallback conversion and human utility use after promotion. A caller requests an FA3 conversion intent; it does not select arbitrary ConvertX CLI arguments or arbitrary internal converter names.

## Pinned upstream adapter contract

ConvertX v0.18.0 does not expose an official stable public machine API. `FA3-CONVERTX-ADAPTER-CONTRACTS-001` therefore pins the candidate adapter to the observed v0.18.0 internal web flow:

1. `GET /` creates authentication/job state in the isolated unauthenticated worker.
2. `POST /upload` uploads exactly one FA3-staged input.
3. `POST /convert` submits an allowlisted `<target>,<converter>` pair and the single staged filename.
4. `POST /progress/:jobId` is polled for the server-rendered result fragment.
5. The candidate executor follows exactly one server-issued `/download/:userId/:jobId/:fileName` result link whose job ID matches the bootstrap job.

The executor does **not** decode the upstream JWT to derive user identity and does **not** predict the output filename. It accepts only loopback origins, rejects cross-origin redirects, rejects output overwrite/symlinks, enforces size limits, and records SHA-256.

This contract is version-specific. A future ConvertX release is not automatically API-compatible and requires revalidation before the reference release can be changed.

## Pair lifecycle

`FA3-CONVERTX-CONVERSION-ALLOWLIST-001` is deny-by-default.

- `CANDIDATE`: may be planned and exercised only through explicit isolated candidate validation.
- `ACTIVE`: may be used for production machine execution only after pair-specific evidence and provider promotion.

Provider promotion never implicitly turns all candidate pairs into active production routes.

## Security boundary

The provider contract requires:

- non-root worker;
- read-only root filesystem;
- dropped Linux capabilities;
- no-new-privileges;
- seccomp and AppArmor when available;
- no host filesystem mounts;
- per-job ephemeral workspace;
- outbound network denied by default;
- digest-pinned image;
- CPU, memory, PID, timeout and output quotas;
- input/output provenance and SHA-256;
- regression coverage for path traversal, malformed media, archive/resource bombs and egress denial.

XeLaTeX and LaTeX-family direct selection remain denied because they are outside the accepted FA3 trust boundary.

## Resource-admission boundary

FA3 currently has verified current-host enforcement for the accelerator-specific `AcceleratorExecutionLease@1` path. That contract carries accelerator identity/VRAM semantics and is **not** treated as an authoritative substitute for CPU/memory admission of a CPU-oriented ConvertX candidate worker.

This integration does not create a new architectural resource authority. Until existing FA3 resource governance exposes an authoritative CPU/memory admission verifier, the current-host ConvertX collector fails closed with no execution and no PASS claim.

## Evidence semantics

GitHub-hosted CI may prove only reference/static conformance and the behavior of the candidate adapter against a controlled mock v0.18.0 flow. It cannot prove the production host, container isolation, egress denial, a real digest-pinned ConvertX worker, or a real CPU/memory resource-admission decision.

`evidence/reference/fa3-convertx-reference-pending.json` therefore remains `PENDING_CURRENT_HOST` with:

- `runtime_claimed: false`;
- `production_admitted: false`;
- `machine_execution_enabled: false`.

## Promotion gate

P2/`QUARANTINED` → P1/`APPROVED` requires all of the following:

- static conformance PASS;
- security regressions PASS;
- pinned adapter contract and candidate executor materialized;
- authoritative CPU/memory resource-admission PASS;
- digest-pinned runtime PASS;
- real current-host safe-pair E2E conversion PASS;
- real output hash/provenance evidence;
- worker egress-denial PASS;
- resource-limit PASS;
- pair-specific evidence followed by explicit `CANDIDATE` → `ACTIVE` transition.

Document edits or GitHub-hosted CI alone cannot perform this promotion.
