# FA3 Binary & Software Analysis Fabric — canonical foundation

The reviewed donor is `P4nda0s/reverse-skills` pinned to `a2baa31c58a3567977188414da68c8c842057152`. It is recorded as `REFERENCE_ONLY`; no upstream code, skill body or bundled executable is runtime-admitted by this foundation.

The donor contributes patterns for symbol recovery, structure recovery, dynamic instrumentation, function-scoped emulation, IDA/IDALib automation and IL2CPP analysis. FA3 re-expresses these as provider-neutral contracts. The canonical IR therefore does not require IDA, Ghidra, Rizin/radare2, Binary Ninja or another specific backend.

The upstream README states MIT, but the reviewed repository root did not expose a LICENSE file. Redistribution therefore remains fail-closed. The bundled `skills/rev-dex-dumper/panda-dex-dumper` executable is blocked pending separate provenance, license, source/build correspondence, security and digest-bound admission.

Binary strings, symbols, decompiler comments, resources and metadata are untrusted data. They cannot become system instructions or grant tool/model/secret/execution authority.

## Hardware Audit

The foundation is vendor-neutral and CPU-only viable. Accelerators are optional with cardinality 0..N. Execution resources remain HRB-governed.

## Runtime status

Static/canonical admission does not promote any analysis provider or current-host runtime.
