# FA3 local AI model development policy

## Rule

Every FA3 application, module or feature that requires or materially benefits from a local AI model must research current suitable models and produce a model matrix before development closure. A generic platform default is not sufficient.

The recommended model is chosen from already eligible candidates using the hardware on which the application is currently running. Recommendation is advisory policy output only: Model Router remains the model/provider routing authority and the Host Resource Broker remains the CPU/GPU/NPU resource authority.

## In-application model choice

The consuming application must expose the compatible model candidates, not only the primary recommendation. The UI must distinguish recommended-on-this-hardware, installed/compatible, available-to-download, higher-quality/higher-resource, faster/lower-resource, CPU-optimized, GPU/NPU-optimized, incompatible-on-current-hardware and policy-blocked states.

A compatible alternative remains manually selectable. Hardware-aware ranking may change as the application moves between hosts or as available safe resources change, but it must never silently switch execution to another model, provider or cloud route.

## Optional model acquisition

A candidate that is not installed may be offered for download only when it is eligible for that application and platform. Download and install are explicit user actions and are mediated by Model Manager. License & Rights, provenance, integrity, model-artifact security, disk/storage preflight and all applicable admission checks remain mandatory.

Applications must not directly download model artifacts into a promoted store and must not treat visibility in the model list as admission.

## Hardware-aware recommendation

The recommendation considers CPU capability, RAM, GPU/NPU inventory, backend compatibility, available VRAM, supported precision/quantization, current safe resource pressure, Hardware Safety Envelope and Software Coexistence constraints.

CPU-only remains a mandatory path. Accelerators are vendor-neutral and 0..N.

The display GPU remains display-only by default. It may be considered automatically for AI only when there is no other GPU and no NPU and normal FA3 safety/HRB admission passes. If another GPU or NPU exists, use of the display GPU requires an explicit in-application, task-and-model-specific user selection. Hardware discovery cannot override this rule.

## Development closure

A local-AI consumer is not complete until its plan or materialization covers task-specific current model research and Reuse Discovery; a candidate model matrix with selection rationale; hardware-aware current-host recommendation; CPU-only operation; in-application visibility of compatible alternatives; optional governed acquisition for eligible non-installed candidates; Model Router and HRB bindings; no silent fallback; and retroactive impact on existing consumers.

This policy changes no capability count and introduces no architectural authority.
