# FA3 Host Bootstrap / Admission Orchestrator

`FA3-HOST-BOOTSTRAP-ADMISSION-ORCHESTRATOR-001` exposes the current-host resource-admission proof chain without creating a second resource authority.

`FA3-AUTH-HOST-RESOURCE-BROKER-001` remains the sole admission, placement, reservation and lease authority. The orchestrator may prepare typed requests and invoke privilege-separated clients, but it cannot mint or sign an admission authorization or an accelerator lease.

## Hardware Audit

The baseline is vendor-neutral and CPU-only viable. Accelerator cardinality is `0..N`. A CPU-only workload must not invoke accelerator discovery or require an accelerator lease. Accelerator discovery is performed only after the workload envelope explicitly requests an accelerator resource class.

## One-time host bootstrap

Run once for the interactive/current-host runner user:

```bash
sudo ./bin/fa3-install-host-admission-bridge.sh --user "$USER"
```

This installs three privilege-separated clients:

- generic admission authorization: `/usr/local/bin/fa3-host-resource-broker-admission`;
- accelerator lease acquire: `/usr/local/bin/fa3-host-resource-broker-acquire`;
- accelerator lease validate: `/usr/local/bin/fa3-host-resource-broker-validator`.

The admission HMAC keyring and accelerator lease HMAC key remain root-only. The runtime user gets no key read access and no generic root shell.

## Runtime selection

For any admitted workload envelope:

```bash
./bin/fa3-host-admission admit \
  --workload .fa3-current-host/input/my-workload-envelope.json
```

For CPU/memory/storage/NUMA-only workloads, the orchestrator requests a short-lived `fa3.hrb-admission-authorization.v1` bound to host, workload ID, exact workload-envelope SHA-256 and requested resource classes. That artifact is explicitly **not** a resource lease.

For accelerator workloads, the existing acquire bridge remains in force. The workload must carry an explicit accelerator requirement; the bridge requests an `AcceleratorExecutionLease@1`, and the canonical collector independently validates it. The accelerator lease may serve as the HRB admission authorization source for that accelerated execution.

`CU`/`TU` and aliases remain forbidden as admission requirements.

## Smoke and doctor

```bash
./bin/fa3-host-admission doctor
./bin/fa3-host-admission smoke
```

The default smoke is CPU-only and therefore exercises the generic HRB admission authorization path. `nvidia-smi` is not a global readiness requirement. Accelerator-specific workflows may still invoke the explicit accelerator smoke path.

## Evidence boundary

Both paths converge on `evidence/collect-resource-admission-current-host.py` and `./bin/fa3-enforce resource-admission-current-host`.

A PASS may claim only `CURRENT_HOST_RESOURCE_ADMISSION_PASS`. It does not imply provider runtime E2E or `GLOBAL_FA3_PROMOTION`. Missing bridges, expired/invalid authorization, failed lease validation, or skipped physical execution remain fail-closed.

## Self-hosted Agent Workload path

The Agent Workload Runtime workflow now creates its own exact CPU-only workload envelope for `fa3-agent-workload-native-current-host`, obtains a fresh same-run HRB admission authorization, produces a resource-admission receipt, and only then executes the native systemd/cgroup-v2 pause/resume probe.

Google AX and Podman remain separate provider subclaims; this path does not promote either one.
