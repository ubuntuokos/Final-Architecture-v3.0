# FA3 Hungarian-First Content Studio

`FA3-HU-CONTENT-STUDIO-001` separates three policy surfaces that must not be
collapsed into one convenience API:

1. Hungarian copy generation (`hu-HU`) with an injected real language
   validator.
2. Consent-bound XTTS-v2 voice cloning in an isolated GPU worker.
3. Generic Piper Hungarian TTS, which is **not** voice cloning and is never a
   silent fallback for a failed clone request.

## Security invariants

- voice-cloning consent is exact, purpose-bound, time-bounded, revocable,
  speaker-file-bound, and HMAC-SHA256 verified;
- the HMAC key is supplied by the secret/token vault and never stored in the
  consent registry;
- provider/model/voice use is deny-by-default until a separate license and
  intended-use admission record is `APPROVED`;
- GPU synthesis requires a Host Resource Broker lease, and the lease is
  released in `finally`;
- the XTTS worker receives the leased GPU through `CUDA_VISIBLE_DEVICES` in a
  child process rather than mutating the long-lived GUI/service process;
- Piper is invoked with argv + stdin, never `shell=True`;
- provenance hashes the actual reference WAV bytes;
- no code path hardcodes a `CURRENT_HOST_*_PASS`.

A real current-host PASS additionally requires a qualified host attestation
and an HRB lease explicitly attested to that host. Portable unit tests remain
portable security evidence only.
