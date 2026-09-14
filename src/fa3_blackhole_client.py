#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import requests


class BlackholeClientError(RuntimeError):
    pass


class BlackholeCredentialError(BlackholeClientError):
    pass


class BlackholePreconditionError(BlackholeClientError):
    pass


class BlackholeConflictError(BlackholeClientError):
    pass


class BlackholeBridgeClient:
    """Declarative FA3 Blackhole API client.

    The client cannot choose executables, filesystem model paths, CUDA/OMP
    environment variables, owner identity, accelerator ordinals or priority.
    Those are server/HRB policy decisions.
    """

    REQUIRED_FEATURES = ["cuda", "nvenc", "onnxruntime-gpu", "zero-copy"]

    def __init__(
        self,
        base_url: str,
        token_vault_path: str | Path,
        *,
        timeout: tuple[float, float] = (3.0, 30.0),
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = self._load_secure_token(Path(token_vault_path))
        self.timeout = timeout
        self.session = session or requests.Session()

    @staticmethod
    def _load_secure_token(vault_path: Path) -> str:
        try:
            vault = json.loads(vault_path.read_text(encoding="utf-8"))
            token = vault["api_tokens"]["blackhole_bridge"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise BlackholeCredentialError("FA3 Blackhole credential unavailable") from exc
        if not isinstance(token, str) or not token:
            raise BlackholeCredentialError("FA3 Blackhole credential unavailable")
        return token

    def build_request(
        self,
        *,
        input_asset_id: str,
        lease_id: str,
        minimum_tu: float = 1.5,
        model_id: str = "FA3-MODEL-MEDIA-ENHANCER-V3",
        output_profile: str = "1080p-h264",
        request_id: UUID | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": "fa3.blackhole.request.v3",
            "request_id": str(request_id or uuid4()),
            "lease_id": lease_id,
            "requirements": {
                "minimum_tu": float(minimum_tu),
                "required_features": list(self.REQUIRED_FEATURES),
            },
            "pipeline": {
                "operation": "neural_media_enhance",
                "model_id": model_id,
                "input_asset_id": input_asset_id,
                "output_profile": output_profile,
            },
        }

    def submit_zero_copy_job(
        self,
        *,
        input_asset_id: str,
        lease_id: str,
        minimum_tu: float = 1.5,
        model_id: str = "FA3-MODEL-MEDIA-ENHANCER-V3",
        output_profile: str = "1080p-h264",
        request_id: UUID | None = None,
    ) -> dict[str, Any]:
        endpoint = f"{self.base_url}/api/v3/bridge/submit"
        payload = self.build_request(
            input_asset_id=input_asset_id,
            lease_id=lease_id,
            minimum_tu=minimum_tu,
            model_id=model_id,
            output_profile=output_profile,
            request_id=request_id,
        )
        response = self.session.post(
            endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        if response.status_code == 202:
            return response.json()
        if response.status_code == 412:
            raise BlackholePreconditionError(response.text)
        if response.status_code == 409:
            raise BlackholeConflictError(response.text)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise BlackholeClientError(
                f"Blackhole API request failed with HTTP {response.status_code}"
            ) from exc
        raise BlackholeClientError(f"unexpected Blackhole API status: {response.status_code}")
