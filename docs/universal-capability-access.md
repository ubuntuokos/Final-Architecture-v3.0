# FA3 Universal Capability Access

Universal Capability Access is a P0, fail-closed donor and License & Rights rule applying retroactively to every current donor/reference record and prospectively to every future record. It creates no new capability or top-level authority; the capability baseline remains **175**.

No user-facing FA3 capability may depend exclusively on a third-party component whose terms exclude users by geography, territory, jurisdiction, noncommercial/research-only conditions, mandatory cloud/account access, platform exclusivity or hardware exclusivity. Restricted sources may remain references, but cannot be the sole material implementation path. Every user-facing capability retains at least one independently usable, rights-cleared global FA3-native or compatible path.

FA3 must not use VPNs, proxies, foreign hosting, artifact relocation, account indirection or equivalent techniques to evade upstream restrictions. The solution is capability substitution or an independent implementation.

The executable gate classifies every current donor at runtime as GLOBAL_DIRECT_REUSE, GLOBAL_CONDITIONAL_REUSE, RESTRICTED_REFERENCE, DISCOVERY_INDEX, or UNVERIFIED_REFERENCE_ONLY. Classification is an engineering admission input, not legal clearance; unknown facts fail closed for material use.

CODE_REUSE, RUNTIME_DEPENDENCY, or explicit imported-code/runtime/provider/model admission is material use. Restricted material use requires OPTIONAL_RESTRICTED_WITH_GLOBAL_SUBSTITUTE, global_substitute_refs, rights_evidence_refs, and explicit no-circumvention. Discovery indexes and unverified sources cannot be material dependencies.

The globally usable path preserves CPU-only viability, 0..N accelerators through HRB, no mandatory commercial account or cloud, and no silent provider/model/device/cloud fallback. Optional providers may coexist in the Engine/Provider Selector without removing the universal path.

Substitution order: existing globally usable donor; independently rights-cleared donor combination; FA3-native implementation from global components; clean-room FA3-native implementation; new owner-marked donor through normal admission. Restricted source code, weights, datasets and prohibited training outputs are not provided to clean-room implementation; independent provenance and separate patent/IP review are required.

This static gate does not claim provider/model/runtime admission or physical Current Host PASS.
