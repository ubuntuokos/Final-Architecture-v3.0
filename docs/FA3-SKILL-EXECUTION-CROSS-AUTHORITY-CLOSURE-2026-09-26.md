# FA3 Skill Execution Cross-Authority Closure

Date: 2026-09-26

This material extension strengthens `FA3-SKILL-FABRIC-001` only. It creates no capability, architectural authority, provider, global daemon, model router, resource broker, secret authority, sandbox authority or evidence authority.

Canonical execution chain:

`Skill admission -> activation preview -> SkillExecutionBinding -> existing MCP / Model Router / HRB / Secret Broker / Agent Workload / Agent Sandbox -> Hardware Safety + CAP-175 coexistence preconditions -> execution -> postcondition -> cleanup/rollback -> SkillExecutionReceipt -> Evidence`.

A skill package remains inert data until separately authorized. Binding and receipt records are not authorities.

Fixed bounds: capability count 175; capability delta 0; authority delta 0; provider delta 0; new daemon count 0. Static or CI PASS never promotes current-host runtime state. PR #410 CAP-175 materialization is a dependency and remains separately auditable.

Arbitrary root shell, unrestricted sudo, broad host subprocess execution, direct provider/model/tool/resource/secret bypass and unsandboxed arbitrary code remain denied. Privileged actions may only reuse an already-authorized exact-helper path and remain subject to Hardware Safety and coexistence policy.

A PASS execution receipt requires postcondition verification and cleanup. Current-host PASS requires separate physical evidence; this change itself makes no current-host runtime claim.
