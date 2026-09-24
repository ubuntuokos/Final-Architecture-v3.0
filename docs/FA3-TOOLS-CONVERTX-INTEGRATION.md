# FA3 Tools Fabric + ConvertX integration

## Canonical decision

Generic file conversion remains `FA3-FILE-CONVERSION-001`. ConvertX is a replaceable long-tail provider and is **not** an architectural root, routing authority, resource authority or bundled FA3 runtime.

Current provider state:

- `FA3-PROVIDER-CONVERTX-001`: P2 / `QUARANTINED`;
- distribution: `USER_LOCAL_EXTERNAL`;
- FA3 release bundle: `EXCLUDED`;
- production machine execution: **disabled**;
- current-host status: `PENDING_REAL_HOST_EXECUTION`;
- XeLaTeX and LaTeX-family direct selection: **DENY**.

## Current execution boundary

```text
GUI / agent / CLI / MCP / automation intent
  -> typed file.convert.* UAF action
  -> identity / authorization / approval
  -> deterministic SPECIALIZED_PROVIDER_FIRST routing
  -> hardware compatibility
  -> HRB resource admission
  -> governed provider adapter
  -> execution
  -> evidence / provenance
```

Direct GUI, agent, MCP, n8n or automation invocation of ConvertX is forbidden.

The canonical UAF actions are:

- `file.convert.plan`
- `file.convert.execute`
- `file.convert.inspect`

The Control Center exposes Tools at semantic route `create.tools`. It creates only `DRAFT_NOT_SUBMITTED` intents and has no execution authority.

## Decision Fabric

Decision Fabric use is **OPTIONAL** and limited to advisory classification among the exact FA3-defined Tools intents. It cannot select or admit ConvertX, expand the conversion allowlist, activate CANDIDATE pairs, authorize execution or obtain resources. Provider routing stays deterministic `SPECIALIZED_PROVIDER_FIRST`.

## ConvertX adapter

The FA3 adapter remains pinned to ConvertX v0.18.0's observed internal web flow because no official stable public machine API is claimed:

1. bootstrap isolated loopback state;
2. upload one staged input;
3. submit one allowlisted target/converter mapping;
4. poll the matching job result;
5. download exactly one server-issued result link.

The adapter never derives provider identity from JWT payloads, never predicts output names, rejects non-loopback/cross-origin routing, rejects output overwrite and symlinks, enforces size/time limits, and records SHA-256.

## Pair lifecycle

`FA3-CONVERTX-CONVERSION-ALLOWLIST-001` is deny-by-default.

- `CANDIDATE`: isolated candidate validation only.
- `ACTIVE`: eligible for production routing only after pair-specific evidence and provider promotion.

Provider promotion cannot implicitly activate candidate pairs.

## Resource-admission boundary

The Host Resource Broker remains the only resource authority. Its canonical profile covers typed CPU/memory/accelerator placement, but the current-host bootstrap still reports non-accelerator CPU/memory authorization as:

`HRB_NON_ACCELERATOR_AUTHORIZATION_UNMATERIALIZED`

Therefore ConvertX production/current-host execution remains fail-closed. Accelerator lease evidence cannot substitute for CPU/memory authorization, and this integration creates no resource authority.

## Distribution boundary

The upstream ConvertX runtime is `USER_LOCAL_EXTERNAL` and excluded from the FA3 product bundle. FA3 may distribute its own provider-neutral contracts, policy, GUI and adapter code without asserting that the upstream runtime is part of the FA3 redistributable bundle.

## Promotion gate

Promotion from P2/`QUARANTINED` to P1/`APPROVED` still requires all of:

- static and security conformance;
- authoritative HRB non-accelerator CPU/memory admission;
- digest-pinned runtime identity;
- real current-host safe-pair E2E;
- real output hash/provenance;
- egress-denial and resource-limit evidence;
- pair-specific evidence;
- explicit `CANDIDATE` → `ACTIVE` transition;
- valid current-host production E2E receipt.

Hosted CI and documentation changes never satisfy current-host promotion.
