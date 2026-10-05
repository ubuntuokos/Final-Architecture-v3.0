# GitHub Actions runner-images — FA3 donor curation (2026-09-28)

**Scope:** selective, metadata-only capture of [actions/runner-images](https://github.com/actions/runner-images) into `FA3-DONOR-REFERENCE-REGISTRY-001` as `FA3-DONOR-ACTIONS-RUNNER-IMAGES-001`. **State: CANDIDATE.** This is not code approval, dependency admission, installation, provider authorization, or a current-host validation claim.

## Upstream verification

- Public official GitHub Actions image-source repository. Observed upstream default-branch revision: [`7ef9dd0112f1827264dbca2dff8b13eb9f1a5534`](https://github.com/actions/runner-images/commit/7ef9dd0112f1827264dbca2dff8b13eb9f1a5534) on 2026-09-28. This is an observation, not a promoted source pin.
- Repository-level [MIT license](https://github.com/actions/runner-images/blob/main/LICENSE). Licenses and provenance for bundled third-party tools, scripts and packages require independent review before reuse or redistribution.
- [README](https://github.com/actions/runner-images/blob/main/README.md) documents image labels, supported architectures, software inventories, weekly image releases, GA and deprecation processes.
- [Packer HCL templates](https://github.com/actions/runner-images/tree/main/images/ubuntu/templates), [Ubuntu installation scripts](https://github.com/actions/runner-images/tree/main/images/ubuntu/scripts/build), [software-report generators](https://github.com/actions/runner-images/tree/main/images/ubuntu/scripts/docs-gen) and [Pester validation tests](https://github.com/actions/runner-images/tree/main/images/ubuntu/scripts/tests) are distinct candidate reference areas.
- [Image-generation instructions](https://github.com/actions/runner-images/blob/main/docs/create-image-and-azure-resources.md) explicitly rely on Azure image creation. Their build discipline may be studied without making Azure an FA3 dependency.

## Selective FA3 applicability

| Existing FA3 area | Candidate pattern | Guardrail |
|---|---|---|
| Release Fabric | Explicit runner image revisions, GA and deprecation notices, staged release visibility | Do not automatically change hosted labels or FA3 runner configuration |
| Evidence Registry / CI | Installation checks and machine-readable software manifest generation | Hosted CI is not proof of current-host operation |
| Developer Agent | Reproducible toolchain installation and validation examples | Do not bundle unreviewed third-party tools or import source automatically |
| Hardware Audit | Reference for separating OS/architecture and software inventory from host-specific evidence | Never infer physical core count, accelerators, drivers or backend availability from a VM image |
| CI runner provisioning | Packer image-build stages as a reference implementation | No mandatory Azure, Packer, Windows or GPU dependency; preserve CPU-only and vendor-neutral paths |

As of 2026-09-28, upstream lists `ubuntu-26.04` and `ubuntu-26.04-arm` separately, while `ubuntu-latest` still denotes Ubuntu 24.04. Keep CI labels explicit where an OS migration would change evidence comparability. Upstream's published announcement targets a change of `ubuntu-latest` to 26.04 in November 2026; that date is **not** a current-host deployment instruction.

## Hardware Audit and trust boundary

The donor registry change is metadata-only; no executable code, new service, cloud subscription, dependency, global hardware prerequisite or accelerator requirement is introduced. CPU-only operation and vendor-neutral discovery remain required, with 0..N accelerators and all device placement under the FA3 Host Resource Broker. The Model Router, application inventory, donor registry, canonical release baseline and current-host evidence remain under their existing authorities.

Before any actual source copy, provisioning integration, installation or promotion: perform exact source/third-party license and provenance review; assess supply-chain risk and coexistence; compare current FA3 implementations and the central Reuse Discovery results; and run relevant isolated, CI, and current-host gates. Until then, the donor record is only discoverable research metadata.

## Review / verification limits

This curation confirms the upstream repository's declared structure and MIT license, not the security, correctness or suitability of any individual installer or all bundled packages. No Packer image was built or third-party software installed as part of the donor capture.
