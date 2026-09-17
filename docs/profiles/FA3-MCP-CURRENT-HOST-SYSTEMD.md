# FA3 MCP Current-Host systemd contract

`FA3-MCP-CURRENT-HOST-001` MUST be deployed as a managed current-host service under systemd (or an explicitly canonical equivalent on a non-systemd host).

Minimum unit properties:

```ini
[Unit]
Description=FA3 Central MCP Capability Gateway
After=network.target

[Service]
Type=notify
Restart=on-failure
RestartSec=2
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
RestrictSUIDSGID=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes

# Exact executable, user/group, paths, capabilities and resource limits are
# materialized by the host package/profile and must be admitted before use.

[Install]
WantedBy=multi-user.target
```

Security directives are a minimum intent contract, not a copy-paste final unit. Required filesystem/network access MUST be explicitly narrowed to the gateway implementation and admitted adapters. GPU/CPU/RAM execution remains governed by HRB leases rather than by this unit becoming a resource authority.

The service MUST expose health/readiness locally and MUST NOT bind a remotely reachable listener by default. Remote access, if ever used, requires a separate canonical exposure and identity/TLS policy.
