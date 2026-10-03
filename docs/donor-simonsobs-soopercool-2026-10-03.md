# FA3 simonsobs/SOOPERCOOL donor intake — 2026-10-03

**Authority:** owner-explicit `donornak` registration.  
**Source:** https://github.com/simonsobs/SOOPERCOOL  
**Scope:** canonical donor/reference registration plus applicability analysis; no code, runtime, dependency, provider, model or dataset admission.

## Upstream identity

SOOPERCOOL is the Simons Observatory map-to-C_ell analysis pipeline for SAT B-mode work. The observed upstream head during intake is `6191a79688392e1d57982c7697c54e110b32f49f` (2026-10-02).

The repository is public, but GitHub metadata exposes no license and no root `LICENSE` file was observed. Therefore direct source copying, redistribution, dependency adoption and runtime integration are fail-closed until an exact License & Rights/provenance review clears the relevant material.

## Selective FA3 reuse

The valuable content is domain-general rather than astronomy-specific:

- configuration-driven multi-stage scientific pipelines;
- dataset/map-set metadata and bundle management;
- masks, weights and region-of-interest processing patterns;
- FFT / spectral / Fourier-space filtering;
- transfer-function calibration and correction;
- analytic covariance and empirical simulation-derived covariance;
- Monte-Carlo / synthetic-data validation;
- batch-parallel and MPI/HPC execution organization;
- structured result packaging and reproducible run configuration.

The astronomy/CMB estimator itself is not proposed as an FA3 baseline capability.

## Intended FA3 placement

Patterns may strengthen existing shared layers and consumers:

- Shared Scientific / Signal Processing;
- Simulation & Validation;
- Verification / Evidence;
- Orchestration & Workflow Fabric;
- Host Resource Broker / execution planning;
- Audio, Speech and Music processing;
- Image, Video and VFX processing;
- Sensor / Measurement Analytics.

Temporal remains the sole global durable workflow authority. HRB remains the sole host resource/device-placement authority. Upstream `srun`/MPI conventions are reference patterns only and must be abstracted behind FA3 execution backends rather than becoming mandatory infrastructure.

## Admission boundary

This intake registers `FA3-DONOR-SIMONSOBS-SOOPERCOOL-001` as `ACCEPTED_REFERENCE`.

It does not install or admit SOOPERCOOL, NumPy/SciPy/healpy/NaMaster/SACC/CAMB/pixell/scikit-learn, MPI, SLURM, astronomy datasets, models or services. It creates no usage edge, provider, application, capability or architectural authority.

Any later material adoption requires a fresh Reuse Assessment bound to a published registry snapshot containing this donor, then an explicit typed donor usage edge. Direct code/runtime use additionally requires License & Rights/provenance, security/supply-chain, Software Coexistence, Hardware Safety and Current Host review.

Parent published main: `fd8adf5ab2ef12882c47250ecb5d5f22ff8e796b`  
Parent registry blob: `6ca92f89dba92910b202d51e607b68cfee0cb488`  
Parent donor count: **1423**  
Proposed donor count: **1424**  
Capability baseline: **175**  
Capability delta: **0**  
Authority delta: **0**
