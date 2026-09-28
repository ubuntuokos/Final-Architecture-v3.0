# FA3 Skill Fabric — verified developer worker context (2026-09-28)

## Purpose and actual scope

The original coordinator accepted any caller-supplied list of dictionary
receipts with a PASS status, and selected SKILL.md bytes were never delivered
to the worker. The revised path accepts only an in-repository
`SkillTaskPreflight` instance for tasks declaring required skills.

This concrete preflight reads the current canonical skill registry; requires
exact registry membership and identity; calls the existing task-scoped
rehash-at-use and Language Gateway checks; then separately opens actual
SKILL.md bytes, verifies SHA-256 and requires a 128 KiB UTF-8 budget. No
remote fetch or skill script execution is performed.

The coordinator requires adapter-declared support for verified skill
projection. It stages a 0600 temporary JSON projection, passes its path to
the fixture worker, and requires the worker to attest the exact staged file
digest and declared skill IDs in its result. Temporary projection files are
deleted on normal and failed coordinator cleanup. Logs retain only task
identities, skill IDs, hashes and evidence scope, not SKILL.md content.

## Evidence and trust boundary

The built-in reference worker verifies the delivered content digest before
modifying its ordinary pre-existing test file. Tests include real source
tampering, unregistered skill denial, forged callback rejection, unsupported
adapter denial, and missing authority verifier denial.

An arbitrary Python callback returning True is **not** cryptographic
authentication. The production constructor requires an adapter wired to
existing FA3 authorities for admission, selection and language claims, but
this change does not provide or claim issuer-signed production receipts.
Reference mode is explicitly labelled CI_REFERENCE_ONLY. Production
admission and actual cross-host provider promotion remain PENDING.
The fixture worker verifies that it received the skill; it does not execute
instructions from that skill.

## Reuse and Hardware Audit

The existing Donor & Reference Registry was checked. No new donor source
or architectural authority is introduced. The code is CPU-only and
accelerator/vendor-neutral (0..N); no display GPU participation is needed.
No GUI/session coupling is introduced; existing Wayland/X11 rules remain.
