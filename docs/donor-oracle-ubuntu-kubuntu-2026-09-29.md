# Oracle, Oracle Developer Relations, Ubuntu and Kubuntu donor curation (2026-09-29)

This is a metadata-only extension to the **existing** `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`, not an upstream-admission decision or new donor authority. **Five submitted URLs** (four organization discovery indexes and one Python-filtered topic discovery index) and **eight separately verified upstream repositories** are recorded as 13 source-unique `CANDIDATE` entries. Registry snapshot: **592 → 605** on this branch's pinned base; the 175-capability baseline is unchanged. Concurrent donor PRs must be reconciled by normalized source key, not by the branch-local count.

## Submitted sources

| Source | Type | Potential FA3 relevance |
| --- | --- | --- |
| [oracle](https://github.com/oracle) | Official organization index | GraalVM build/compiler references; OpenGrok code indexing |
| [oracle-devrel](https://github.com/oracle-devrel) | Developer Relations organization index | Infrastructure guides, Linux/virtualization laboratory patterns |
| [ubuntu](https://github.com/ubuntu) | Ubuntu organization index | App catalog UX, developer tooling/provisioning patterns |
| [kubuntu-team](https://github.com/kubuntu-team) | Kubuntu Team organization index | Desktop QA workflow and multilingual user documentation |
| [kubuntu topic, Python filter](https://github.com/topics/kubuntu?l=python) | Dynamic GitHub topic discovery query | Candidate discovery only, not verified membership or a fixed package |

The topic is normalized to `github:topics/kubuntu`; the supplied `?l=python` filter is retained in `discovery_filter.observed_url`. The filtered result membership and count were **not validated**; no individual topic results have been admitted.

## Eight separately verified concrete source repositories

Repository existence and readme purpose were checked against GitHub on 2026-09-29; license mentions below are *README observations*, not legal clearance or exact revision audits.

| Source | Selective reference reuse | Observed license / blocking issue |
| --- | --- | --- |
| [oracle/graal](https://github.com/oracle/graal) | Optional AOT and compiler/build patterns, never mandatory Java/GraalVM runtime | Multi-component license/version audit pending |
| [oracle/opengrok](https://github.com/oracle/opengrok) | Code cross-reference and search design within existing Knowledge/Reuse Discovery | README CDDL-1.0 badge; dependency/coexistence audit pending |
| [oracle-devrel/technology-engineering](https://github.com/oracle-devrel/technology-engineering) | Architecture examples and infrastructure research, per asset | Large heterogeneous asset collection; license per asset required |
| [oracle-devrel/linux-virt-labs](https://github.com/oracle-devrel/linux-virt-labs) | Bounded Linux VM/lab testing workflows | README UPL-1.0; OCI/Ansible are not FA3 dependencies |
| [ubuntu/app-center](https://github.com/ubuntu/app-center) | Catalog search, listing and provisioning UX patterns in the **existing Qt6 FA3 Application Fabric** | README GPL-3.0; Flutter app must not replace FA3-native shell |
| [ubuntu/ubuntu-make](https://github.com/ubuntu/ubuntu-make) | Developer provisioning workflow and package-manager instruction patterns | Exact license pending; no mandatory Snap/PPA or privileged installs |
| [kubuntu-team/KubuQA](https://github.com/kubuntu-team/KubuQA) | ISO/VM installer test workflow and test-case UX | Exact license pending; upstream kdialog/VirtualBox/pkexec/install actions **not** authorized |
| [kubuntu-team/kubuntu-manual](https://github.com/kubuntu-team/kubuntu-manual) | Sphinx documentation/localization patterns | README CC-BY-SA-4.0; no verbatim content reuse pending rights audit |

## FA3 integration constraints

- Existing central Donor & Reference Registry, Reuse Discovery, Application Fabric, installer and test/evidence authorities remain unique. No new parallel provider, package manager, documentation or code indexing authority.
- FA3 remains **generic Linux** with CPU-only capability, Qt6/Wayland-first GUI and X11 fallback. Kubuntu/Ubuntu-specific dependencies may be documented as optional distro adaptations, never global requirements.
- Hardware Safety Envelope and Software Coexistence are fail-closed. No unrequested root access, apt/snap, privilege escalation, VM installation, sysctl/kernel tuning, changes to ports/paths/services, or upstream uninstall.
- No cloud/OCI dependency; no forced GraalVM/Java runtime; no automatic donor code copy, fetch, activation, model/provider admission or physical current-host PASS.
- Any code or content adoption requires exact upstream revision and license/IP check, provenance/SBOM, security, host coexistence, dependency, Reuse Discovery and appropriate physical current-host/evidence gates. License declarations here are *not* completed assessments.
- For subsequent registry merges, reconcile same normalized source keys against current main and every overlapping open donor PR; retain earlier candidates and historical evidence. Branch-local **605** is not an overall post-merge count.

## Verification boundary

Static branch metadata assertions: 13 source keys, 13 unique IDs, all new candidates non-authoritative with nine automatic action/authority flags false, registry count consistent, capability baseline 175. The Python topic query is not individually curated, end-to-end repository CI and actual host-runtime tests remain separate.
