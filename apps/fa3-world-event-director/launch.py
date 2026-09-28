#!/usr/bin/env python3
"""FA3 World & Event Director standalone launcher.

--gui auto selects Qt6/PySide6 when installed; otherwise executable Tk fallback.
--headless-preview is dependency-free and suitable for CPU-only validation.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from fa3_world.engine import WorldProject


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--gui", choices=("auto","qt","tk"),default="auto")
    ap.add_argument("--headless-preview",action="store_true")
    ap.add_argument("--screenshot",help="Capture actual Tk GUI PNG under a graphical session")
    ap.add_argument("--project",help="Optional .fa3world JSON file")
    args=ap.parse_args(argv)
    project=WorldProject.load(args.project) if args.project else WorldProject()
    if args.headless_preview:
        print(json.dumps({"project":project.to_dict(),"sky":project.sky_context(),"four_scales":project.effects()},ensure_ascii=False,indent=2))
        return 0
    if args.gui in ("qt","auto") and not args.screenshot:
        try:
            from fa3_world.qt_app import run_qt
            return run_qt(project)
        except ImportError as exc:
            if args.gui=="qt":
                raise SystemExit("Qt6/PySide6 unavailable; use --gui tk or install PySide6 in a venv") from exc
            print("Qt6 unavailable; starting executable Tk preview",file=sys.stderr)
    from fa3_world.tk_app import WorldEventTk,run_tk
    if args.project:
        app=WorldEventTk(project)
        app.mainloop()
        return 0
    return run_tk(args.screenshot)


if __name__=="__main__":
    raise SystemExit(main())
