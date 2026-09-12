# FA3 Human Motion current-host admission

This package promotes neither GEM-X nor SOMA-X by documentation alone. It creates the executable path for a real, manually dispatched current-host E2E receipt.

## Immutable runtime inputs

The runner must already contain:

- GEM-X checkout at `32992550dba114c62243fb55e361311972dce8f9`, clean, with its pre-provisioned `.venv`.
- SOMA-X checkout at `d29dbe5a3f5a0b2632ecac91e8d5125f243a7e36`, clean, with its pre-provisioned `.venv`.
- The GEM-X SOMA checkpoint, pre-admitted and addressed by SHA-256.
- A separate NVIDIA Open Model License receipt bound to that same checkpoint SHA-256.
- All GEM/SOMA-X/SAM3D runtime assets, pre-admitted and content-addressed.
- Licensed SMPL-X model assets and an explicit SMPL-X license/asset receipt.
- An active HRB compute-role placement lease with live UUID+BDF and NUMA/locality evidence.
- A real, non-synthetic validation video with an artifact hash and a rights/consent receipt.
- Bforartists or Blender with headless USD import support.
- `bubblewrap`, `ffprobe`, `nvidia-smi`, Git and Python.

The current-host workflow performs no installation and no network download. GEM-X and SOMA-X execution runs inside a Bubblewrap network namespace with Hugging Face/Transformers offline flags.

## Mandatory hardware-conformance chain

Production Human Motion admission is fail-closed on this complete chain:

`HRB compute-role admission -> non-display GPU -> UUID+BDF live identity -> NUMA/locality evidence -> CUDA execution -> no CPU/cross-accelerator fallback`

This chain consumes the existing `FA3-AUTH-HOST-RESOURCE-BROKER-001` authority and the canonical HRB, multi-GPU, CPU/NUMA and portable-hardware contracts. It does not create a parallel placement authority.

The gate MUST NOT encode a concrete GPU SKU, VRAM size, fixed PCI BDF, fixed NUMA node or CUDA ordinal. Current-host tuples are evidence only. A future qualifying compute GPU can replace the current device without changing this contract when HRB admits it under the same canonical role and locality semantics.

### HRB receipt requirements

`human-motion-hrb-placement.json` uses `fa3.hrb-placement-receipt.v1` and must contain at least:

```json
{
  "schema": "fa3.hrb-placement-receipt.v1",
  "authority_id": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
  "status": "ACTIVE",
  "lease_id": "<opaque lease id>",
  "expires_at": "<future RFC3339 timestamp>",
  "placement_source": "LIVE_TOPOLOGY",
  "device_uuid": "<live GPU UUID>",
  "pci_bdf": "<live PCI BDF>",
  "static_runtime_ordinal_as_identity": false,
  "accelerator_role": "COMPUTE",
  "compute_eligible": true,
  "display_role": false,
  "topology_revalidated_at_admission": true,
  "cpu_memory_accelerator_one_placement": true,
  "accelerator_numa_node": 0,
  "compute_cpu_set": "0-7,36-43",
  "memory_numa_nodes": [0],
  "locality_mode": "NUMA_LOCAL"
}
```

The numeric values above are examples only. The collector resolves the GPU's NUMA node from live PCI sysfs, verifies the HRB CPU set is contained in that node's live CPU list, and requires the memory node to match. On a multi-NUMA-node host, unknown GPU NUMA locality fails closed. On a single-NUMA-node host, `SINGLE_NUMA_HOST` is also accepted when live topology proves it.

The selected GPU must also report no active display through `nvidia-smi`. This prevents a display/UI accelerator from satisfying the Human Motion compute admission even if it is otherwise CUDA-capable.

## Other receipt contracts

`gem-x-checkpoint-admission.json`:

```json
{"schema":"fa3.model-artifact-admission-receipt.v1","admitted":true,"artifact_sha256":"<64 hex>","malware_security_admission":"PASS"}
```

`gem-x-model-license.json`:

```json
{"schema":"fa3.model-license-receipt.v1","license_name":"NVIDIA Open Model License Agreement","accepted":true,"artifact_sha256":"<same checkpoint SHA-256>"}
```

`human-motion-runtime-assets-admission.json` contains the admitted GEM/SOMA-X/SAM3D paths and their content hashes. `smplx-license.json` binds accepted SMPL-X assets to their tree hash. `human-motion-video-admission.json` binds the real validation video to its SHA-256 and rights/consent confirmation.

## E2E evidence

A successful run must prove all of the following in the same current-host receipt:

1. exact clean GEM-X and SOMA-X source revisions;
2. checkpoint/model/third-party license and artifact admission;
3. HRB compute-role admission on a non-display accelerator;
4. live UUID+BDF identity and non-authoritative runtime ordinal;
5. live CPU/memory/accelerator NUMA-local placement evidence;
6. exactly one HRB-scoped visible CUDA accelerator and actual CUDA execution;
7. no CPU or cross-accelerator fallback;
8. real video -> GEM-X 77-joint 2D/3D motion;
9. finite world-space output, frame/timestamp consistency and a non-identity dynamic-camera trajectory;
10. motion-continuity, foot-sliding and hand-jitter metrics;
11. provider-neutral/SOMA-X-compatible 77-joint NPZ projection;
12. SOMA-X pose transfer to licensed SMPL-X;
13. USD export;
14. headless Bforartists or Blender USD import.

The output receipt is `evidence/receipts/human-motion-current-host.json`. `./bin/fa3-enforce human-motion-current-host` rejects a missing, synthetic, hosted-CI-only, non-compute-role, display-attached, identity-mismatched, NUMA-incoherent, stale-HRB, license-mismatched, non-CUDA, fallback, non-finite, non-dynamic-camera, incomplete-interchange or failed-DCC receipt.

## Running

The real E2E is intentionally manual:

1. prepare the runner-local inputs above;
2. open **Actions -> FA3 Human Motion Current-Host E2E -> Run workflow**;
3. set `execute_current_host=true`;
4. keep the defaults or provide the corresponding runner-local paths.

A hosted PR regression validates the contracts and negative hardware cases and explicitly proves that a missing real receipt fails closed. It is not production runtime evidence.
