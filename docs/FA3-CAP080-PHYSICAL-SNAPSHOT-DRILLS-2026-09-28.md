# CAP-080: physical snapshot drills added to Skill Fabric qualification

The existing CAP-080 verified supply-chain constituent already runs positive,
negative and rollback drills but relies on synthetic descriptor/digest fixtures.
This change retains those gates and adds **actual local filesystem** evidence:
- Positive: writes a real SKILL.md in the qualification scope, binds its real
  digest and deterministic manifest, verifies actual bytes at admission and use.
- Negative: mutates the real file after activation and requires fail-closed
  rejection when the materializer rehashes it at use.
- Rollback: changes the real file, checks denial, restores exact original
  bytes and checks that the same admitted lease works again.

The three cases run in each qualification mode, inside the caller's existing
source-artifact scope. Existing CAP-080 provenance and verdict schemas remain
unchanged; the result gains explicit physical fixture fields. These tests
prove current-host *fixture file operations* when the official host collector
actually invokes them; a CI run remains **reference testing only**. They do
not authenticate production admission issuers, drive a real agent consumer,
or independently promote CAP-080 or the whole Skill Fabric to production.
Any real status change still goes through existing Evidence authority.

Hardware audit: local filesystem and Python only. CPU-only, vendor-neutral,
zero to N accelerators, no display-GPU use or desktop/session dependency.
