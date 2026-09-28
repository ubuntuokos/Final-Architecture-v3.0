# Signed Skill Fabric / Codex current-host execution and evidence

This stacked PR adds a real-host execution path after the existing Codex
current-host provider admission. It does NOT manufacture trust, signatures,
host credentials or CI-equivalent production evidence.

## Required deployed prerequisites

1. Merge the stacked Skill Fabric PR chain after review and deploy the exact
   source commit on the FA3 workstation. The machine-wide, root-managed
   /etc/fa3/trust/skill-runtime.json must independently pin that exact commit,
   the SHA-256 of installed canonical/skill-registry.json, and the existing
   pinned Codex provider/archive. The running unprivileged service must not
   be able to edit its trusted pin, root CA or Security Governance public key.
2. The existing pinned Codex 0.151.0 Linux x86_64 archive and installed
   executable must agree byte-for-byte, and existing Codex current-host
   evidence/receipts/codex-current-host.json must PASS the existing gate.
   The pre-existing ChatGPT login is accessed only through the normal
   Codex provider preflight. Nothing silently switches models or providers.
3. Existing FA3 Skill Package Admission, deterministic Selection and
   Language Admission issuers must each produce an exact task-bound
   fa3.authenticated-approval-receipt.v2 receipt under an FA3_SKILL_RUNTIME
   Security Governance-signed role grant and real PKI certificate. These
   records are embedded in the private bundle as authority_receipt for
   admission, selection and language_context. The skill package must match
   the current canonical registry/native SHA256 pins and pass existing
   package admission, not a synthetic good_package fixture.
4. Create a private bundle outside the repository (0600):
   schema: fa3.skill-codex-host-bundle.v1;
   provider_id: FA3-PROVIDER-CODEX-001; task_id; skill_id; registry_entry;
   package; admission; selection; lease; intent; language_context.
   Its task ID and lease must match, task scope must be developer, and the
   private records must match the exact signed claims and installed registry.

## Real execution

Run the manual fa3-skill-codex-current-host.yml workflow only on the
existing self-hosted fa3-current-host Linux x86_64 runner after the
existing Codex current-host producer succeeds. The runner is nonroot,
checks the independent trust config and existing provider receipt,
re-verifies issuer X.509 chain and signed Security Governance role grants,
checks actual native skill bytes and runs the pinned real Codex binary.
It runs one explicit skill-consuming and one plain worktree worker,
requires actual delivery SHA256, bounded mutation, no forbidden tool
surface and complete cleanup. Only then does it write
reports/skill-codex-current-host-report.json with OBSERVED_PASS, explicitly
UNSIGNED_HOST_OBSERVATION_AWAITING_EXISTING_EVIDENCE_AUTHORITY.

## Existing Evidence authority signs AFTER observation

An authorized CURRENT_HOST_EVIDENCE_SIGNER issues a *separate* existing
fa3.authenticated-approval-receipt.v2 with
receipt_type=CURRENT_HOST_EVIDENCE_SIGNING, scope=FA3_RELEASE_ACCEPTANCE,
source_commit equal to deployed exact HEAD, and payload:

  schema: fa3.skill-codex-current-host-evidence-binding.v1
  artifact_sha256: SHA-256 of exact raw observation report file bytes
  subject_id: CAP-080
  provider_id: FA3-PROVIDER-CODEX-001
  source_commit: exact approved commit
  qualification_id: assigned existing current-host qualification ID

Place the signed receipt only in the existing permitted Evidence path
evidence/receipts/skill-codex-current-host.json and run
PYTHONPATH=src python src/fa3_skill_host_gate.py --root .
A boolean flag, a missing PKI certificate, changed report bytes, a
wrong signer role or an old commit FAIL closed. Even a signed gate PASS is
component-specific evidence for CAP-080; global promotion is controlled
by the existing Evidence authority and current-host qualification.

Current coverage stops short of distributed single-use consumption and
cross-host federation. That must be supplied by the existing Security
Governance shared ledger / Agent Federation, not another skill authority.
Never claim these local checks prove cross-host replay protection.

## Hardware Audit

The Skill Fabric path is CPU-only and accelerator/vendor-neutral.
Existing pinned Codex 0.151.0 is currently Linux x86_64-specific;
other operating systems/architectures use their already admitted
providers instead of an undocumented fallback. GPU/NPU count is 0..N,
no automatic display-GPU compute is enabled, and this CLI test is
GUI/session-independent without imposing KDE or Wayland exclusivity.
Historical 143-capability contracts and active 175 baseline are unchanged.
