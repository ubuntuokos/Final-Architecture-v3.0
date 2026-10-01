# FA3 Plugin & Extension Management Fabric

This materializes the shared, authority-neutral FA3-wide plugin and extension management plane.

## Core rule

There is one common manager backend and one state model. Every FA3 GUI application must expose an application-context entry to it, while the same manager is also available from Control Center and from a standalone launcher without starting the target application.

`INSTALLED != ADMITTED != ENABLED != CURRENT_HOST_PASS`.

## Authority boundaries

The manager does not own Registry, SCS, Security/Governance, MCP/Capability Gateway, Model Router, HRB, Secret Broker, durable orchestration, Layer Guard or Evidence authority. It composes their decisions and fails closed.

## AI

AI access is declared per extension and remains centrally and locally switchable. Disabled AI may not launch a model, call a provider, start a background AI service or silently fall back.

## Shared packages

A shared package has one package identity and per-application consumer bindings. Disabling it in one application does not disable it in other consumers.

## Lifecycle

Resolve → Impact → Approval → Stage → Verify → Commit. Update permission growth requires approval; ABI break cannot auto-activate; rollback is mandatory.

## Current Host

Static materialization is not runtime promotion. Physical Current Host evidence remains required for install/deny/rollback/quarantine/coexistence/CPU-only/HRB/standalone-GUI cases declared in `FA3-PLUGIN-EXTENSION-CURRENT-HOST-001`.
