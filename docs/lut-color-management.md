# LUT and color-transform governance

`FA3-LUT-COLOR-001` makes LUT registration and color-transform ordering a mandatory provider-neutral projection over existing `CAP-121` and `CAP-126`. It creates no capability and no architectural authority.

The canonical order is input discovery, technical input transform, primary correction, optional creative LUT, output transform, and export validation. A non-Log source still records an explicit identity technical transform. Unknown input/output color spaces, duplicate LUT hashes, more than one active creative LUT, creative-before-technical ordering, runtime download, executable payloads, floating sources, missing licenses and unpinned artifacts fail closed.

The LUT artifact registry is governed by `FA3-REGISTRY-001`; provider-local folders are projections only. Each `.cube`, `.3dl`, `.dat`, `.m3d` LUT or pinned OCIO configuration requires immutable source identity, exact SHA-256, byte size, license, classification, input/output color spaces, interpolation, domain metadata, parser validation and a non-finite-value scan.

Kdenlive remains the human finishing and picture-lock surface. Its native LUT route is a typed, capability-discovered MLT/FFmpeg-avfilter effect projection. FFmpeg is the deterministic headless route. OpenFX remains optional and external-host-only: it renders a hash-addressed intermediate that is validated and relinked to Kdenlive; Kdenlive is not claimed as a native OpenFX host.

Every project mutation requires preview/dry-run semantics, pre/post effect-stack digests and human approval at picture lock. Every render receipt preserves color/pixel/range/HDR metadata, LUT and pipeline hashes, provider/host versions, QC results and rollback identity. Static CI PASS does not promote runtime; current-host Kdenlive/FFmpeg/OpenFX color E2E evidence remains separate.

Run the static gate with:

```bash
./bin/fa3-enforce lut-color
```

Run the readiness collector on the real workstation with:

```bash
PYTHONPATH=src python3 evidence/collect-lut-color-current-host.py --root .
```
