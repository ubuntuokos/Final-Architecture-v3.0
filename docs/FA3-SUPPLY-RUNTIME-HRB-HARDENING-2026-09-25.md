# FA3 Supply-chain / Provider Runtime / HRB hardening

This package materializes the 2026-09-25 hardening decision without adding capabilities or architectural authorities.

## Hardware Audit

- vendor-neutral baseline is preserved;
- CPU-only execution remains valid;
- accelerator cardinality is 0..N;
- accelerator identity is stable provider/device identity, never a fixed runtime ordinal;
- HRB remains the only host resource admission/reservation/lease authority.

## Supply-chain admission

`tools/fa3_supply_chain_scan.py` consumes already installed local Syft, Grype and ScanCode binaries. It intentionally does not download tools at runtime. The generated `SoftwareSupplyChainReceipt@1` records source/artifact identity, dependency lock, SBOM digest, scanner identities/versions, detected licenses, vulnerability findings and build provenance. Required unknowns fail closed.

## Provider runtimes

`FA3-PROVIDER-RUNTIME-001` supports VENV, OCI and explicitly justified HOST_NATIVE execution. VENV is preferred when reproducible. Native ABI/C++/accelerator-heavy providers may use rootless Podman with digest-pinned images. Conda/Mamba is not an FA3 baseline.

## HRB composite reservation

`ResourceReservationPlan@1`, `LeaseGroup@1`, `DerivedExecutionLease@1` and `LeaseLineageReceipt@1` extend the existing HRB authority. Composite admission is atomic and forbids hold-and-wait. Child leases are strict subsets of active parents and can only be created by HRB; revocation cascades from parent to children.

## Controlled upstream patching

The allowed dispositions are DIRECT_PINNED, REFERENCE_ONLY, PATCHED_VENDOR, FA3_NATIVE_REIMPLEMENTATION and REJECTED. PATCHED_VENDOR requires immutable upstream/patched identities, patch-series and tree digests, dependency-lock identity, security disposition, SCS admission and review expiry. A security patch never converts unresolved license incompatibility into distribution admission.

## Hungarian AQC

The existing FA3-HU-AQC-001 architecture and current-host collector remain authoritative. No document-only closure is claimed. Promotion still requires real hu-HU current-host evidence using admitted scorers and the canonical thresholds.
