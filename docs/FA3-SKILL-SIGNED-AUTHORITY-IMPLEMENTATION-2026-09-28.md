# Skill Fabric: signed admission, selection and language claims

This is a stacked PR on top of the real native skill byte-pins PR.

**Security Governance is reused, not duplicated.** The existing
`fa3_authenticated_approval.verify_authenticated_receipt` keeps
FA3_RELEASE_ACCEPTANCE as its default grant scope. A distinct, explicit
FA3_SKILL_RUNTIME scope enables three tightly typed receipts:
SKILL_PACKAGE_ADMISSION, SKILL_TASK_SELECTION and SKILL_LANGUAGE_ADMISSION.
The existing role grant is signed by Security Governance, while the
workload identity presents a separate certificate and signs the receipt.
The existing PKI chain, URI SAN, certificate fingerprint, immutable source
commit, exact canonical payload SHA-256, signature and expiry checks apply.

`SignedSkillAuthorityVerifier` requires an independently trusted release
source commit and a pinned SHA-256 of the installed canonical skill registry.
It binds each signed payload to exact claim bytes and one task ID. No
unsigned boolean callback qualifies for non-reference SkillTaskPreflight.

The existing offline approval CLI can now issue role grants for the
FA3_SKILL_RUNTIME scope and only sign a skill receipt with a compatible
typed payload and grant. The tool never stores a private key in the repo:
issuer keys and the existing Security Governance signing key remain
externally provisioned under current host PKI/Secret Broker policy.

**Limits, not silently promoted:** repository CI uses short-lived
ephemeral self-signed test fixtures and a test Security Governance key.
It proves actual cryptographic validation of those test keys, *not*
availability or approval of a real deployed authority signer. The
existing global grant consumption ledger currently covers promotion
receipts; this PR does not claim distributed single-use skill receipt
enforcement. Cross-host execution must still pass Federation replay
protection and existing central Security Governance authorization.

The FA3 Donor & Reference Registry was queried. Existing PKI/approval,
Skill Fabric, Language Gateway and native quality-skill components are
reused. No new architectural authority/capability is created. Hardware
audit: CPU-only, vendor-neutral, accelerator count 0..N, no display GPU
AI participation, desktop/session agnostic and X11/Wayland unaffected.
