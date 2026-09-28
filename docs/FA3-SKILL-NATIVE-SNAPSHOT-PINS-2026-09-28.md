# Native admitted FA3 skill byte pins

The five existing FA3-native, already ADMITTED quality skills have SHA-256
content and deterministic one-file manifest digests in the **existing**
canonical skill registry. The immutable source commit is recorded and no
new registry, architectural authority or capability is introduced.

The existing Skill Fabric parent gate now invokes the shared no-symlink
snapshot digester on each native admitted SKILL.md. Unexpected file changes,
missing or unsafe assets, malformed metadata, and digest drift fail closed.
The skill CI is triggered by registry and native SKILL.md changes. Tests
verify the actual repository bytes and deliberately tamper with a copied
native skill to confirm rejection.

This is current-tree **static integrity**, not cryptographic source-commit
signature verification, admission issuer authentication, production
projection adoption or current-host runtime promotion. A revised skill
requires updated reviewed digest metadata and the usual FA3 admission.
Historical 143-capability records are untouched; current release baseline
remains 175.

Hardware Audit: CPU-only and vendor-neutral. 0..N GPUs/NPUs permitted
without accelerator requirement or automatic display-GPU recruitment.
No desktop environment, Wayland, X11 or provider dependency is added.
