# FA3 PageIndex MCP provider

\`FA3-PROVIDER-PAGEINDEX-MCP-001\` is an optional cloud-backed reasoning-RAG provider behind the canonical \`FA3-AUTH-MCP-GATEWAY-001\`. It creates no new FA3 authority and projects only the existing \`fa3.document.index\` and \`fa3.document.retrieve\` capabilities.

## Capability mapping

The adapter exposes only four upstream operations:

- \`fa3.document.index\` -> \`process_document\`
- \`fa3.document.retrieve(operation=metadata)\` -> \`get_document\`
- \`fa3.document.retrieve(operation=structure)\` -> \`get_document_structure\`
- \`fa3.document.retrieve(operation=pages)\` -> \`get_page_content\`

Other PageIndex tools discovered dynamically are not exposed. The adapter checks the required input fields returned by \`tools/list\`; incompatible remote contract drift fails closed.

The current PageIndex cloud MCP contract identifies retrieval targets by \`doc_name\` plus optional \`folder_id\`. FA3 exposes these as \`document_name\` and \`folder_id\`.

## Privacy and approval

PageIndex MCP is cloud-backed. A local PDF passed to \`process_document\` can leave the workstation and be processed by PageIndex infrastructure. Therefore the PageIndex binding overrides the generic \`fa3.document.index\` approval mode to **explicit**. The generic capability contract itself is not changed.

The upstream local MCP client stores OAuth state in \`~/.pageindex-mcp/oauth-tokens.json\`. FA3 production use must instead provide a Secret-Broker-created ephemeral HOME containing that file with mode 0600 (or stricter). Invocation-time interactive OAuth is denied.

## Supply-chain pin

Canonical upstream identity:

- release: \`v1.8.2\`
- PageIndex MCP source commit: \`bda946b4b6fffaaf6926aa8809bc62e0098f30e8\`
- MCPB SHA-256: \`972705b6991a5291112db368fafccf2ce89926a8a0318601cba89bff4adc5de2\`
- PageIndex cloud-contract reference commit: \`18eb5c9b3c31d305c022974aa194a7047950228b\`
- Node.js: \`>=20.8.1\`
- package manager declared upstream: pinned pnpm 10.12.1 via Corepack

Production execution does not use floating \`npx\`. Materialize the exact source tree and build it with the locked dependency graph:

\`\`\`bash
sudo bash bin/fa3-pageindex-mcp-bootstrap.sh
\`\`\`

The adapter verifies the clean Git commit, package version and exact \`node <source-root>/build/index.js\` command before starting the provider.

## Current-host E2E

A real provider PASS requires all of the following: authenticated ephemeral OAuth material, an explicitly approved sample PDF, authenticated \`tools/list\` with matching schemas, Gateway-mediated upload, completed metadata lookup, structure retrieval, page-content retrieval, and the mandatory negative checks.

Example:

\`\`\`bash
FA3_PAGEINDEX_MCP_SOURCE_ROOT=/opt/fa3/providers/pageindex-mcp-bda946b4b6fffaaf6926aa8809bc62e0098f30e8 \
FA3_PAGEINDEX_MCP_OAUTH_HOME=/run/fa3-secrets/pageindex \
FA3_PAGEINDEX_MCP_SAMPLE_PDF=/approved/e2e/sample.pdf \
bash bin/fa3-pageindex-mcp-current-host.sh
\`\`\`

The canonical registry bindings remain \`PENDING_CURRENT_HOST\` until that receipt is admitted. Documentation, discovery, a successful local fake-server regression, or GUI visibility can never promote the provider to \`CONNECTED\`.
