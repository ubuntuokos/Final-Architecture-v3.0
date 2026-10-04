# SCALE CUDA compatibility backend — 2026-10-04

## Placement

SCALE is integrated as the optional shared provider **FA3-PROVIDER-SCALE-CUDA-COMPAT-001**. It is not a capability, does not change the 175 capability baseline, and does not create a new placement, routing, security or evidence authority.

The backend name is `scale-cuda` and its FA3 execution class is `translation`. Applications do not embed SCALE-specific functional cores; they consume the shared execution contract.

## AMD path

FA3 performs read-only SCALE discovery with `scaleinfo`. A SCALE target is bound to an AMD accelerator only when SCALE reports the exact PCI BDF already discovered by FA3. The reported `gfx...` target is retained as evidence.

Detection does not imply admission. For commercial-context execution, a fail-closed License & Rights receipt is required. The receipt stores only an opaque entitlement reference; raw license secrets are forbidden.

The workload must explicitly allow translation and request/permit the `scale-cuda` path. HRB must still issue the accelerator lease. No silent substitution to SCALE, CUDA, ROCm, cloud or another device is permitted.

## NVIDIA and Intel

SCALE upstream supports NVIDIA compilation, but FA3 does not replace its native NVIDIA CUDA path with SCALE by default. The SCALE integration in this change is the AMD CUDA-compatibility path.

SCALE is not claimed as an Intel backend. Intel CUDA-oriented workloads continue to use the separately governed Intel cross-vendor execution paths.

## Installation and host mutation

FA3 does not install SCALE, activate `scaleenv`, edit `PATH`, install drivers, alter kernel modules or modify the host package manager as part of this provider. An administrator/user supplies the external runtime separately.

The current SCALE Free License observed on 2026-10-04 is non-commercial-only. Therefore commercial FA3/CFA3 execution requires a separately admitted entitlement. This repository change does not bundle or redistribute SCALE.

## Promotion state

The implementation is present, but runtime promotion is not claimed. Physical Current Host or target-host qualification is required for the SCALE path before promotion. Historical or simulated PASS is not accepted.
