#!/usr/bin/env python3
from __future__ import annotations
from typing import Any

from fa3_caption_workflows import NATIVE_ACTION_IDS, execute_native_action
from fa3_uaf import CallableProvider, ProviderDescriptor

PROVIDER_ID = "FA3-PROVIDER-CAPTION-NATIVE-001"

def build_native_provider() -> CallableProvider:
    descriptor = ProviderDescriptor(
        provider_id=PROVIDER_ID,
        action_ids=tuple(NATIVE_ACTION_IDS),
        capabilities=("caption-native", "subtitle-authoring", "narration-planning"),
        priority=20,
        state="CONNECTED",
        metadata={
            "architectural_authority": False,
            "provider_selection_authority": False,
            "hardware_vendor_pin": False,
        },
    )
    def handler(request: Any, resource_lease: Any, secret_leases: tuple[Any, ...]) -> dict[str, Any]:
        return execute_native_action(request.action_id, request.arguments)
    return CallableProvider(descriptor, handler)
