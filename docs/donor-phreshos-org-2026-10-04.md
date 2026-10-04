# FA3 PhreshOS GitHub organization donor intake — 2026-10-04

## Owner marker

The owner explicitly requested the exact source `https://github.com/PhreshOS` to be added among FA3 donors on 2026-10-04.

## Source classification

- canonical source key: `github:phreshos`
- donor id: `FA3-DONOR-PHRESHOS-ORG-001`
- source kind: `GITHUB_ORGANIZATION`
- status: `ACCEPTED_REFERENCE`
- mode: metadata-only `DISCOVERY_INDEX`
- observed public child repositories during intake scan: **21**
- capability delta: **0**
- authority delta: **0**
- capability baseline: **175**
- runtime impact: **NO_RUNTIME_IMPACT**

Organization-level registration is a discovery index only. It does not recursively admit repositories, source code, packages, services, providers, runtimes or UI implementations.

## High-value FA3 discovery areas

The current organization portfolio exposes strong reference material for:

- canonical environment-neutral Core contracts and shared domain objects;
- System authority separated from Client, Server and external Node adapters;
- Program / Process / Endpoint / Service / Context lifecycle modeling;
- inter-program communication without application-owned transports;
- centralized permission and storage boundaries;
- one authoritative runtime state exposed consistently to GUI, CLI, SDK and agents;
- machine-discoverable CLI/operation contracts suitable for automation;
- runtime-neutral React adaptation separated from visual components;
- shared Appearance and accessible UI component contracts;
- verified program packaging, clean-machine bootstrap, first-run provisioning and settings workflows.

Representative observed repositories include `system`, `core`, `client`, `server`, `node`, `cli`, `react`, `react-ui`, `install`, `settings-program` and `sprout-program`.

## FA3 architectural boundary

PhreshOS is a reference for patterns, not a replacement runtime. In particular:

- no second FA3 System/runtime authority is created;
- existing Security, UAF/MCP Gateway, Temporal, HRB, Model Router, Evidence and License & Rights authorities remain unchanged;
- human UI actions and agent/CLI actions may be studied as projections over one canonical operation contract, but any FA3 materialization must use FA3-native authority and permission boundaries;
- the upstream Node/Bun/web stack does not become a mandatory FA3 dependency;
- FA3 CPU-only viability, Hardware Safety, Software Coexistence and display-GPU rules remain mandatory;
- the PhreshOS visual style is not imported; only reusable UI architecture/accessibility patterns may be considered under the FA3 GUI rules.

## License and reuse boundary

The organization index has no single project license. Several reviewed core repositories currently declare MIT, but every child repository and every exact revision selected for material reuse must be reviewed independently.

No code is copied and no package is installed. No provider, model, runtime, dependency, service or child repository is admitted. No usage edge is created by this intake.

Repository-level material adoption requires exact provenance, License & Rights clearance, security review, Software Coexistence review, dependency/runtime review, capability/layer placement, canonical typed usage-edge registration and Current Host requalification if runtime behavior is affected.

The fixed FA3 capability baseline remains **175**.

## Rolling intake state

At creation time four earlier canonical donor-intake PRs are open (#651, #657, #663, #664), so this one-source PhreshOS intake occupies the fifth active slot. Finalization ordering is ascending donor-mutation workload and FIFO for equal workloads; therefore the earlier one-source #664 intake must finalize before this intake.
