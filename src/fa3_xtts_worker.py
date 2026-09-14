#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Isolated FA3 XTTS-v2 worker")
    parser.add_argument("--speaker-wav", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--language", default="hu")
    args = parser.parse_args()
    text = sys.stdin.read()
    if not text.strip() or args.language != "hu":
        raise SystemExit("FAIL-CLOSED: XTTS worker requires non-empty Hungarian input")
    from TTS.api import TTS
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda:0")
    tts.tts_to_file(text=text, speaker_wav=args.speaker_wav, language="hu", file_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
