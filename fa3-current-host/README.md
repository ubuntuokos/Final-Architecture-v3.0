# FA3 Current Host

\`fa3-current-host\` is the executable current-host runtime and evidence projection for FINAL ARCHITECTURE v3.0.

It is **not** a new canonical profile, capability, provider authority, or architectural authority. Canonical identity and policy remain in \`canonical/\` under \`FA3-REGISTRY-001\`; this directory only coordinates current-host collection, validation, admission evidence, and fail-closed promotion checks.

## Invariants

- canonical capability count: **143**
- new capabilities: **0**
- new architectural authorities: **0**
- document-only promotion: **forbidden**
- automatic promotion: **disabled**
- secret collection: **prohibited**
- Linux Recovery/Rebuild projection: **out of scope**
- raw current-host state: stored under \`/.fa3-current-host/\` and ignored by Git

## Commands

\`\`\`bash
./bin/fa3-current-host verify
./bin/fa3-current-host collect
./bin/fa3-current-host gate
./bin/fa3-current-host status
./bin/fa3-current-host all
./bin/fa3-current-host promote
\`\`\`

\`verify\` checks the current-host projection against the canonical policy, the exact \`CAP-001..CAP-143\` conformance surface, the 143-record Evidence Registry, registered collectors/gates, and the unified release manifest.

\`collect\` runs the existing read-only host fingerprint collector. Successful collection remains \`COLLECTED_UNVALIDATED\`; it is never converted to \`PASS\` merely because collection succeeded.

\`gate\` runs the global static, runtime, and 19-point acceptance gates. Exit code \`2\` means fail-closed blocking, not a successful promotion.

\`all\` performs \`verify → collect → gate\`. It deliberately does **not** promote.

\`promote\` is explicit and delegates to the existing FA3 promotion guard. It succeeds only when current-host evidence and all 19 acceptance criteria are already PASS.

## Current-host execution

CI validates only the projection structure. Real host execution is opt-in through \`.github/workflows/fa3-current-host.yml\` on a self-hosted runner labeled:

\`\`\`text
self-hosted, linux, x64, fa3-current-host
\`\`\`

No GitHub-hosted runner may claim current-host production evidence for the workstation.
