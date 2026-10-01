# FA3 License & Rights retroactive audit — Phase 4

Phase 4 closes the two remaining **release-included subject** blockers:

- `FA3-PROVIDER-AGENT-RUNNER-NATIVE-001`
- `FA3-PROVIDER-AGENT-RUNNER-PODMAN-001`

This closure is limited to the FA3-native provider records, contracts and
adapter/runtime-policy implementation.

## Provenance boundary

The pinned Google AX material remains `REFERENCE_ONLY` and excluded from the
release bundle. Its canonical reference explicitly records that no upstream
source snapshot is bundled by the materialization. AX contributes architectural
patterns; FA3 implements provider-neutral workload contracts in native source.

## External runtime boundary

The Native Runner uses host-provided systemd/cgroup facilities. systemd remains
a separate external host runtime; its upstream compiled-program licensing is
recorded as LGPL-2.1-or-later and is not relicensed by FA3.

The Podman Runner uses a host-provided `podman` executable. The current pinned
upstream Podman license evidence is Apache-2.0. Podman source or binaries are
not bundled by this Agent Runner subject, and the Podman name is used only as a
nominative runtime identifier.

## Audit consequence

After the two descriptors validate, the current distribution manifest has
**zero release-included subjects without a valid LicenseRightsDescriptor**.

This does **not** close the repository-wide retroactive audit. Dependency,
donor/reference, model, dataset, font, media, SDK, codec, service and historical
file-level provenance work remains in the audit work queue. Therefore:

- `status = IN_PROGRESS_RETROACTIVE_AUDIT`
- `release_eligible = false`
- global rights promotion remains forbidden.
