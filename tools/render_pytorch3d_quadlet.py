#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

DIGEST_REF = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")


def render(template: str, image_ref: str) -> str:
    if DIGEST_REF.fullmatch(image_ref) is None:
        raise ValueError("runtime image must be an immutable @sha256 reference")
    if "@IMAGE_REF@" not in template:
        raise ValueError("quadlet template missing @IMAGE_REF@")
    return template.replace("@IMAGE_REF@", image_ref)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True)
    p.add_argument("--template", type=Path, default=Path("deployment/quadlet/fa3-pytorch3d.container.in"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.write_text(render(a.template.read_text(encoding="utf-8"), a.image), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
