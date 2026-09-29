# FA3 S3: original/translated text and AV transcript fan-out preview

Date 2026-09-29; PR #528. This builds on S1 17 source-family choices and S2 original stream binding. **This is a pure dependency planner, not STT, translation, GUI, model/runtime or current-host PASS.**

## Source-aware 0/1/N original and target languages

- TEXT document: inspect native source text through existing Document Fabric / Story; optional Language Fabric translation, preserving source paragraph and revision IDs.
- AUDIO/VIDEO derived TEXT or TRANSCRIPT_ONLY: if selected track is audio, existing STT must generate a corrected and timestamped original transcript before translation; if selected track is an original subtitle stream, existing Caption/Subtitle Studio must inspect it. VIDEO with both source audio and original timed text requires an explicit operator origin choice; these sources may disagree and cannot be silently conflated.
- ORIGINAL_LANGUAGE yields only the source language. ONE_TRANSLATION yields exactly one target. MULTI_TRANSLATION yields all requested targets. ORIGINAL_PLUS_TRANSLATIONS produces original and all targets with separate immutable identities. Audio/video transcript overlays use the identical logic; no 18th selector.
- Source locale auto detection or code-switching is explicitly pending per-segment Language Fabric verification. Translation glossary, named entities, human correction, subtitle cue alignment and BCP-47/script variants require separate approved downstream evidence.
- Preview output is bounded to 1024 branches from at most 256 S1 output leaves; no hidden AV delivery for transcript-only requests. A repeated destination/language/range from two selected modes is flagged as PENDING_DUPLICATE_DESTINATION_REVIEW, not overwritten.

The typed S3 plan is `canonical/schemas/selective-language-fanout.v1.json`, implemented without I/O in `src/fa3_selective_import_language_fanout.py`; synthetic positive/negative fixtures are in `tests/test_selective_import_language_fanout.py`. Real S3 acceptance still requires source-rights and authenticated inspection receipts from existing Security/Evidence; existing File Conversion, Language Fabric, STT/Subtitle Studio and UAF/Temporal integration; original-language and Hungarian/other locale golden fixture assessment; human-controlled publication and signed current-host E2E. No unrequested media may be published and no cloud upload is permitted without explicit approval. Capability baseline remains 175 and provider count dynamic.
