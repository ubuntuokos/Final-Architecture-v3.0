#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CudaParameterIR:
    declaration: str
    name: str
    pointer: bool
    const: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CudaKernelIR:
    name: str
    parameters: tuple[CudaParameterIR, ...]
    body: str
    detected_features: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "parameters": [p.as_dict() for p in self.parameters],
            "body": self.body,
            "detected_features": list(self.detected_features),
        }


@dataclass(frozen=True)
class CudaTranslationUnitIR:
    source_kind: str
    source_sha256: str
    kernels: tuple[CudaKernelIR, ...]
    runtime_calls: tuple[str, ...]
    cuda_identifiers: tuple[str, ...]
    driver_calls: tuple[str, ...]
    math_calls: tuple[str, ...]
    detected_features: tuple[str, ...]
    unsupported_features: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "fa3.cuda-compat-ir.v1",
            "source_kind": self.source_kind,
            "source_sha256": self.source_sha256,
            "kernels": [k.as_dict() for k in self.kernels],
            "runtime_calls": list(self.runtime_calls),
            "cuda_identifiers": list(self.cuda_identifiers),
            "driver_calls": list(self.driver_calls),
            "math_calls": list(self.math_calls),
            "detected_features": list(self.detected_features),
            "unsupported_features": list(self.unsupported_features),
        }
