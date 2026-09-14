#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
GPU_UUID_RE = re.compile(r"^GPU-[A-Fa-f0-9-]{8,}$")
PCI_BDF_RE = re.compile(r"^[0-9A-Fa-f]{4}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}\.[0-7]$")
DIGEST_IMAGE_RE = re.compile(r"^[^\s]+@sha256:[A-Fa-f0-9]{64}$")


class HRBProjectionError(RuntimeError):
    pass


def _parse_ts(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise HRBProjectionError(f"invalid RFC3339 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise HRBProjectionError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AcceleratorLease:
    lease_id: str
    holder: str
    device_uuid: str
    pci_bdf: str
    expires_at: datetime

    @property
    def cdi_selector(self) -> str:
        return f"nvidia.com/gpu={self.device_uuid}"


def validate_placement_receipt(
    receipt: Mapping[str, Any],
    *,
    expected_holder: str,
    at: datetime | None = None,
) -> AcceleratorLease:
    """Semantically validate an HRB PlacementReceipt.

    This deliberately does not authenticate the receipt. Production materialization
    MUST first invoke the HRB-owned verifier command. This module is a projection,
    never a parallel resource authority.
    """
    if receipt.get("authority_id") != AUTHORITY_ID:
        raise HRBProjectionError("receipt was not issued under the canonical HRB authority")
    if receipt.get("receipt_type") not in {"PlacementReceipt", "AcceleratorAssignmentReceipt"}:
        raise HRBProjectionError("unsupported HRB receipt_type")
    if receipt.get("lease_state") != "ACTIVE":
        raise HRBProjectionError("HRB lease is not ACTIVE")

    lease_id = str(receipt.get("lease_id", "")).strip()
    holder = str(receipt.get("holder", "")).strip()
    if not lease_id:
        raise HRBProjectionError("lease_id is required")
    if holder != expected_holder:
        raise HRBProjectionError(
            f"lease holder mismatch: expected {expected_holder!r}, got {holder!r}"
        )

    assignment = receipt.get("accelerator_assignment")
    if not isinstance(assignment, Mapping):
        raise HRBProjectionError("accelerator_assignment object is required")

    uuid = str(assignment.get("device_uuid", "")).strip()
    bdf = str(assignment.get("pci_bdf", "")).strip()
    runtime_index = assignment.get("runtime_index")

    if uuid.lower() == "all" or uuid.isdigit():
        raise HRBProjectionError("GPU ordinal/all is forbidden as canonical accelerator identity")
    if not GPU_UUID_RE.fullmatch(uuid):
        raise HRBProjectionError("valid NVIDIA device_uuid is required")
    if not PCI_BDF_RE.fullmatch(bdf):
        raise HRBProjectionError("valid PCI BDF is required")
    if runtime_index is not None and str(runtime_index) == uuid:
        raise HRBProjectionError("runtime index cannot replace device_uuid")

    not_before = _parse_ts(str(receipt.get("not_before", "")))
    expires_at = _parse_ts(str(receipt.get("expires_at", "")))
    current = (at or _now()).astimezone(timezone.utc)
    if current < not_before:
        raise HRBProjectionError("HRB lease is not active yet")
    if current >= expires_at:
        raise HRBProjectionError("HRB lease has expired")
    if expires_at <= not_before:
        raise HRBProjectionError("HRB lease time window is invalid")

    return AcceleratorLease(
        lease_id=lease_id,
        holder=holder,
        device_uuid=uuid,
        pci_bdf=bdf,
        expires_at=expires_at,
    )


def verify_receipt_with_hrb(receipt_path: Path, verifier_command: str) -> None:
    """Invoke an HRB-owned verifier before production projection."""
    argv = shlex.split(verifier_command)
    if not argv:
        raise HRBProjectionError("HRB receipt verifier command is empty")
    result = subprocess.run(
        [*argv, str(receipt_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-1000:]
        raise HRBProjectionError(
            f"HRB receipt authentication failed (exit={result.returncode}): {detail}"
        )


def require_digest_image(image: str, field: str) -> str:
    value = image.strip()
    if not DIGEST_IMAGE_RE.fullmatch(value):
        raise HRBProjectionError(f"{field} must be pinned by sha256 digest")
    return value


def materialize_comfyui_quadlet(
    *,
    template_path: Path,
    output_path: Path,
    receipt_path: Path,
    comfyui_image: str,
    hrb_verifier_command: str,
    expected_holder: str = "fa3-blackhole-comfyui-worker",
) -> dict[str, Any]:
    verify_receipt_with_hrb(receipt_path, hrb_verifier_command)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    lease = validate_placement_receipt(receipt, expected_holder=expected_holder)
    image = require_digest_image(comfyui_image, "ComfyUI image")

    template = template_path.read_text(encoding="utf-8")
    required = {"@FA3_CDI_DEVICE@", "@FA3_COMFYUI_IMAGE@", "@FA3_HRB_LEASE_ID@"}
    missing = [token for token in required if token not in template]
    if missing:
        raise HRBProjectionError(f"Quadlet template is missing placeholders: {missing}")

    rendered = (
        template.replace("@FA3_CDI_DEVICE@", lease.cdi_selector)
        .replace("@FA3_COMFYUI_IMAGE@", image)
        .replace("@FA3_HRB_LEASE_ID@", lease.lease_id)
    )
    if "nvidia.com/gpu=all" in rendered or "NVIDIA_VISIBLE_DEVICES=all" in rendered:
        raise HRBProjectionError("unscoped GPU access is forbidden")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{output_path.name}.", dir=str(output_path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            if not rendered.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, output_path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise

    return {
        "status": "PASS",
        "authority_id": AUTHORITY_ID,
        "lease_id": lease.lease_id,
        "holder": lease.holder,
        "device_uuid": lease.device_uuid,
        "pci_bdf": lease.pci_bdf,
        "cdi_selector": lease.cdi_selector,
        "expires_at": lease.expires_at.isoformat().replace("+00:00", "Z"),
        "output": str(output_path),
    }


def load_image_manifest(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "fa3.blackhole-image-manifest.v1":
        raise HRBProjectionError("unsupported Blackhole image manifest schema")
    result: dict[str, str] = {}
    for field in ("blackhole_api", "litellm", "comfyui", "egress_gateway"):
        result[field] = require_digest_image(str(data.get(field, "")), field)
    return result


def _atomic_render(template: Path, output: Path, replacements: Mapping[str, str]) -> None:
    rendered = template.read_text(encoding="utf-8")
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    leftovers = sorted(set(re.findall(r"@FA3_[A-Z0-9_]+@", rendered)))
    if leftovers:
        raise HRBProjectionError(
            f"unresolved production placeholders in {template.name}: {leftovers}"
        )
    if ":latest" in rendered or "NVIDIA_VISIBLE_DEVICES=all" in rendered:
        raise HRBProjectionError(f"forbidden production configuration in {template.name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{output.name}.", dir=str(output.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            if not rendered.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, output)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def materialize_blackhole_quadlet_bundle(
    *,
    source_dir: Path,
    output_dir: Path,
    receipt_path: Path,
    image_manifest_path: Path,
    hrb_verifier_command: str,
    expected_holder: str = "fa3-blackhole-comfyui-worker",
) -> dict[str, Any]:
    verify_receipt_with_hrb(receipt_path, hrb_verifier_command)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    lease = validate_placement_receipt(receipt, expected_holder=expected_holder)
    images = load_image_manifest(image_manifest_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    static_units = [
        "fa3-internal.network",
        "fa3-egress.network",
        "fa3-media-storage.volume",
        "fa3-evidence-registry.volume",
        "fa3-comfyui-models.volume",
    ]
    for name in static_units:
        src = source_dir / name
        if not src.is_file():
            raise HRBProjectionError(f"missing Quadlet source unit: {src}")
        _atomic_render(src, output_dir / name, {})

    mappings = {
        "fa3-blackhole-api.container.in": {
            "@FA3_BLACKHOLE_IMAGE@": images["blackhole_api"],
        },
        "fa3-litellm.container.in": {
            "@FA3_LITELLM_IMAGE@": images["litellm"],
        },
        "fa3-egress-gateway.container.in": {
            "@FA3_EGRESS_GATEWAY_IMAGE@": images["egress_gateway"],
        },
        "fa3-comfyui-worker.container.in": {
            "@FA3_COMFYUI_IMAGE@": images["comfyui"],
            "@FA3_CDI_DEVICE@": lease.cdi_selector,
            "@FA3_HRB_LEASE_ID@": lease.lease_id,
        },
    }
    for template_name, replacements in mappings.items():
        src = source_dir / template_name
        if not src.is_file():
            raise HRBProjectionError(f"missing Quadlet template: {src}")
        output_name = template_name.removesuffix(".in")
        _atomic_render(src, output_dir / output_name, replacements)

    receipt_out = {
        "schema": "fa3.blackhole-quadlet-materialization-receipt.v1",
        "status": "PASS",
        "authority_id": AUTHORITY_ID,
        "lease_id": lease.lease_id,
        "holder": lease.holder,
        "device_uuid": lease.device_uuid,
        "pci_bdf": lease.pci_bdf,
        "cdi_selector": lease.cdi_selector,
        "expires_at": lease.expires_at.isoformat().replace("+00:00", "Z"),
        "images": images,
        "output_dir": str(output_dir),
    }
    receipt_file = output_dir / "fa3-blackhole-materialization-receipt.json"
    _atomic_render(
        _write_temp_json_template(output_dir, receipt_out),
        receipt_file,
        {},
    )
    (output_dir / ".materialization-receipt.template").unlink(missing_ok=True)
    return receipt_out


def _write_temp_json_template(output_dir: Path, value: Mapping[str, Any]) -> Path:
    path = output_dir / ".materialization-receipt.template"
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 HRB -> NVIDIA CDI / Quadlet projection")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--source-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--image-manifest")
    parser.add_argument("--template")
    parser.add_argument("--output")
    parser.add_argument("--comfyui-image")
    parser.add_argument(
        "--hrb-verifier-command",
        default=os.environ.get("FA3_HRB_RECEIPT_VERIFY_COMMAND", ""),
    )
    parser.add_argument("--expected-holder", default="fa3-blackhole-comfyui-worker")
    args = parser.parse_args()

    if not args.hrb_verifier_command:
        raise SystemExit("FAIL-CLOSED: FA3_HRB_RECEIPT_VERIFY_COMMAND is required")

    if args.source_dir and args.output_dir and args.image_manifest:
        result = materialize_blackhole_quadlet_bundle(
            source_dir=Path(args.source_dir),
            output_dir=Path(args.output_dir),
            receipt_path=Path(args.receipt),
            image_manifest_path=Path(args.image_manifest),
            hrb_verifier_command=args.hrb_verifier_command,
            expected_holder=args.expected_holder,
        )
    elif args.template and args.output and args.comfyui_image:
        result = materialize_comfyui_quadlet(
            template_path=Path(args.template),
            output_path=Path(args.output),
            receipt_path=Path(args.receipt),
            comfyui_image=args.comfyui_image,
            hrb_verifier_command=args.hrb_verifier_command,
            expected_holder=args.expected_holder,
        )
    else:
        raise SystemExit(
            "FAIL-CLOSED: supply either bundle args (--source-dir/--output-dir/--image-manifest) "
            "or single-worker args (--template/--output/--comfyui-image)"
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
