# FA3 Host Bootstrap / Admission Orchestrator

`FA3-HOST-BOOTSTRAP-ADMISSION-ORCHESTRATOR-001` converts the current-host resource-admission proof chain into a product-facing flow without creating a second resource authority.

The Host Resource Broker remains the sole authority for lease issuance, accelerator placement, memory budget, validity, and conflict resolution. The orchestrator only validates workload input, discovers a candidate accelerator as a request hint, delegates lease acquisition through the root-separated HRB bridge, executes the existing current-host collector and gate, and emits a scoped report.

## One-time host bootstrap

Run once for the interactive/current-host runner user:

```bash
sudo ./bin/fa3-install-host-admission-bridge.sh --user "$USER"
```

This installs both privilege-separated bridges:

- validate-only client: `/usr/local/bin/fa3-host-resource-broker-validator`
- acquire client: `/usr/local/bin/fa3-host-resource-broker-acquire`

The authoritative HRB binary and its HMAC key remain root-owned. The runtime user receives no HMAC-key read permission and no direct generic root shell. The acquire bridge accepts only a typed, caller-owned request and delegates explicit `issue-lease` / `validate-lease` operations to the existing HRB.

## Normal runtime UX

Check readiness:

```bash
./bin/fa3-host-admission doctor
```

Run the fixed current-host admission smoke without manually issuing a lease:

```bash
./bin/fa3-host-admission smoke
```

Admit a provider/application workload envelope:

```bash
./bin/fa3-host-admission admit \
  --workload .fa3-current-host/input/my-workload-envelope.json
```

The custom workload must use schema `fa3.workload-resource-envelope.v1`, contain a non-empty `workload_id`, and include an explicit `gpu.vram_gib >= N` requirement when an accelerator lease is required. `CU`/`TU` and aliases remain forbidden as production admission requirements.

## Execution boundary

The orchestrator discovers NVIDIA UUID/BDF, physical VRAM and CUDA compute capability only to select a candidate for the lease request. It does not authorize that candidate. The real lease returned by `FA3-HOST-RESOURCE-BROKER-001` is still revalidated by the existing root-separated validator and the canonical `resource-admission-current-host` collector/gate.

A PASS from this surface may claim only `CURRENT_HOST_RESOURCE_ADMISSION_PASS`. It does not claim `GLOBAL_FA3_PROMOTION` or provider runtime E2E. Global promotion still requires the independent Evidence Registry and all 19 acceptance criteria.

## Self-hosted runner

`bin/fa3-current-host-runner-bootstrap.sh` installs both bridges if needed and writes the fixed `FA3_HRB_ACQUIRE_COMMAND` adapter into the runner's systemd user unit. Existing current-host resource-admission smoke workflows therefore acquire a fresh HRB lease automatically instead of requiring a dispatch-time raw lease path.

`bin/fa3-current-host-runner-doctor` fails closed unless both validation and acquire bridges are available non-interactively while the runner remains non-root.

## Failure semantics

- exit `0`: scoped PASS from the existing canonical proof chain
- exit `2`: BLOCKED/PENDING, including missing bridge, denied lease, insufficient resources, invalid/stale lease, or failed admission
- exit `3`: implementation/input error

No missing bridge, skipped production job, hosted-CI test, or documentation state is promoted to current-host PASS.
