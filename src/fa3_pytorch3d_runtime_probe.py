#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    import torch
    import torchvision
    from pytorch3d import _C, __version__ as pytorch3d_version
    from pytorch3d.io import load_obj, load_ply, save_obj, save_ply
    from pytorch3d.loss import chamfer_distance
    from pytorch3d.ops import marching_cubes, sample_points_from_meshes
    from pytorch3d.renderer import PerspectiveCameras
    from pytorch3d.renderer.mesh.rasterize_meshes import rasterize_meshes
    from pytorch3d.renderer.points.pulsar import Renderer as PulsarRenderer
    from pytorch3d.structures import Meshes

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; PyTorch3D current-host admission is fail-closed")
    visible_count = torch.cuda.device_count()
    if visible_count != 1:
        raise RuntimeError(f"expected one HRB-leased visible accelerator, observed {visible_count}")

    device = torch.device("cuda")
    original_device = torch.cuda.current_device()
    properties = torch.cuda.get_device_properties(device)

    verts = torch.tensor(
        [[-0.7, -0.7, 0.1], [0.7, -0.7, 0.1], [0.0, 0.7, 0.1], [0.0, 0.0, -0.7]],
        dtype=torch.float32,
        device=device,
        requires_grad=True,
    )
    faces = torch.tensor(
        [[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]],
        dtype=torch.int64,
        device=device,
    )
    mesh = Meshes(verts=[verts], faces=[faces])
    sampled = sample_points_from_meshes(mesh, num_samples=64)
    target = sampled.detach() + 0.01
    chamfer, _ = chamfer_distance(sampled, target)
    chamfer.backward()
    if not torch.isfinite(chamfer) or verts.grad is None or not torch.isfinite(verts.grad).all():
        raise RuntimeError("non-finite geometry metric or gradient")

    raster = rasterize_meshes(mesh, image_size=32, faces_per_pixel=1)
    pix_to_face = raster[0]
    if pix_to_face.shape != (1, 32, 32, 1) or not torch.isfinite(raster[1]).all():
        raise RuntimeError("mesh rasterization output invalid")

    cameras = PerspectiveCameras(device=device)
    projected = cameras.transform_points(verts.detach()[None])
    if projected.shape != (1, 4, 3) or not torch.isfinite(projected).all():
        raise RuntimeError("camera projection output invalid")

    axis = torch.linspace(-1.0, 1.0, 12, device=device)
    zz, yy, xx = torch.meshgrid(axis, axis, axis, indexing="ij")
    volume = 0.55 - torch.sqrt(xx * xx + yy * yy + zz * zz)
    mc_verts, mc_faces = marching_cubes(volume[None], isolevel=0.0)
    if len(mc_verts[0]) == 0 or len(mc_faces[0]) == 0:
        raise RuntimeError("marching cubes produced empty geometry")

    with tempfile.TemporaryDirectory(prefix="fa3-pytorch3d-") as td:
        tmp = Path(td)
        obj_path = tmp / "mesh.obj"
        ply_path = tmp / "mesh.ply"
        save_obj(obj_path, verts.detach().cpu(), faces.cpu())
        loaded_obj_verts, loaded_obj_faces, _ = load_obj(obj_path, load_textures=False)
        save_ply(ply_path, verts.detach().cpu(), faces.cpu(), ascii=False)
        loaded_ply_verts, loaded_ply_faces = load_ply(ply_path)
        if loaded_obj_verts.shape != (4, 3) or loaded_obj_faces.verts_idx.shape != (4, 3):
            raise RuntimeError("OBJ roundtrip shape mismatch")
        if loaded_ply_verts.shape != (4, 3) or loaded_ply_faces.shape != (4, 3):
            raise RuntimeError("PLY roundtrip shape mismatch")
        interchange = {
            "obj_sha256": sha256_file(obj_path),
            "ply_sha256": sha256_file(ply_path),
        }

    renderer = PulsarRenderer(width=32, height=32, max_num_balls=1).to(device)
    position = torch.tensor([[0.0, 0.0, 2.0]], dtype=torch.float32, device=device, requires_grad=True)
    color = torch.tensor([[0.2, 0.4, 0.7]], dtype=torch.float32, device=device)
    radius = torch.tensor([0.3], dtype=torch.float32, device=device)
    camera = torch.tensor([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 2.0], dtype=torch.float32, device=device)
    rendered_a = renderer(position, color, radius, camera, gamma=1.0e-2, max_depth=10.0)
    rendered_b = renderer(position, color, radius, camera, gamma=1.0e-2, max_depth=10.0)
    if not torch.isfinite(rendered_a).all() or not torch.equal(rendered_a, rendered_b):
        raise RuntimeError("Pulsar output is non-finite or non-deterministic")
    rendered_a.sum().backward()
    if position.grad is None or not torch.isfinite(position.grad).all():
        raise RuntimeError("Pulsar gradient is non-finite")
    if torch.cuda.current_device() != original_device:
        raise RuntimeError("Pulsar did not preserve the caller active device")

    invalid_device_failed_closed = False
    try:
        renderer.to(torch.device("cuda", visible_count))
    except (RuntimeError, AssertionError, ValueError):
        invalid_device_failed_closed = True
    if not invalid_device_failed_closed:
        raise RuntimeError("invalid Pulsar device did not fail closed")
    if torch.cuda.current_device() != original_device:
        raise RuntimeError("invalid-device path changed the caller active device")

    torch.cuda.synchronize(device)
    uuid = getattr(properties, "uuid", None)
    report = {
        "schema": "fa3.pytorch3d-runtime-probe.v1",
        "result": "PASS",
        "pid": os.getpid(),
        "versions": {
            "python_runtime": os.sys.version.split()[0],
            "torch": torch.__version__,
            "torchvision": torchvision.__version__,
            "pytorch3d": pytorch3d_version,
            "torch_compiled_cuda": torch.version.cuda,
        },
        "accelerator": {
            "visible_count": visible_count,
            "name": properties.name,
            "uuid": str(uuid) if uuid is not None else None,
            "compute_capability": f"{properties.major}.{properties.minor}",
        },
        "extension": {
            "loaded": True,
            "pulsar_symbol": hasattr(_C, "PulsarRenderer"),
        },
        "checks": {
            "mesh_sampling": list(sampled.shape),
            "mesh_rasterization": list(pix_to_face.shape),
            "camera_projection": list(projected.shape),
            "chamfer": float(chamfer.detach().cpu()),
            "gradient_finite": True,
            "marching_cubes_vertices": len(mc_verts[0]),
            "marching_cubes_faces": len(mc_faces[0]),
            "obj_ply_roundtrip": interchange,
            "pulsar_render_shape": list(rendered_a.shape),
            "pulsar_deterministic": True,
            "pulsar_invalid_device_fail_closed": True,
            "pulsar_caller_device_preserved": True,
        },
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
