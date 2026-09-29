# FA3 Skill Fabric - existing Codex verified skill consumer

This stacked PR reuses the existing pinned Codex adapter, existing isolated worktree, strict sandbox and disabled web/MCP/plugins/subagents. No new provider or model authority is created.

A task requesting approved skills reaches the existing coordinator as a private, bound skill projection. The Codex worker checks expected task and agent, exact skill identities, immutable content digests, lease expiry and evidence scope before invoking the pinned binary. CI-only reference mode requires an explicit adapter flag. Approved skill text is passed as bounded, inert, quoted data; it cannot authorize tools, shell use, additional agents or mutation beyond the original exact task.

Reference tests check actual fake-Codex prompt consumption; additional tests pass real ephemeral test-certificate signatures through the existing FA3 verifier and Codex adapter. This is NOT live workstation Codex evidence or promotion: deployed issuer keys, source pins, actual installed binary, its pre-existing current-host admission and official current-host collector must still be checked.

Hardware audit: CPU-only, vendor neutral, 0..N accelerators, no automatic display GPU recruitment. No desktop/session coupling; Wayland and X11 compatibility unchanged.
