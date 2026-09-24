#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fa3_gui_current_host import collect


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect FA3 Control Center physical current-host GUI evidence"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--executable", required=True)
    parser.add_argument(
        "--output",
        default="reports/gui-current-host/current-host-receipt.json",
    )
    parser.add_argument("--smoke-seconds", type=float, default=8.0)
    parser.add_argument(
        "--tested-path",
        default="CONTROL_CENTER_STARTUP_SESSION_VAULT_UNCONFIGURED",
        choices=["CONTROL_CENTER_STARTUP_SESSION_VAULT_UNCONFIGURED"],
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    executable = Path(args.executable)
    if not executable.is_absolute():
        executable = root / executable
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    report = collect(
        root,
        executable,
        output_dir=output.parent,
        smoke_seconds=max(5.0, args.smoke_seconds),
        tested_path=args.tested_path,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
