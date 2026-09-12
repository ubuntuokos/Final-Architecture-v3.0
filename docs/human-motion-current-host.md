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
- An active HRB placement lease resolving to one live accelerator by UUID + PCI BDF.
- A real, non-synthetic validation video with an artifact hash and a rights/consent receipt.
- Bforartists or Blender with headless USD import support.
- `bubblewrap`, `ffprobe`, `nvidia-smi`, Git and Python.

The current-host workflow performs no installation and no network download. GEM-X and SOMA-X execution runs inside a Bubblewrap network namespace with Hugging Face/Transformers offline flags.

## Receipt contracts

`gem-x-checkpoint-admission.json`:

```json
{"schema":"fa3.model-artifact-admission-receipt.v1","admitted":true,"artifact_sha256":"<64 hex>","malware_security_admission":"PASS"}
```

`gem-x-model-license.json`:

```json
{"schema":"fa3.model-license-receipt.v1","license_name":"NVIDIA Open Model License Agreement","accepted":true,"artifact_sha256":"<same checkpoint SHA-256>"}
```

`human-motion-runtime-assets-admission.json`:

```json
{
  "schema":"fa3.human-motion-runtime-assets-admission.v1",
  "admitted":true,
  "all_third_party_assets_admitted":true,
  "gem_soma_assets_path":"/absolute/path/to/GEM-X/inputs/soma_assets",
  "gem_soma_assets_tree_sha256":"<64 hex>",
  "soma_x_data_root":"/absolute/path/to/SOMA-X/assets",
  "soma_x_data_root_sha256":"<64 hex>",
  "sam3d_ckpt_path":"/absolute/path/to/sam3d.ckpt",
  "sam3d_ckpt_sha256":"<64 hex>",
  "sam3d_mhr_path":"/absolute/path/to/mhr/model-or-asset",
  "sam3d_mhr_sha256":"<64 hex>"
}
```

`smplx-license.json`:

```json
{"schema":"fa3.smplx-license-asset-receipt.v1","accepted":true,"model_assets_present":true,"data_root":"/same/absolute/path/as/soma_x_data_root","asset_sha256":"<tree SHA-256>"}
```

`human-motion-video-admission.json`:

```json
{"schema":"fa3.media-input-admission-receipt.v1","artifact_sha256":"<video SHA-256>","synthetic":false,"rights_or_consent_confirmed":true}
```

The HRB receipt uses the existing `fa3.hrb-placement-receipt.v1` contract and must be `ADMITTED` or `ACTIVE`, have a non-expired lease, `placement_source=LIVE_TOPOLOGY`, `static_runtime_ordinal_as_identity=false`, and UUID/BDF that resolve to exactly one live NVIDIA device.

## E2E evidence

A successful run must prove all of the following in the same current-host receipt:

1. exact clean GEM-X and SOMA-X source revisions;
2. checkpoint/model/third-party license and artifact admission;
3. live HRB accelerator identity and CUDA-only execution with no silent CPU fallback;
4. real video → GEM-X 77-joint 2D/3D motion;
5. finite world-space output, frame/timestamp consistency and a non-identity dynamic-camera trajectory;
6. motion-continuity, foot-sliding and hand-jitter metrics;
7. provider-neutral/SOMA-X-compatible 77-joint NPZ projection;
8. SOMA-X pose transfer to licensed SMPL-X;
9. USD export;
10. headless Bforartists or Blender USD import.

The output receipt is `evidence/receipts/human-motion-current-host.json`. `./bin/fa3-enforce human-motion-current-host` rejects a missing, synthetic, hosted-CI-only, stale-HRB, license-mismatched, fallback, non-finite, non-dynamic-camera, incomplete-interchange or failed-DCC receipt.

## Running

The real E2E is intentionally manual:

1. prepare the runner-local inputs above;
2. open **Actions → FA3 Human Motion Current-Host E2E → Run workflow**;
3. set `execute_current_host=true`;
4. keep the defaults or provide the corresponding runner-local paths.

A hosted PR regression validates the contracts and explicitly proves that a missing real receipt fails closed. It is not production runtime evidence.
