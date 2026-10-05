# CFA3/FA3 one-click conversation handoff

**Policy:** `CFA3-ONE-CLICK-CONVERSATION-HANDOFF-POLICY-001`
**Status:** mandatory on the development line and in the CFA3/FA3 product UX.

## Development rule

Whenever the owner asks to continue work in a new conversation, the complete continuation payload is one logical handoff artifact. It MUST be presented in exactly one one-click-copyable surface. This remains mandatory for a one-word payload.

The payload must not be split between prose and copy surfaces, split across several copy blocks, or require manual text selection or scrolling to make the copy complete.

## Product rule

Every CFA3/FA3 assistant, agent, workflow, application or context-transfer UI that presents a new-conversation handoff MUST use the shared one-click handoff behavior:

- one complete payload;
- one visible **Másolás / Copy** primary action;
- one platform-equivalent action copies the complete payload;
- visual scrolling may be used for display, but copy completeness is independent of scroll position;
- an empty handoff is not presented;
- copy failure is visible and never reported as success.

The reference QML component is `apps/shared/conversation-handoff/qml/OneClickHandoffBox.qml`. The Control Center Chat Workspace consumes the same shared component.

This policy creates no new architectural authority and does not change the 175 capability baseline.