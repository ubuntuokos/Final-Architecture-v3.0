# FA3-MCP-GATEWAY-001 — Central MCP Gateway

## Végleges döntés

Az FA3 egyetlen canonical MCP/tool/capability végrehajtási határa a
FA3-AUTH-MCP-GATEWAY-001 authority alatt működő FA3-MCP-GATEWAY-001.

A gateway providerfüggetlen. A microsoft/mcp-gateway referenciaimplementáció és
részleges kód-/mintaforrás, nem kötelező runtime dependency és nem authority.

## Canonical transport

- MCP revision: 2026-07-28.
- Canonical mód: stateless.
- Modern endpoint: POST /mcp.
- server/discover kötelező.
- MCP-Protocol-Version, Mcp-Method és Mcp-Name routing/validation kötelező.
- Mcp-Session-Id a modern útvonalon tiltott.
- initialize/initialized a modern útvonalon tiltott.
- Régi stateful MCP csak külön, admitted compatibility adapteren keresztül használható.
- FA3 application/workflow state explicit handle vagy FA3 context id lehet; ez nem MCP transport-session.

## Authority boundary

A gateway nem veszi át a policy, identity, secret, HRB, Temporal, model routing,
Journal vagy evidence authority szerepét. Ezek döntéseit/bérleteit ellenőrzi és
érvényesíti. Közvetlen agent/provider bypass production útvonalon DENY.

## Planes

Data plane: modern MCP ingress, typed dispatch, result/stream forwarding.
Control plane: Provider/Tool/Capability/Route Registry és lifecycle projection.
Policy plane: külső authorization/approval döntések végrehajtása, timeout,
rate-limit és circuit-breaker policy.
Governance plane: provenance, supply-chain admission, audit/evidence, revocation.

## Local-first lifecycle

Kubernetes, Azure és Entra ID nem kötelező. A lifecycle driver lehet systemd,
native process, Podman, Docker, Kubernetes vagy remote adapter. A current-host
default bind továbbra is loopback 127.0.0.1:18790.

## GUI

Az FA3 Control Center első osztályú MCP Gateway oldalt tartalmaz:
Overview, Servers, Tools, Providers, Capabilities, Routes, Requests,
Permissions, Security, Logs, MCP Inspector és Settings.

A GUI health/registry adatot olvashat, draftot készíthet és policy-gated backend
műveletet kérhet, de QML-ből közvetlen tool execution és GUI self-approval tilos.
CONNECTED/PASS állapot nem fabrikálható.

## Promotion

A canonical döntés FINAL és a statikus implementáció materializált, de a
production runtime csak valódi current-host E2E evidence után promotálható.
A meglévő FA3-MCP-CURRENT-HOST-001 current-host gate változatlanul fail-closed.
