# Verification — 2026-09-18

- 130 projects retained: original 14 plus 116 source-reviewed additions. Five false positives excluded permanently pending review.
- Live scans: initial GitHub Actions run succeeded and committed data; expanded local repository/README/commit/PR scan checked 130 candidates; corrected code-search supplement checked 60 more.
- Code-search correction verified live: the same domain query returned 1,348 matches without unsupported `is:public`, and zero with it. The radar now filters repository visibility explicitly.
- Fixed-version source evidence reviewed for all current entries; no project runtime or performance verification is claimed.
- Browser checks passed: fuzzy typo search, category/tag/star filters, all three sort modes, empty state, bookmark reload persistence, keyboard search, copy-share URL, project evidence dialog, and submission form validation. No issue was submitted during testing.
- Desktop and phone layout checked: no document horizontal overflow; phone cards form one column. Native modal focus and Escape behavior checked.
- Search benchmark at 134 pre-review candidates: 500 queries, p95 2.56 ms of search computation, with a 90 ms input debounce. This is not a network or end-to-end latency benchmark.
- WebMCP search tested with valid input; invalid input intentionally rejected.
- Privacy review excludes local paths and common credential patterns from publication. Source credentials remain ephemeral.
- Source caps, remaining candidate queues and failures are visible in radar receipts; a successful workflow is not presented as exhaustive web coverage.

## GitHub Pages hardening

- Pages enabled through REST API as a workflow-based public HTTPS site; Actions default permissions read back as write, without PR-approval capability.
- All workflows explicitly declare contents/pages/id-token write permissions. Pages deployment accepts main only, with no manual reviewer gate.
- 25 focused tests passed for source verification, pinned fields, serial pacing, retries, redirect credential isolation, and public projection.
- Public build audit passed: no credential patterns, private paths, source maps, radar configuration or crawler logs; only the allowlisted project fields are shipped.
- 14 original projects are pinned; all 130 curated descriptions, decisions, benefits, tags, categories and evidence match the pre-change baseline.
- Production local preview rendered 130 projects, the removed radar interface was absent, repository links opened in a new tab, and a nested query-parameter project URL rendered its detail without a blank screen.
- Twitter/OpenGraph fields and the actual 1200×630 PNG share image were inspected. X cache refresh behavior and unmeasured traffic capacity are not guaranteed.

## Interaction and bilingual release

- 35 tests passed, including repository shorthand/deep-link/SSH normalization, malicious-host rejection, Unicode length checks, issue parameter encoding, English validation, and UI translation coverage.
- Browser verified Chinese/English switching and reload persistence; 24 records have English copy, and an untranslated record correctly falls back to its original summary.
- The Star action contains only a star icon and “Star on GitHub”; it does not fetch or display this repository's star count.
- Submission stays enabled. Empty and short inputs produce inline errors after activation; the first invalid field receives focus. A deep repository URL was cleaned to its root and a real new tab opened the encoded issue draft URL. No issue was published.
- Dialog padding clicks keep it open; backdrop clicks close it and restore page scrolling. Draft text survives close/reopen, and closing project details removes its query/hash selection.
- A reviewed guard keeps project deep links and the submission dialog mutually exclusive during delayed data loading; modal title IDs are unique.
- Search slash/Cmd-K, explicit empty-state recovery, all external link attributes, and 375px/430px layouts were checked. No document horizontal overflow was observed in either language.
- The featured placement links directly to the requested X profile; README contains the live-site badge and bilingual submission instructions.
- The English-copy patch preserved the prior 130 records and added optional fields for 24 records. Later upstream jev-trade content/evidence changes and single-record tolerance were merged without reverting them.
