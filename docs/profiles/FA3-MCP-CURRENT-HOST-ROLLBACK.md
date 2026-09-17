# FA3 MCP Current-Host rollback

Rollback of `FA3-MCP-CURRENT-HOST-001` MUST:

1. stop/disable the current-host gateway runtime;
2. revoke runtime adapter registrations and ephemeral leases/handles;
3. preserve canonical provider/profile records and evidence history;
4. leave MCP Control Chat targets non-connected;
5. keep direct agent-to-provider production execution denied;
6. avoid transferring MCP authority to any client, provider, registry or orchestration component.

Rollback is an availability reduction, not an authority transfer.
