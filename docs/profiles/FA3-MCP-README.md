# FA3 Central MCP/Capability Gateway profiles

This directory materializes, but does not replace, the existing canonical authority `FA3-AUTH-MCP-GATEWAY-001`.

Relationships:

```text
FA3-AUTH-MCP-GATEWAY-001       (existing canonical authority)
        |
        +-- FA3-MCP-CURRENT-HOST-001
        |      +-- FA3-MCP-CAPABILITY-CONTRACT-001
        |      +-- FA3-MCP-CAPABILITY-REGISTRY-SEED.yaml
        |      +-- FA3-MCP-CURRENT-HOST-REGRESSION-GATE.md
        |      +-- FA3-MCP-CURRENT-HOST-EVIDENCE-TEMPLATE.yaml
        |
        +-- FA3-MCP-AUTHORITY-NONREGRESSION.md

FA3-MCP-CONTROL-CHAT-001 is a control-surface/client projection and does not gain execution authority.

Current-host state remains `PENDING_CURRENT_HOST` until runtime evidence satisfies the mandatory gate.
