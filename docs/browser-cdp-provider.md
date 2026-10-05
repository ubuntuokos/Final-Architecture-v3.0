# FA3 CDP Browser Execution Provider

`FA3-PROVIDER-BROWSER-CDP-001` is the first physical execution provider for `FA3-BROWSER-ACTION-RUNTIME-001`. It is optional, disabled by default and is not an architectural authority.

The provider discovers a Chromium-compatible CDP browser on the current host at runtime. That dependency is provider-scoped only: FA3 itself does not require Chrome, Chromium, Brave, Edge, a GPU, NVIDIA or CUDA.

The provider launches a temporary sandboxed browser profile with loopback-only CDP. Remote CDP endpoints are rejected. The browser sandbox is never disabled. The provider accepts only an already-bound `browser.action.execute` request from UAF; it cannot accept model-created CSS selectors, JavaScript, arbitrary target IDs or new actions.

Observation IDs, document IDs, page fingerprints and action-space hashes are revalidated immediately before execution. Physical click/type/key events are issued only after this guard passes. Mutating retries remain protected by the Browser Action Runtime ledger. Outcome verification is independent from execution.

The current-host gate runs a real local HTTP page and a real discovered browser on the `fa3-current-host` self-hosted runner. It proves positive physical click execution, stale-observation denial, UAF/HRB/evidence mediation and cleanup rollback. Synthetic or GitHub-hosted current-host promotion is denied.

A successful current-host receipt admits this provider for that evidenced host/run only. It does not create a global browser-provider requirement or a global promotion claim.
