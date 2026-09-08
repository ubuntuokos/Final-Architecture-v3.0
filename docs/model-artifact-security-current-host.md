# FA3 current-host Model Artifact Security Runtime

This runtime materializes `FA3-MODEL-ARTIFACT-SECURITY-001` beside the Model Manager. It is an evidence-producing security sensor stack, not a new FA3 authority.

## Runtime root

Default: `/ai-cache/fa3/model-security`. The production root must be outside the user's home directory so the scan sandbox can mask `$HOME` completely.

## Bootstrap

```bash
export FA3_MODEL_SECURITY_HOME=/ai-cache/fa3/model-security
export FA3_MODEL_SECURITY_ALLOW_NETWORK_BOOTSTRAP=1
# Only if ClamAV/YARA/bubblewrap/curl are missing and operator explicitly permits sudo:
export FA3_MODEL_SECURITY_ALLOW_SUDO=1
bash bin/fa3-model-artifact-security-bootstrap.sh
```

Bootstrap/update may access the network to install pinned tools and refresh scanner databases. Scan execution never may. ModelAudit telemetry is disabled.

## Production E2E

```bash
export FA3_MODEL_SECURITY_HOME=/ai-cache/fa3/model-security
export FA3_MODEL_SECURITY_ALLOW_NETWORK_BOOTSTRAP=0
# Optional deterministic selection of a real local model:
export FA3_MODEL_SECURITY_E2E_TARGET=/path/to/existing/model.safetensors
# Required for explicit/custom targets unless the file is from the known Stability Matrix media store:
export FA3_MODEL_SECURITY_E2E_MODEL_CLASS=DIFFUSION
bash bin/fa3-model-artifact-security-current-host.sh
```

Without `FA3_MODEL_SECURITY_E2E_TARGET`, the collector searches only the known Stability Matrix media-model stores and selects a real regular `.safetensors` or `.gguf` artifact. This avoids silently classifying an unknown Hugging Face/LM Studio artifact as non-generative. For an explicit/custom target, `FA3_MODEL_SECURITY_E2E_MODEL_CLASS` is required unless the target resides under the known Stability Matrix store. A synthetic target can never satisfy production E2E.

The current-host proof includes: all eleven scanner identities and digests, ClamAV and Trivy database presence, real-model quarantine/hash/static scan, bubblewrap isolated first-load, Model Manager hash-bound `SECURITY_ADMITTED` hook, and a controlled malicious Pickle negative regression that is scanned but never unpickled or executed.

Generative LLM behavior admission and upstream signature verification remain fail-closed when applicable unless an explicit local garak generator profile or offline Cosign verification material is supplied. The runtime never silently falls back to remote scanning.
