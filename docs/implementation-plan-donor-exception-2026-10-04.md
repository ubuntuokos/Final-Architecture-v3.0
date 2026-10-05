# Implementation-plan donor analysis exception

**Date:** 2026-10-04  
**Scope:** CFA3 development workflow and donor-governance enforcement only.

During implementation-plan preparation, an external source may receive substantive technical analysis before registry admission only in the originating conversation lineage and its direct continuations. The readiness gate must receive that active lineage explicitly; a copied or self-declared assessment cannot authorize planning in another conversation.

After owner approval, every donor listed in `planning_processed_donors` must be published in the canonical Donor & Reference Registry before implementation execution continues. The approved plan creates a narrow registration authorization for exactly that processed set, so a second per-link donor command is not required.

The approval record, plan, and donor assessment must all be committed. The approval binds the exact plan SHA-256, assessment SHA-256, processed normalized-key set, and conversation lineage. Any mismatch fails closed. The registry writer may register only an exact key from that committed approved set.

This exception authorizes reference registration only. It never authorizes donor adoption, code copying, dependency installation, provider/model admission, runtime activation, architectural authority, or Current Host promotion. Ordinary donor intake outside this exception continues to require an authenticated explicit owner donor-intake command.

The `plan` readiness phase may allow unregistered processed donors only under the exact active-lineage exception and never grants execution. `entry`, `execute`, and `finalize` fail closed while any processed planning donor is absent from the verified published-main registry. Finalization retains the existing immutable approved-plan and exact-head review requirements.

Capability baseline remains **175**; capability delta and architectural-authority delta are **0**.
