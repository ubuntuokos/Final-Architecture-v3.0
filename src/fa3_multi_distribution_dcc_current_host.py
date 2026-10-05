#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fa3_full_current_host_capability_producer as base
from fa3_application_installation_resolver import discover_group


def _healthy_dcc(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = discover_group(root, "DCC", perform_health_check=True)
    healthy = [row for row in rows if row.get("health") == "HEALTHY"]
    if not healthy:
        raise RuntimeError("no healthy registered DCC installation instance")
    healthy.sort(key=lambda row: (
        str(row.get("application_id", "")),
        str(row.get("packaging", "")),
        str(row.get("locator", "")),
    ))
    return rows, healthy[0]


def proof_graphics_3d(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    rows, chosen = _healthy_dcc(Path.cwd().resolve())
    sentinel = f"FA3_{cap.replace('-', '_')}_3D_PASS"
    proc = base.cmd([
        *chosen["command_prefix"],
        "--background", "--factory-startup",
        "--python-expr", f"print('{sentinel}')",
    ], 90)
    combined = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0 or sentinel not in combined:
        raise RuntimeError("selected healthy DCC failed capability-specific headless smoke")
    return {
        "application": chosen["display_name"],
        "application_id": chosen["application_id"],
        "packaging": chosen["packaging"],
        "locator": chosen["locator"],
        "headless_smoke": True,
        "dcc_instances": rows,
        "selection_semantics": "QUALIFICATION_PROBE_ONLY_NO_RUNTIME_DEFAULT_NO_SILENT_FALLBACK",
    }


def proof_metric_3d_reconstruction(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    rows, chosen = _healthy_dcc(Path.cwd().resolve())
    script = scope / "metric_3d_reconstruction.py"
    script.write_text(
        "import bpy,bmesh,json\n"
        "mesh=bpy.data.meshes.new('fa3_metric_reconstruction')\n"
        "obj=bpy.data.objects.new('fa3_metric_reconstruction',mesh)\n"
        "bm=bmesh.new()\n"
        "coords=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(1.,1.,0.),"
        "(0.,0.,1.),(1.,0.,1.),(0.,1.,1.),(1.,1.,1.)]\n"
        "verts=[bm.verts.new(co) for co in coords]\n"
        "bm.verts.ensure_lookup_table()\n"
        "bmesh.ops.convex_hull(bm,input=verts,use_existing_faces=False)\n"
        "bm.to_mesh(mesh);bm.free();mesh.update()\n"
        "vv=[v.co.copy() for v in mesh.vertices]\n"
        "volume=0.0\n"
        "for poly in mesh.polygons:\n"
        " p=[vv[i] for i in poly.vertices]\n"
        " for i in range(1,len(p)-1): volume += p[0].dot(p[i].cross(p[i+1]))/6.0\n"
        "dims=[]\n"
        "for axis in range(3):\n"
        " values=[float(v[axis]) for v in vv];dims.append(max(values)-min(values))\n"
        "payload={'vertices':len(mesh.vertices),'faces':len(mesh.polygons),"
        "'volume':abs(float(volume)),'dimensions':dims}\n"
        "print('FA3_METRIC_3D_JSON='+json.dumps(payload,sort_keys=True))\n",
        encoding="utf-8",
    )
    proc = base.cmd([*chosen["command_prefix"], "--background", "--factory-startup", "--python", str(script)], 90)
    combined = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0:
        raise RuntimeError("registered DCC metric reconstruction execution failed")
    match = re.search(r"FA3_METRIC_3D_JSON=(\{.*\})", combined)
    if not match:
        raise RuntimeError("metric 3D reconstruction payload missing")
    payload = json.loads(match.group(1))
    dims = payload.get("dimensions", [])
    if payload.get("vertices", 0) < 8 or payload.get("faces", 0) < 6:
        raise RuntimeError("metric 3D reconstruction topology invalid")
    if abs(float(payload.get("volume", 0.0)) - 1.0) > 1e-6:
        raise RuntimeError("metric 3D reconstruction volume invalid")
    if len(dims) != 3 or any(abs(float(value) - 1.0) > 1e-6 for value in dims):
        raise RuntimeError("metric 3D reconstruction dimensions invalid")
    return {
        "application": chosen["display_name"],
        "application_id": chosen["application_id"],
        "packaging": chosen["packaging"],
        "locator": chosen["locator"],
        "point_count": 8,
        "mesh_vertices": payload["vertices"],
        "mesh_faces": payload["faces"],
        "metric_volume": payload["volume"],
        "metric_dimensions": dims,
        "dcc_instances": rows,
        "selection_semantics": "QUALIFICATION_PROBE_ONLY_NO_RUNTIME_DEFAULT_NO_SILENT_FALLBACK",
    }


base.PRIMITIVES["graphics_3d"] = proof_graphics_3d
base.PRIMITIVES["metric_3d_reconstruction"] = proof_metric_3d_reconstruction


if __name__ == "__main__":
    raise SystemExit(base.main())
