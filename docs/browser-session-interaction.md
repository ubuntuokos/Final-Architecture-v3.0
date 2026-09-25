# FA3 Browser Session Interaction

## Status

`FA3-BROWSER-SESSION-INTERACTION-001` is a zero-authority child of the canonical Browser Action Runtime. It adds a governed local bridge for an existing Chromium-compatible browser profile without creating a second browser-action, security, human-approval, secret, resource, evidence, workflow, or model-routing authority.

Capability count remains **143**. New capabilities: **0**. New architectural authorities: **0**.

The physical implementation is materialized, but production/current-host claims remain evidence-gated. Automated physical qualification does **not** claim that a real logged-in user profile or a real human-completed assistance step has been proven.

## Architecture

```text
Browser tab / Agent Window
        |
FA3-native MV3 extension
        |
Chromium Native Messaging
        |
fa3-browser-session-native-host.py
        |
$XDG_RUNTIME_DIR/fa3/browser-session/bridge.sock
        |
BrowserSessionBridgeServer
        |
FA3-PROVIDER-BROWSER-SESSION-BRIDGE-001
        |
Unified Action Fabric
        |
Browser Action Runtime
        |
Security / Human approval / HRB / Evidence
```

There is no required TCP listener and no imported BrowserSkill runtime. Tencent BrowserSkill remains a pinned pattern and host-compatibility reference only.

## Non-interfering tab borrow

FA3 intentionally strengthens the reference pattern: borrowing an existing user tab is a **logical lease**, not a tab move into the Agent Window.

A `BrowserTabLease` is bound to:

- the FA3 browser session;
- one opaque tab reference;
- the current origin;
- an explicit action scope;
- an issue/expiry interval;
- a single-use external approval receipt.

The user's tab remains in its original window and index. This avoids changing the user's layout and removes the risk that closing the Agent Window also closes a borrowed user tab.

Sibling tabs, popups, and newly opened tabs do not inherit the lease. A navigation that changes origin invalidates the usable scope until a new authorization is issued.

## Privacy and secrets

`browser.tab.list` returns opaque tab/window references, index, active state, origin, and FA3 scope only. Full URL paths, page titles, cookies, tokens, passwords, browser-profile contents, and authentication material are not inventory output.

The extension does not request the Chromium `cookies`, `history`, `downloads`, `webRequest`, `webRequestBlocking`, or `debugger` permissions.

Authenticated session use is not secret extraction. The FA3 Secret authority remains separate.

## Browser actions

The session provider does not accept model-generated selectors or JavaScript. It reuses `FA3-BROWSER-ACTION-RUNTIME-001`:

```text
observe
 -> normalize
 -> build bounded action space
 -> bind candidate
 -> revalidate fresh observation
 -> authorize
 -> execute
 -> independently verify
```

Supported page mutations remain bounded to CLICK, TYPE_TEXT, SELECT, SCROLL_INTO_VIEW, and allowlisted key presses. Page content is always `UNTRUSTED_EXTERNAL_CONTENT`.

Stale observations and blind mutation retries fail closed.

## Human assistance

The extension can present a visible Continue/Cancel overlay for login, CAPTCHA, OTP, consent, payment confirmation, or other human-only steps.

Two evidence lanes are deliberately separate:

1. **automated physical evidence** may prove that the overlay was physically rendered and that the request remained `PENDING_HUMAN`;
2. **manual human qualification** is required to prove that a real person completed the requested step.

An automated test must never click Continue and then label that result as human evidence. Cancellation does not mean completion, and resumption after real human assistance requires a fresh observation and authorization.

## Software coexistence

The current-host test uses:

- a temporary HOME;
- a temporary browser profile;
- temporary Native Messaging host manifests inside that HOME;
- a namespaced runtime directory and Unix socket;
- the already installed browser executable discovered at runtime.

It does not uninstall, replace, shadow, or globally reconfigure Chrome, Chromium, Brave, Edge, BrowserSkill, or another browser-automation tool.

## Hardware Audit

The bridge is CPU-only viable and vendor-neutral. Accelerator cardinality is `0..N`; no GPU, NPU, CUDA, ROCm, oneAPI, vendor, or SKU is a prerequisite.

Every UAF browser-session action still requires the existing Host Resource Broker. The physical current-host gate obtains and revalidates a real CPU-only HRB admission authorization.

## Current-host evidence

The automated self-hosted gate must physically prove:

- a real Chromium-compatible process;
- the FA3 MV3 extension;
- Chromium Native Messaging;
- the namespaced Unix socket;
- a real CPU-only HRB authorization;
- separate Agent Window creation;
- redacted tab inventory;
- missing-approval denial;
- wrong-origin denial;
- policy-approved logical borrow without reparenting;
- Browser Action Runtime bounded mutation and independent verification;
- stale-binding rejection;
- human-assistance overlay presentation with no synthetic human-completion claim;
- explicit return;
- TTL expiry and loss of control;
- session stop and process rollback.

The following remain separate manual qualifications until real evidence exists:

- reuse of a real logged-in user browser profile;
- actual human completion of an assistance request.

Static/canonical success and automated bridge E2E do not imply either manual claim or global FA3 promotion.
