# FA3 Maggi-Chen Inspector donor intake — 2026-10-03

**Authority:** owner-explicit `donornak` registration.
**Source:** https://github.com/Maggi-Chen/Inspector
**Scope:** canonical donor/reference registration only; no runtime, code, provider, model, dataset or bioinformatics-application admission.

## Upstream identity and provenance

GitHub upstream metadata identifies `Maggi-Chen/Inspector` as the non-fork repository. The related `ChongLab/Inspector` repository is a fork whose parent is `Maggi-Chen/Inspector`; it is lineage context only and is not separately admitted by this intake.

Observed upstream `master`: `2d813d96eb38adec9b8fb25388a3f4f1a2c63573` (2024-08-25). The repository declares the MIT license.

Inspector is a long-read de novo assembly evaluator. Its direct bioinformatics runtime uses Python and external scientific/bioinformatics dependencies. None of those dependencies or the Inspector runtime are admitted by this reference intake.

## FA3 reuse scope

The reusable lessons are deliberately domain-general rather than a new genomics capability:

- reference-free validation from intrinsic/source evidence;
- optional reference-backed validation;
- separation of structural and local errors;
- localized defect reporting;
- evidence/support-backed confidence;
- detect -> evidence -> repair proposal -> authorization -> correction -> revalidation;
- auditable summary/error artifacts.

These patterns strengthen existing FA3 verification and shared review/provenance designs. They do not create a new top-level capability. The canonical capability baseline remains **175**.

Future materialized use must derive capability bindings from canonical FA3 profile/contract `capability_bindings`; manual donor-name-to-CAP inference is forbidden.

## Canonical boundary

This intake registers `FA3-DONOR-MAGGI-CHEN-INSPECTOR-001` as `ACCEPTED_REFERENCE`.

It does not:

- install Inspector or its dependencies;
- copy Inspector source code;
- admit a bioinformatics runtime, model, provider, service or dataset;
- create an architectural authority;
- create a donor usage edge;
- claim Current Host PASS;
- alter the 175-capability baseline.

Existing Evidence, Human approval, Security, HRB, Model Router, Reuse Discovery and workflow authorities remain unchanged.

## Post-publication adoption rule

Registration is not adoption. A later FA3-native use of Inspector-derived patterns requires a fresh Reuse Assessment bound to a published registry snapshot containing this donor and an explicit typed usage edge in `FA3-APPLICATION-DONOR-LINKS-001`.

Any direct code/runtime use additionally requires the normal License & Rights/provenance, security, Software Coexistence, Hardware Safety, dependency and Current Host admission path.

Parent published main: `4ce349ff4089823a23563d06e5077be16554e15f`
Parent registry blob: `6ca92f89dba92910b202d51e607b68cfee0cb488`
Parent donor count: **1423**
Proposed donor count: **1424**
Capability baseline: **175**
Capability delta: **0**
Authority delta: **0**
