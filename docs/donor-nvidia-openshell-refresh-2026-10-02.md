# FA3 NVIDIA OpenShell donor refresh — 2026-10-02

This is an **in-place refresh of an existing canonical donor identity**, not a new donor intake.

- donor ID: `FA3-DONOR-NVIDIA-OPENSHELL-001`
- source: https://github.com/NVIDIA/OpenShell
- normalized key: `github:nvidia/openshell`
- registry count: **1354 → 1354**
- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**

## Verified upstream snapshot

The stable reference remains **v0.1.2**, resolved to commit
`6648bd0c290efbc41ba131ee9831ee45cd431f94`.

At refresh time upstream `main` was observed at
`ec49209da25be39840742df29b64ec694d159c2f`, **71 commits ahead** of v0.1.2.

The development head is retained only as a discovery/reference snapshot. It is
not an FA3 runtime baseline and does not authorize installing or activating
OpenShell.

## Selected FA3 planning value

The refresh records OpenShell as a reference for:

- policy proving and policy-boundary containment;
- executable identity and digest binding;
- deny-by-default filesystem/process/network enforcement;
- endpoint-bound credential projection;
- MCP L7 request inspection and protocol-aware denial;
- sandbox lifecycle and fail-closed loss/reconnect handling;
- structured security events;
- Docker/Podman/Kubernetes/VM-style isolation adapter patterns.

## Authority boundary

This refresh does **not** admit an OpenShell control plane, gateway, scheduler,
provider/model router, secret authority, host-resource authority, evidence
authority, automatic dependency or runtime.

The intended later FA3 use is selective pattern adoption under existing
Security Governance, Testőr/Layer Guard, UAF, Central MCP Gateway, Secret
Broker, HRB, Model Router, Evidence and Temporal boundaries.

Any actual adoption requires a fresh published-main-bound Reuse Assessment and
an explicit canonical donor usage edge. Any OpenShell runtime/backend use would
require separate License & Rights, dependency/supply-chain, Security, Software
Coexistence, Hardware Safety and physical Current Host admission.

Parent published main:
`44ebf7444485aeb29db1a4677e7d485fee83fae3`

Parent donor registry blob:
`804786e96c66ef6c4397b1471e52a6594473bb20`

Parent/proposed donor count: **1354 / 1354**
