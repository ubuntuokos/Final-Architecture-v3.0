# FA3 Communications Hub

Qt6/QML standalone projection of **FA3 Communications & Contacts Shared**.

The executable is intentionally provider-neutral and has no direct SMTP/IMAP/CardDAV or AI-provider implementation. QML emits action intents only. Network/provider execution must be supplied later through the existing FA3 UAF, Security Governance, Secret Broker and provider-admission path after physical Current Host evidence.

CommunicationsSharedSurface.qml is the reusable projection:
- surfaceMode FULL for the standalone Hub.
- surfaceMode EMBEDDED for application-local context-filtered use.
- embedded mode hides account/security administration and must not enumerate the global address book.
- openFullHubRequested(context) preserves focus context without granting broader permissions.
