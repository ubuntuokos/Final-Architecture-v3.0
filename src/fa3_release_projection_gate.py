#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

PROJECTION_ID = "FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30"
PROJECTION_PATH = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
DECISION_PATH = "canonical/decisions/FA3-DEC-UNIFIED-POST-V3.0.11-PROJECTION-2026-08-30.json"
BASE_RELEASE = "2026-08-23/v3.0.11"
BASE_COMMIT = "1d8a3ffaa2b4d11abcc6003250ff66b4798eef60"
CAPABILITY_COUNT = 143
EXPECTED_SOURCE_GRAPH_SHA256 = "0418528b52fd9a29d993fc69c1ea508f57cd527d96e234d738c6b8fc553c4f16"
EXPECTED_SOURCE_GRAPH_NODES = 1615
EXPECTED_SOURCE_GRAPH_EDGES = 6144
SNAPSHOT_SEMANTICS = "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR"
KANBOARD_PROVIDER_ID = "FA3-PROVIDER-KANBOARD-001"
KANBOARD_GATE_ID = "FA3-KANBOARD-GATESET-001"
KANBOARD_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-KANBOARD-001.json"
KANBOARD_DECISION_PATH = "canonical/decisions/FA3-DEC-KANBOARD-2026-08-30.json"
KANBOARD_REFERENCE_PATH = "canonical/references/FA3-KANBOARD-UPSTREAM-REFERENCE-2026-08-30.json"
KANBOARD_EVIDENCE_PATH = "evidence/reference/kanboard-ci-2026-08-30.json"
KANBOARD_ENFORCEMENT_PATH = "canonical/kanboard-enforcement.json"
KANBOARD_GATE_PATH = "src/fa3_kanboard_gate.py"
KANBOARD_TEST_PATH = "tests/test_kanboard_gate.py"
KANBOARD_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED"
PRESENTON_PROVIDER_ID = "FA3-PROVIDER-PRESENTON-001"
PRESENTON_GATE_ID = "FA3-PRESENTON-GATESET-001"
PRESENTON_CONTRACT_ID = "FA3-PRESENTON-CONTRACTS-001"
PRESENTON_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-PRESENTON-001.json"
PRESENTON_DECISION_PATH = "canonical/decisions/FA3-DEC-PRESENTON-2026-08-30.json"
PRESENTON_REFERENCE_PATH = "canonical/references/FA3-PRESENTON-UPSTREAM-REFERENCE-2026-08-30.json"
PRESENTON_EVIDENCE_PATH = "evidence/reference/presenton-provider-ci-2026-08-30.json"
PRESENTON_CONTRACT_PATH = "canonical/contracts/FA3-PRESENTON-CONTRACTS-001.json"
PRESENTON_ENFORCEMENT_PATH = "canonical/presenton-enforcement.json"
PRESENTON_GATE_PATH = "src/fa3_presenton_gate.py"
PRESENTON_TEST_PATH = "tests/test_presenton_gate.py"
PRESENTON_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CURRENT_HOST_PENDING"
AUTOGPT_PROVIDER_ID = "FA3-PROVIDER-AUTOGPT-001"
AUTOGPT_GATE_ID = "FA3-AUTOGPT-GATESET-001"
AUTOGPT_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-AUTOGPT-001.json"
AUTOGPT_DECISION_PATH = "canonical/decisions/FA3-DEC-AUTOGPT-2026-08-30.json"
AUTOGPT_REFERENCE_PATH = "canonical/references/FA3-AUTOGPT-UPSTREAM-REFERENCE-2026-08-30.json"
AUTOGPT_EVIDENCE_PATH = "evidence/reference/autogpt-ci-2026-08-30.json"
AUTOGPT_RECONCILIATION_EVIDENCE_PATH = "evidence/reference/autogpt-global-reconciliation-ci-2026-08-30.json"
AUTOGPT_ENFORCEMENT_PATH = "canonical/autogpt-enforcement.json"
AUTOGPT_ADMISSION_PATH = "canonical/autogpt-runtime-admission.json"
AUTOGPT_GATE_PATH = "src/fa3_autogpt_gate.py"
AUTOGPT_TEST_PATH = "tests/test_autogpt_gate.py"
AUTOGPT_CAPABILITY_ID = "CAP-028"
AUTOGPT_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_RUNTIME_NOT_ADMITTED"
DAC_PROFILE_ID = "FA3-AGENT-EXEC-001"
DAC_CONTRACT_ID = "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
DAC_RUNTIME_ID = "FA3-DEVELOPER-AGENT-COORDINATION-REF-RUNTIME-001"
DAC_GATE_ID = "FA3-DEVELOPER-AGENT-COORDINATION-GATESET-001"
DAC_CONTRACT_PATH = "canonical/contracts/FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001.json"
DAC_CONFORMANCE_PATH = "canonical/FA3-DEVELOPER-AGENT-COORDINATION-RUNTIME-CONFORMANCE-001.json"
DAC_DECISION_PATH = "canonical/decisions/FA3-DEC-DEVELOPER-AGENT-COORDINATION-2026-08-30.json"
DAC_ENFORCEMENT_PATH = "canonical/developer-agent-coordination-enforcement.json"
DAC_RUNTIME_PATH = "src/fa3_developer_agent_coordination.py"
DAC_GATE_PATH = "src/fa3_developer_agent_coordination_gate.py"
DAC_TEST_PATH = "tests/test_developer_agent_coordination.py"
DAC_COLLECTOR_PATH = "evidence/collect-developer-agent-coordination-e2e.py"
DAC_EXAMPLE_PATH = "examples/developer-agent-coordination-request.json"
DAC_RUNNER_PATH = "bin/fa3-developer-agent-coordination-e2e"
DAC_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_E2E_REQUIRED"
CODEX_PROVIDER_ID = "FA3-PROVIDER-CODEX-001"
CODEX_GATE_ID = "FA3-CODEX-GATESET-001"
CODEX_CONTRACT_ID = "FA3-CODEX-ADAPTER-CONTRACTS-001"
CODEX_ADMISSION_ID = "FA3-CODEX-RUNTIME-ADMISSION-001"
CODEX_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-CODEX-001.json"
CODEX_REFERENCE_PATH = "canonical/references/FA3-CODEX-UPSTREAM-REFERENCE-2026-08-31.json"
CODEX_CONTRACT_PATH = "canonical/contracts/FA3-CODEX-ADAPTER-CONTRACTS-001.json"
CODEX_ADMISSION_PATH = "canonical/codex-runtime-admission.json"
CODEX_ENFORCEMENT_PATH = "canonical/codex-enforcement.json"
CODEX_DECISION_PATH = "canonical/decisions/FA3-DEC-CODEX-ADAPTER-2026-08-31.json"
CODEX_EVIDENCE_PATH = "evidence/reference/codex-adapter-ci-2026-08-31.json"
CODEX_ADAPTER_PATH = "src/fa3_codex_adapter.py"
CODEX_GATE_PATH = "src/fa3_codex_gate.py"
CODEX_TEST_PATH = "tests/test_codex_adapter.py"
CODEX_COLLECTOR_PATH = "evidence/collect-codex-current-host.py"
CODEX_BOOTSTRAP_PATH = "bin/fa3-codex-bootstrap.sh"
CODEX_RUNNER_PATH = "bin/fa3-codex-current-host.sh"
CODEX_WORKFLOW_PATH = ".github/workflows/fa3-codex-current-host.yml"
CODEX_RUNBOOK_PATH = "docs/codex-current-host.md"
CODEX_EXAMPLE_PATH = "examples/codex-delegated-agent-request.json"
CODEX_CAPABILITY_ID = "CAP-028"
CODEX_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CURRENT_HOST_PENDING"
AISEC_PROFILE_ID = "FA3-AI-SEC-VALIDATION-001"
AISEC_CONTRACT_ID = "FA3-AI-SECURITY-VALIDATION-CONTRACTS-001"
AISEC_PROVIDER_ID = "FA3-PROVIDER-AI-INFRA-GUARD-001"
AISEC_GATE_ID = "FA3-AI-INFRA-GUARD-GATESET-001"
AISEC_PROFILE_PATH = "canonical/profiles/FA3-AI-SEC-VALIDATION-001.json"
AISEC_CONTRACT_PATH = "canonical/contracts/FA3-AI-SECURITY-VALIDATION-CONTRACTS-001.json"
AISEC_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-AI-INFRA-GUARD-001.json"
AISEC_DECISION_PATH = "canonical/decisions/FA3-DEC-AI-INFRA-GUARD-2026-08-30.json"
AISEC_REFERENCE_PATH = "canonical/references/FA3-AI-INFRA-GUARD-UPSTREAM-REFERENCE-2026-08-31.json"
AISEC_EVIDENCE_PATH = "evidence/reference/ai-infra-guard-ci-2026-08-31.json"
AISEC_ENFORCEMENT_PATH = "canonical/ai-infra-guard-enforcement.json"
AISEC_GATE_PATH = "src/fa3_ai_infra_guard_gate.py"
AISEC_TEST_PATH = "tests/test_ai_infra_guard_gate.py"
AISEC_CAPABILITY_IDS = ("CAP-003", "CAP-005", "CAP-007", "CAP-011")
AISEC_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_PASS_CURRENT_HOST_PENDING"
AISEC_ADMISSION_PATH = "canonical/ai-infra-guard-runtime-admission.json"
AISEC_ADAPTER_PATH = "src/fa3_ai_infra_guard_adapter.py"
AISEC_COLLECTOR_PATH = "evidence/collect-ai-infra-guard-current-host.py"
AISEC_BOOTSTRAP_PATH = "bin/fa3-ai-infra-guard-bootstrap.sh"
AISEC_RUNNER_PATH = "bin/fa3-ai-infra-guard-current-host.sh"
AISEC_WORKFLOW_PATH = ".github/workflows/fa3-ai-infra-guard-current-host.yml"

HYBRID_PROFILE_ID = "FA3-HYBRID-EDITORIAL-001"
HYBRID_CONTRACT_ID = "FA3-HYBRID-EDITORIAL-CONTRACTS-001"
HYBRID_KRITA_PROVIDER_ID = "FA3-PROVIDER-KRITA-001"
HYBRID_KDENLIVE_PROVIDER_ID = "FA3-PROVIDER-KDENLIVE-001"
HYBRID_GATE_ID = "FA3-GATE-HYBRID-EDITORIAL-001"
HYBRID_GATESET_ID = "FA3-HYBRID-EDITORIAL-GATESET-001"
HYBRID_DECISION_ID = "FA3-DEC-HYBRID-EDITORIAL-2026-08-31"
HYBRID_PROFILE_PATH = "canonical/profiles/FA3-HYBRID-EDITORIAL-001.json"
HYBRID_CONTRACT_PATH = "canonical/contracts/FA3-HYBRID-EDITORIAL-CONTRACTS-001.json"
HYBRID_KRITA_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-KRITA-001.json"
HYBRID_KDENLIVE_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-KDENLIVE-001.json"
HYBRID_DECISION_PATH = "canonical/decisions/FA3-DEC-HYBRID-EDITORIAL-2026-08-31.json"
HYBRID_GATE_RECORD_PATH = "canonical/FA3-GATE-HYBRID-EDITORIAL-001.json"
HYBRID_ENFORCEMENT_PATH = "canonical/hybrid-editorial-enforcement.json"
HYBRID_EVIDENCE_PATH = "evidence/reference/hybrid-editorial-ci-2026-08-31.json"
HYBRID_REFERENCE_RUNTIME_PATH = "src/fa3_hybrid_editorial_reference.py"
HYBRID_GATE_PATH = "src/fa3_hybrid_editorial_gate.py"
HYBRID_KDENLIVE_GATE_PATH = "src/fa3_kdenlive_editorial_gate.py"
HYBRID_GLOBAL_ENFORCE_PATH = "src/fa3_enforce.py"
HYBRID_TEST_PATH = "tests/test_hybrid_editorial_gate.py"
HYBRID_COLLECTOR_PATH = "evidence/collect-hybrid-editorial-reference-e2e.py"
HYBRID_EXAMPLE_PATH = "examples/hybrid-editorial-reference-request.json"
HYBRID_WORKFLOW_PATH = ".github/workflows/fa3-permanent-enforcement.yml"
HYBRID_CAPABILITY_IDS = ("CAP-016", "CAP-017", "CAP-121", "CAP-126")
HYBRID_RECONCILIATION_STATUS = (
    "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_E2E_PASS_CURRENT_HOST_PENDING"
)

MARKETING_PROFILE_ID = "FA3-MARKETING-001"
MARKETING_CONTRACT_ID = "FA3-MARKETING-CONTRACTS-001"
MARKETING_I18N_ID = "FA3-MARKETING-I18N-001"
MARKETING_GATE_ID = "FA3-GATE-MARKETING-001"
MARKETING_GATESET_ID = "FA3-MARKETING-GATESET-001"
MARKETING_DECISION_ID = "FA3-DEC-MARKETING-2026-08-31"
MARKETING_PROFILE_PATH = "canonical/profiles/FA3-MARKETING-001.json"
MARKETING_CONTRACT_PATH = "canonical/contracts/FA3-MARKETING-CONTRACTS-001.json"
MARKETING_I18N_PATH = "canonical/FA3-MARKETING-I18N-001.json"
MARKETING_DECISION_PATH = "canonical/decisions/FA3-DEC-MARKETING-2026-08-31.json"
MARKETING_GATE_RECORD_PATH = "canonical/FA3-GATE-MARKETING-001.json"
MARKETING_ENFORCEMENT_PATH = "canonical/marketing-enforcement.json"
MARKETING_REFERENCE_PATH = "canonical/references/FA3-MARKETING-UPSTREAM-REFERENCE-2026-08-31.json"
MARKETING_EVIDENCE_PATH = "evidence/reference/marketing-ci-2026-08-31.json"
MARKETING_REFERENCE_RUNTIME_PATH = "src/fa3_marketing_reference.py"
MARKETING_GATE_PATH = "src/fa3_marketing_gate.py"
MARKETING_TEST_PATH = "tests/test_marketing_gate.py"
MARKETING_COLLECTOR_PATH = "evidence/collect-marketing-reference-e2e.py"
MARKETING_EXAMPLE_PATH = "examples/marketing-reference-request.json"
MARKETING_WORKFLOW_PATH = ".github/workflows/fa3-permanent-enforcement.yml"
MARKETING_PROVIDER_IDS = ["FA3-PROVIDER-MAUTIC-001", "FA3-PROVIDER-TWENTY-001", "FA3-PROVIDER-LISTMONK-001", "FA3-PROVIDER-DITTOFEED-001", "FA3-PROVIDER-POSTHOG-001"]
MARKETING_PROVIDER_PATHS = tuple(
    f"canonical/providers/{provider_id}.json"
    for provider_id in MARKETING_PROVIDER_IDS
)
MARKETING_CAPABILITY_IDS = ["CAP-003", "CAP-004", "CAP-010", "CAP-011", "CAP-018", "CAP-019", "CAP-040", "CAP-049", "CAP-103", "CAP-112", "CAP-125"]
MARKETING_RECONCILIATION_STATUS = (
    "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_E2E_PASS_CURRENT_HOST_PENDING"
)

STABILITY_SGM_PROVIDER_ID = "FA3-PROVIDER-STABILITY-SGM-001"
STABILITY_SGM_CONTRACT_ID = "FA3-GENERATIVE-PIPELINE-MULTIVIEW-CONTRACTS-001"
STABILITY_SGM_GATE_ID = "FA3-STABILITY-SGM-GATESET-001"
STABILITY_SGM_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json"
STABILITY_SGM_CONTRACT_PATH = "canonical/contracts/FA3-GENERATIVE-PIPELINE-MULTIVIEW-CONTRACTS-001.json"
STABILITY_SGM_DECISION_PATH = "canonical/decisions/FA3-DEC-STABILITY-SGM-2026-09-01.json"
STABILITY_SGM_REFERENCE_PATH = "canonical/references/FA3-STABILITY-SGM-UPSTREAM-REFERENCE-2026-09-01.json"
STABILITY_SGM_GATE_RECORD_PATH = "canonical/FA3-GATE-STABILITY-SGM-001.json"
STABILITY_SGM_ENFORCEMENT_PATH = "canonical/stability-sgm-enforcement.json"
STABILITY_SGM_EVIDENCE_PATH = "evidence/reference/stability-sgm-ci-2026-09-01.json"
STABILITY_SGM_GATE_PATH = "src/fa3_stability_sgm_gate.py"
STABILITY_SGM_TEST_PATH = "tests/test_stability_sgm_gate.py"
STABILITY_SGM_RECONCILIATION_STATUS = (
    "CANONICAL_MATERIALIZED_EXECUTABLE_REFERENCE_PASS_CURRENT_HOST_PENDING"
)

OPENCUT_PROFILE_ID = "FA3-PROGRAMMABLE-VIDEO-EDITING-001"
OPENCUT_CONTRACT_ID = "FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001"
OPENCUT_PROVIDER_ID = "FA3-PROVIDER-OPENCUT-001"
OPENCUT_DECISION_ID = "FA3-DEC-OPENCUT-PROGRAMMABLE-EDITOR-2026-09-01"
OPENCUT_GATE_ID = "FA3-OPENCUT-GATESET-001"
OPENCUT_PROFILE_PATH = "canonical/profiles/FA3-PROGRAMMABLE-VIDEO-EDITING-001.json"
OPENCUT_CONTRACT_PATH = "canonical/contracts/FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001.json"
OPENCUT_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-OPENCUT-001.json"
OPENCUT_DECISION_PATH = "canonical/decisions/FA3-DEC-OPENCUT-PROGRAMMABLE-EDITOR-2026-09-01.json"
OPENCUT_REFERENCE_PATH = "canonical/references/FA3-OPENCUT-UPSTREAM-REFERENCE-2026-09-01.json"
OPENCUT_GATE_RECORD_PATH = "canonical/FA3-GATE-OPENCUT-001.json"
OPENCUT_ENFORCEMENT_PATH = "canonical/opencut-enforcement.json"
OPENCUT_ADMISSION_PATH = "canonical/opencut-runtime-admission.json"
OPENCUT_EVIDENCE_PATH = "evidence/reference/opencut-ci-2026-09-01.json"
OPENCUT_GATE_PATH = "src/fa3_opencut_gate.py"
OPENCUT_TEST_PATH = "tests/test_opencut_gate.py"
OPENCUT_CAPABILITY_IDS = ("CAP-121", "CAP-126")
OPENCUT_RUNTIME_STATUS = "NOT_ADMITTED_UPSTREAM_INTERFACES_UNSTABLE"
OPENCUT_RECONCILIATION_STATUS = (
    "GLOBAL_PROJECTION_RECONCILED_CANONICAL_REFERENCE_PASS_RUNTIME_NOT_ADMITTED"
)

OPENHANDS_PROVIDER_ID = "FA3-PROVIDER-OPENHANDS-001"
OPENHANDS_CONTRACT_ID = "FA3-OPENHANDS-DEVELOPER-EXECUTION-CONTRACTS-001"
OPENHANDS_DECISION_ID = "FA3-DEC-OPENHANDS-2026-09-01"
OPENHANDS_GATE_ID = "FA3-OPENHANDS-GATESET-001"
OPENHANDS_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-OPENHANDS-001.json"
OPENHANDS_CONTRACT_PATH = "canonical/contracts/FA3-OPENHANDS-DEVELOPER-EXECUTION-CONTRACTS-001.json"
OPENHANDS_DECISION_PATH = "canonical/decisions/FA3-DEC-OPENHANDS-2026-09-01.json"
OPENHANDS_REFERENCE_PATH = "canonical/references/FA3-OPENHANDS-UPSTREAM-REFERENCE-2026-09-01.json"
OPENHANDS_GATE_RECORD_PATH = "canonical/FA3-GATE-OPENHANDS-001.json"
OPENHANDS_ENFORCEMENT_PATH = "canonical/openhands-enforcement.json"
OPENHANDS_ADMISSION_PATH = "canonical/openhands-runtime-admission.json"
OPENHANDS_EVIDENCE_PATH = "evidence/reference/openhands-ci-2026-09-01.json"
OPENHANDS_GATE_PATH = "src/fa3_openhands_gate.py"
OPENHANDS_TEST_PATH = "tests/test_openhands_gate.py"
OPENHANDS_CAPABILITY_ID = "CAP-028"
OPENHANDS_RUNTIME_STATUS = "NOT_PROMOTED_REFERENCE_ONLY"
OPENHANDS_RECONCILIATION_STATUS = (
    "GLOBAL_PROJECTION_RECONCILED_CANONICAL_REFERENCE_PASS_CURRENT_HOST_PENDING"
)

LOOP_PROFILE_ID = "FA3-CLOSED-LOOP-AGENT-OPERATIONS-001"
LOOP_CONTRACT_ID = "FA3-CLOSED-LOOP-AGENT-OPERATIONS-CONTRACTS-001"
LOOP_PROVIDER_ID = "FA3-PROVIDER-LOOP-ENGINEERING-001"
LOOP_DECISION_ID = "FA3-DEC-LOOP-ENGINEERING-2026-09-03"
LOOP_GATE_ID = "FA3-LOOP-ENGINEERING-GATESET-001"
LOOP_PROFILE_PATH = "canonical/profiles/FA3-CLOSED-LOOP-AGENT-OPERATIONS-001.json"
LOOP_CONTRACT_PATH = "canonical/contracts/FA3-CLOSED-LOOP-AGENT-OPERATIONS-CONTRACTS-001.json"
LOOP_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-LOOP-ENGINEERING-001.json"
LOOP_DECISION_PATH = "canonical/decisions/FA3-DEC-LOOP-ENGINEERING-2026-09-03.json"
LOOP_REFERENCE_PATH = "canonical/references/FA3-LOOP-ENGINEERING-UPSTREAM-REFERENCE-2026-09-03.json"
LOOP_GATE_RECORD_PATH = "canonical/FA3-GATE-LOOP-ENGINEERING-001.json"
LOOP_ENFORCEMENT_PATH = "canonical/loop-engineering-enforcement.json"
LOOP_ADMISSION_PATH = "canonical/loop-engineering-runtime-admission.json"
LOOP_EVIDENCE_PATH = "evidence/reference/loop-engineering-ci-2026-09-03.json"
LOOP_REFERENCE_IMPL_PATH = "src/fa3_closed_loop_agent_ops_reference.py"
LOOP_GATE_PATH = "src/fa3_loop_engineering_gate.py"
LOOP_TEST_PATH = "tests/test_loop_engineering_gate.py"
LOOP_CAPABILITY_ID = "CAP-028"
LOOP_RUNTIME_STATUS = "REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY"
LOOP_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CANONICAL_REFERENCE_PASS_RUNTIME_NOT_REQUIRED"
LOOP_UPSTREAM_PIN = "714f1fdf6ea111f27207de6908547c2a155b270c"

TDAI_PROVIDER_ID = "FA3-PROVIDER-TENCENTDB-AGENT-MEMORY-001"
TDAI_CONTRACT_ID = "FA3-AGENT-MEMORY-ASSET-GOVERNANCE-CONTRACTS-001"
TDAI_DECISION_ID = "FA3-DEC-TENCENTDB-AGENT-MEMORY-2026-09-03"
TDAI_GATE_ID = "FA3-TENCENTDB-AGENT-MEMORY-GATESET-001"
TDAI_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-TENCENTDB-AGENT-MEMORY-001.json"
TDAI_CONTRACT_PATH = "canonical/contracts/FA3-AGENT-MEMORY-ASSET-GOVERNANCE-CONTRACTS-001.json"
TDAI_DECISION_PATH = "canonical/decisions/FA3-DEC-TENCENTDB-AGENT-MEMORY-2026-09-03.json"
TDAI_REFERENCE_PATH = "canonical/references/FA3-TENCENTDB-AGENT-MEMORY-UPSTREAM-REFERENCE-2026-09-03.json"
TDAI_GATE_RECORD_PATH = "canonical/FA3-GATE-TENCENTDB-AGENT-MEMORY-001.json"
TDAI_ENFORCEMENT_PATH = "canonical/tencentdb-agent-memory-enforcement.json"
TDAI_ADMISSION_PATH = "canonical/tencentdb-agent-memory-runtime-admission.json"
TDAI_EVIDENCE_PATH = "evidence/reference/tencentdb-agent-memory-ci-2026-09-03.json"
TDAI_GATE_PATH = "src/fa3_tencentdb_agent_memory_gate.py"
TDAI_TEST_PATH = "tests/test_tencentdb_agent_memory_gate.py"
TDAI_CAPABILITY_IDS = ("CAP-010", "CAP-021", "CAP-023", "CAP-094", "CAP-102", "CAP-110", "CAP-139",)
TDAI_RUNTIME_STATUS = "NOT_ADMITTED_PENDING_SECURITY_LICENSE_CURRENT_HOST"
TDAI_RECONCILIATION_STATUS = "CANONICAL_MATERIALIZED_REFERENCE_PASS_SECURITY_LICENSE_CURRENT_HOST_BLOCKED"

VOICE_PROFILE_ID = "FA3-VOICE-001"
VOICE_CONTRACT_ID = "FA3-VOICE-CONTRACTS-001"
VOICE_ADMISSION_ID = "FA3-VOICE-PROVIDER-ADMISSION-001"
VOICE_DECISION_ID = "FA3-DEC-VOICE-SYNTHESIS-PORTFOLIO-2026-09-01"
VOICE_GATE_ID = "FA3-VOICE-SYNTHESIS-GATESET-001"
VOICE_PROVIDER_IDS = (
    "FA3-PROVIDER-VOXCPM-001",
    "FA3-PROVIDER-XTTS-001",
    "FA3-PROVIDER-PIPER-001",
    "FA3-PROVIDER-QWEN3-TTS-001",
    "FA3-PROVIDER-MMS-TTS-HUN-001",
)
VOICE_PROFILE_PATH = "canonical/profiles/FA3-VOICE-001.json"
VOICE_CONTRACT_PATH = "canonical/contracts/FA3-VOICE-CONTRACTS-001.json"
VOICE_ADMISSION_PATH = "canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json"
VOICE_DECISION_PATH = "canonical/decisions/FA3-DEC-VOICE-SYNTHESIS-PORTFOLIO-2026-09-01.json"
VOICE_REFERENCE_PATH = "canonical/references/FA3-VOICE-SYNTHESIS-UPSTREAM-REFERENCE-2026-09-01.json"
VOICE_ENFORCEMENT_PATH = "canonical/voice-synthesis-enforcement.json"
VOICE_EVIDENCE_PATH = "evidence/reference/voice-synthesis-ci-2026-09-01.json"
VOICE_GATE_PATH = "src/fa3_voice_synthesis_gate.py"
VOICE_TEST_PATH = "tests/test_voice_synthesis_gate.py"
VOICE_PROVIDER_PATHS = tuple(f"canonical/providers/{provider_id}.json" for provider_id in VOICE_PROVIDER_IDS)
VOICE_CAPABILITY_IDS = ("CAP-115", "CAP-116", "CAP-117")
VOICE_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_PASS_CURRENT_HOST_AND_HU_QUALITY_PENDING"


GPUK_PROFILE_ID = "FA3-GPU-KERNEL-RUNTIME-001"
GPUK_CONTRACT_ID = "FA3-GPU-KERNEL-RUNTIME-CONTRACTS-001"
GPUK_AMPERE_PROVIDER_ID = "FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001"
GPUK_DEEPGEMM_PROVIDER_ID = "FA3-PROVIDER-DEEPGEMM-001"
GPUK_DECISION_ID = "FA3-DEC-GPU-KERNEL-RUNTIME-DEEPGEMM-2026-09-03"
GPUK_GATE_ID = "FA3-GPU-KERNEL-RUNTIME-GATESET-001"
GPUK_PROFILE_PATH = "canonical/profiles/FA3-GPU-KERNEL-RUNTIME-001.json"
GPUK_CONTRACT_PATH = "canonical/contracts/FA3-GPU-KERNEL-RUNTIME-CONTRACTS-001.json"
GPUK_AMPERE_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001.json"
GPUK_DEEPGEMM_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-DEEPGEMM-001.json"
GPUK_DECISION_PATH = "canonical/decisions/FA3-DEC-GPU-KERNEL-RUNTIME-DEEPGEMM-2026-09-03.json"
GPUK_REFERENCE_PATH = "canonical/references/FA3-DEEPGEMM-UPSTREAM-REFERENCE-2026-09-03.json"
GPUK_EVIDENCE_PATH = "evidence/reference/gpu-kernel-runtime-ci-2026-09-03.json"
GPUK_ENFORCEMENT_PATH = "canonical/gpu-kernel-runtime-enforcement.json"
GPUK_ADMISSION_PATH = "canonical/gpu-kernel-runtime-admission.json"
GPUK_GATE_RECORD_PATH = "canonical/FA3-GATE-GPU-KERNEL-RUNTIME-001.json"
GPUK_CURRENT_HOST_GATE_RECORD_PATH = "canonical/FA3-GATE-GPU-KERNEL-RUNTIME-CURRENT-HOST-001.json"
GPUK_GATE_PATH = "src/fa3_gpu_kernel_runtime_gate.py"
GPUK_DISPATCH_PATH = "src/fa3_gpu_kernel_dispatch_reference.py"
GPUK_TEST_PATH = "tests/test_gpu_kernel_runtime_gate.py"
GPUK_COLLECTOR_PATH = "evidence/collect-gpu-kernel-runtime-current-host.py"
GPUK_BENCH_PATH = "bin/fa3-gpu-kernel-benchmark"
GPUK_CAPABILITY_IDS = ("CAP-005","CAP-006","CAP-056","CAP-060","CAP-069","CAP-078","CAP-087","CAP-137","CAP-143")
GPUK_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CURRENT_HOST_SM86_E2E_PENDING_DEEPGEMM_INELIGIBLE"
GPUK_DEEPGEMM_PIN = "31f4f7276de598d2b59942f6613aa534055b4ab5"


VPLC_PROFILE_ID = "FA3-VIDEO-001"
VPLC_CONTRACT_ID = "FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001"
VPLC_OPEN_SORA_PROVIDER_ID = "FA3-PROVIDER-OPEN-SORA-PLAN-001"
VPLC_HELIOS_PROVIDER_ID = "FA3-PROVIDER-HELIOS-001"
VPLC_PROVIDER_IDS = (VPLC_OPEN_SORA_PROVIDER_ID, VPLC_HELIOS_PROVIDER_ID)
VPLC_DECISION_ID = "FA3-DEC-PKU-YUAN-VIDEO-PROVIDER-LIFECYCLE-2026-09-03"
VPLC_GATE_ID = "FA3-VIDEO-PROVIDER-LIFECYCLE-GATESET-001"
VPLC_EXECUTABLE_GATE_ID = "FA3-GATE-VIDEO-PROVIDER-LIFECYCLE-001"
VPLC_PROFILE_PATH = "canonical/profiles/FA3-VIDEO-001.json"
VPLC_CONTRACT_PATH = "canonical/contracts/FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001.json"
VPLC_OPEN_SORA_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-OPEN-SORA-PLAN-001.json"
VPLC_HELIOS_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-HELIOS-001.json"
VPLC_DECISION_PATH = "canonical/decisions/FA3-DEC-PKU-YUAN-VIDEO-PROVIDER-LIFECYCLE-2026-09-03.json"
VPLC_REFERENCE_PATH = "canonical/references/FA3-PKU-YUAN-VIDEO-UPSTREAM-REFERENCE-2026-09-03.json"
VPLC_GATE_RECORD_PATH = "canonical/FA3-GATE-VIDEO-PROVIDER-LIFECYCLE-001.json"
VPLC_ENFORCEMENT_PATH = "canonical/video-provider-lifecycle-enforcement.json"
VPLC_ADMISSION_PATH = "canonical/video-provider-lifecycle-runtime-admission.json"
VPLC_EVIDENCE_PATH = "evidence/reference/pku-yuan-video-lifecycle-ci-2026-09-03.json"
VPLC_GATE_PATH = "src/fa3_video_provider_lifecycle_gate.py"
VPLC_TEST_PATH = "tests/test_video_provider_lifecycle_gate.py"
VPLC_CAPABILITY_IDS = ("CAP-016", "CAP-123", "CAP-126")
VPLC_OPEN_SORA_PIN = "f7fa604f4e3a523d6b973e4c89a5620ed1aff65a"
VPLC_HELIOS_PIN = "babed9811266e4b5b111c9c1e0977a07899066ab"
VPLC_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CANONICAL_REFERENCE_PASS_RUNTIME_NOT_PROMOTED"

_MUTABLE_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache", ".fa3-current-host"}
_MUTABLE_DIR_NAMES = {"__pycache__"}


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def finding(code: str, message: str, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}


def is_mutable_runtime_path(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts:
        return True
    if parts[0] in _MUTABLE_TOP_LEVEL:
        return True
    if any(part in _MUTABLE_DIR_NAMES for part in parts):
        return True
    if rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep":
        return True
    return False


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed with rc={proc.returncode}: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def _git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    raise RuntimeError(
        f"git merge-base --is-ancestor failed with rc={proc.returncode}: {proc.stderr.strip()}"
    )


def _snapshot_release_surface_equivalent_except_projection(
    root: Path, snapshot_head: str, current_head: str = "HEAD"
) -> bool:
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "diff",
            "--quiet",
            snapshot_head,
            current_head,
            "--",
            ".",
            f":(exclude){PROJECTION_PATH}",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    raise RuntimeError(
        "git diff --quiet snapshot/current release surface failed "
        f"with rc={proc.returncode}: {proc.stderr.strip()}"
    )


def _diff_rows(root: Path, snapshot_head: str):
    raw = _git(root, "diff", "--name-status", "--find-renames", BASE_COMMIT, snapshot_head)
    rows = []
    for line in raw.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith(("R", "C")):
            if len(parts) < 3:
                raise RuntimeError(f"unparseable rename/copy row: {line}")
            path = parts[-1]
        else:
            if len(parts) < 2:
                raise RuntimeError(f"unparseable name-status row: {line}")
            path = parts[1]
        rows.append((status, path))
    return rows


def collect_git_snapshot_facts(root: Path, snapshot_head: str):
    root = Path(root).resolve()
    if not snapshot_head:
        raise RuntimeError("source_snapshot.pre_projection_head_sha is empty")

    rows = _diff_rows(root, snapshot_head)
    paths = [path for _, path in rows]

    def prefixed(prefix: str):
        return sorted(path for path in paths if path.startswith(prefix))

    added = sum(status.startswith("A") for status, _ in rows)
    modified = sum(status.startswith("M") for status, _ in rows)
    removed = sum(status.startswith("D") for status, _ in rows)
    other = len(rows) - added - modified - removed

    return {
        "snapshot_head_sha": _git(root, "rev-parse", snapshot_head),
        "current_head_sha": _git(root, "rev-parse", "HEAD"),
        "root_tree_sha": _git(root, "rev-parse", f"{snapshot_head}^{{tree}}"),
        "canonical_tree_sha": _git(root, "rev-parse", f"{snapshot_head}:canonical"),
        "baseline_is_ancestor": _git_is_ancestor(root, BASE_COMMIT, snapshot_head),
        "snapshot_is_ancestor_of_current_head": _git_is_ancestor(root, snapshot_head, "HEAD"),
        "snapshot_release_surface_equivalent_except_projection":
            _snapshot_release_surface_equivalent_except_projection(root, snapshot_head, "HEAD"),
        "commit_count": int(_git(root, "rev-list", "--count", f"{BASE_COMMIT}..{snapshot_head}")),
        "delta_file_count": len(rows),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": other,
        "area_counts": {
            "canonical_files_in_post_baseline_delta": len(prefixed("canonical/")),
            "evidence_files_in_post_baseline_delta": len(prefixed("evidence/")),
            "source_files_in_post_baseline_delta": len(prefixed("src/")),
            "test_files_in_post_baseline_delta": len(prefixed("tests/")),
            "workflow_files_in_post_baseline_delta": len(prefixed(".github/workflows/")),
        },
        "record_lists": {
            "provider_records": prefixed("canonical/providers/"),
            "profile_records": prefixed("canonical/profiles/"),
            "contract_records": prefixed("canonical/contracts/"),
            "decision_records": prefixed("canonical/decisions/"),
            "upstream_reference_records": prefixed("canonical/references/"),
            "reference_evidence_records": prefixed("evidence/reference/"),
        },
    }


def gate(root: Path):
    root = Path(root).resolve()
    findings = []

    projection = loadj(root / PROJECTION_PATH)
    policy = loadj(root / "canonical/enforcement-policy.json")
    attestation = loadj(root / "canonical/source-graph-attestation.json")
    evidence = loadj(root / "evidence/evidence-registry.json")
    decision = loadj(root / DECISION_PATH)

    if (
        projection.get("schema") != "fa3.canonical-release-projection.v1"
        or projection.get("id") != PROJECTION_ID
        or projection.get("status") != "CANONICAL_PROJECTED"
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-001", "Projection identity/schema/status mismatch"))

    if (
        projection.get("base_release") != BASE_RELEASE
        or projection.get("base_release_commit") != BASE_COMMIT
        or projection.get("projection_semantics") != "NO_BASELINE_SEMANTIC_CHANGE_IMPLEMENTATION_PROJECTION_UPDATE"
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-002", "Baseline release/commit or projection semantics changed"))

    invariants = projection.get("invariants", {})
    if (
        invariants.get("canonical_capability_count") != CAPABILITY_COUNT
        or invariants.get("new_capabilities") != 0
        or invariants.get("new_architectural_authorities") != 0
        or invariants.get("baseline_semantics_frozen") is not True
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-003", "Capability/authority/baseline invariant mismatch"))

    if (
        policy.get("architecture_release") != BASE_RELEASE
        or policy.get("canonical_capability_count") != CAPABILITY_COUNT
        or policy.get("canonical_release_projection") != PROJECTION_ID
        or policy.get("canonical_release_projection_path") != PROJECTION_PATH
        or policy.get("projection_semantics") != projection.get("projection_semantics")
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-004", "Global enforcement policy is not bound to the unified projection"))

    source_graph = projection.get("baseline_source_graph", {})
    if (
        attestation.get("release") != BASE_RELEASE
        or attestation.get("sha256") != EXPECTED_SOURCE_GRAPH_SHA256
        or attestation.get("graph_nodes") != EXPECTED_SOURCE_GRAPH_NODES
        or attestation.get("graph_edges") != EXPECTED_SOURCE_GRAPH_EDGES
        or source_graph.get("sha256") != EXPECTED_SOURCE_GRAPH_SHA256
        or source_graph.get("graph_nodes") != EXPECTED_SOURCE_GRAPH_NODES
        or source_graph.get("graph_edges") != EXPECTED_SOURCE_GRAPH_EDGES
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-005", "v3.0.11 source-graph anchor drift"))

    records = evidence.get("records", [])
    if (
        evidence.get("architecture_release") != BASE_RELEASE
        or evidence.get("canonical_capability_count") != CAPABILITY_COUNT
        or len(records) != CAPABILITY_COUNT
        or [r.get("subject_id") for r in records] != [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-006", "Evidence Registry release/cardinality invariant mismatch"))

    projection_gates = set(projection.get("mandatory_reference_gates", []))
    policy_gates = set(policy.get("mandatory_reference_gates", []))
    if not projection_gates or projection_gates != policy_gates:
        findings.append(finding("FA3-RELEASE-PROJECTION-007", "Projection/global mandatory reference gate set mismatch"))

    manifest = projection.get("manifest", [])
    manifest_paths = {m.get("path") for m in manifest}
    if projection.get("manifest_entry_count") != len(manifest) or len(manifest_paths) != len(manifest):
        findings.append(finding("FA3-RELEASE-PROJECTION-008", "Projection manifest cardinality/uniqueness mismatch"))

    kanboard = projection.get("kanboard_reconciliation", {})
    inventory = projection.get("overlay_inventory", {})
    required_kanboard_manifest_paths = {
        KANBOARD_PROVIDER_PATH,
        KANBOARD_DECISION_PATH,
        KANBOARD_REFERENCE_PATH,
        KANBOARD_EVIDENCE_PATH,
        KANBOARD_ENFORCEMENT_PATH,
        KANBOARD_GATE_PATH,
        KANBOARD_TEST_PATH,
    }
    missing_overlay_members = []
    for key, required in {
        "provider_records": KANBOARD_PROVIDER_PATH,
        "decision_records": KANBOARD_DECISION_PATH,
        "upstream_reference_records": KANBOARD_REFERENCE_PATH,
        "reference_evidence_records": KANBOARD_EVIDENCE_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_overlay_members.append({"inventory": key, "path": required})

    kanboard_provider = loadj(root / KANBOARD_PROVIDER_PATH) if (root / KANBOARD_PROVIDER_PATH).is_file() else {}
    kanboard_evidence = loadj(root / KANBOARD_EVIDENCE_PATH) if (root / KANBOARD_EVIDENCE_PATH).is_file() else {}
    kanboard_manifest_missing = sorted(required_kanboard_manifest_paths - manifest_paths)
    if (
        kanboard.get("provider_id") != KANBOARD_PROVIDER_ID
        or kanboard.get("gate_id") != KANBOARD_GATE_ID
        or kanboard.get("classification") != "OPTIONAL_REFERENCE_PROVIDER"
        or kanboard.get("reconciliation_status") != KANBOARD_RECONCILIATION_STATUS
        or kanboard.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or kanboard.get("new_capabilities") != 0
        or kanboard.get("new_architectural_authorities") != 0
        or kanboard.get("capability_count_after") != CAPABILITY_COUNT
        or KANBOARD_GATE_ID not in projection_gates
        or KANBOARD_GATE_ID not in policy_gates
        or missing_overlay_members
        or kanboard_manifest_missing
        or kanboard_provider.get("id") != KANBOARD_PROVIDER_ID
        or kanboard_provider.get("canonical_root") is not False
        or kanboard_provider.get("architectural_authority") is not False
        or kanboard_provider.get("new_capability") is not False
        or kanboard_provider.get("capability_count") != CAPABILITY_COUNT
        or "OPTIONAL_PROVIDER" not in kanboard_provider.get("classification", [])
        or kanboard_evidence.get("provider_id") != KANBOARD_PROVIDER_ID
        or kanboard_evidence.get("gate_id") != KANBOARD_GATE_ID
        or kanboard_evidence.get("status") != "PASS"
        or kanboard_evidence.get("new_capabilities") != 0
        or kanboard_evidence.get("new_architectural_authorities") != 0
        or kanboard_evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-021",
                "Kanboard global projection/inventory reconciliation invariant mismatch",
                reconciliation_status=kanboard.get("reconciliation_status"),
                missing_overlay_members=missing_overlay_members,
                missing_manifest_paths=kanboard_manifest_missing,
            )
        )

    presenton = projection.get("presenton_reconciliation", {})
    required_presenton_manifest_paths = {
        PRESENTON_PROVIDER_PATH,
        PRESENTON_DECISION_PATH,
        PRESENTON_REFERENCE_PATH,
        PRESENTON_EVIDENCE_PATH,
        PRESENTON_CONTRACT_PATH,
        PRESENTON_ENFORCEMENT_PATH,
        PRESENTON_GATE_PATH,
        PRESENTON_TEST_PATH,
        "evidence/collect-presenton-current-host.py",
        "bin/fa3-presenton-current-host.sh",
        ".github/workflows/fa3-presenton-current-host.yml",
        "deployment/presenton/README.md",
        "deployment/presenton/ai-creative.target",
        "deployment/presenton/postgresql-bootstrap.sql",
        "deployment/presenton/presenton.caddy",
        "deployment/presenton/presenton.container",
    }
    presenton_overlay_requirements = {
        "provider_records": PRESENTON_PROVIDER_PATH,
        "decision_records": PRESENTON_DECISION_PATH,
        "upstream_reference_records": PRESENTON_REFERENCE_PATH,
        "reference_evidence_records": PRESENTON_EVIDENCE_PATH,
        "contract_records": PRESENTON_CONTRACT_PATH,
    }
    missing_presenton_overlay_members = [
        {"inventory": key, "path": required}
        for key, required in presenton_overlay_requirements.items()
        if required not in inventory.get(key, [])
    ]
    presenton_manifest_missing = sorted(required_presenton_manifest_paths - manifest_paths)
    presenton_provider = loadj(root / PRESENTON_PROVIDER_PATH) if (root / PRESENTON_PROVIDER_PATH).is_file() else {}
    presenton_evidence = loadj(root / PRESENTON_EVIDENCE_PATH) if (root / PRESENTON_EVIDENCE_PATH).is_file() else {}
    cap033 = next((item for item in evidence.get("records", []) if item.get("subject_id") == "CAP-033"), {})
    if (
        presenton.get("provider_id") != PRESENTON_PROVIDER_ID
        or presenton.get("contract_id") != PRESENTON_CONTRACT_ID
        or presenton.get("gate_id") != PRESENTON_GATE_ID
        or presenton.get("classification") != "OPTIONAL_PRODUCTION_CANDIDATE_PROVIDER"
        or presenton.get("reconciliation_status") != PRESENTON_RECONCILIATION_STATUS
        or presenton.get("current_host_production_e2e") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or presenton.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or presenton.get("new_capabilities") != 0
        or presenton.get("new_architectural_authorities") != 0
        or presenton.get("capability_count_after") != CAPABILITY_COUNT
        or PRESENTON_GATE_ID not in projection_gates
        or PRESENTON_GATE_ID not in policy_gates
        or missing_presenton_overlay_members
        or presenton_manifest_missing
        or presenton_provider.get("id") != PRESENTON_PROVIDER_ID
        or presenton_provider.get("canonical_root") is not False
        or presenton_provider.get("architectural_authority") is not False
        or presenton_provider.get("new_capability") is not False
        or presenton_provider.get("capability_count") != CAPABILITY_COUNT
        or "OPTIONAL_PROVIDER" not in presenton_provider.get("classification", [])
        or presenton_evidence.get("provider_id") != PRESENTON_PROVIDER_ID
        or presenton_evidence.get("gate_id") != PRESENTON_GATE_ID
        or presenton_evidence.get("status") != "PASS"
        or presenton_evidence.get("current_host_production_e2e", {}).get("status") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or "FA3-DEC-PRESENTON-2026-08-30" not in cap033.get("source_decision_ids", [])
        or PRESENTON_EVIDENCE_PATH not in cap033.get("evidence_artifacts", [])
        or cap033.get("status") != "PENDING_CURRENT_HOST"
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-022",
                "Presenton global projection/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=presenton.get("reconciliation_status"),
                current_host_production_e2e=presenton.get("current_host_production_e2e"),
                missing_overlay_members=missing_presenton_overlay_members,
                missing_manifest_paths=presenton_manifest_missing,
            )
        )

    autogpt = projection.get("autogpt_reconciliation", {})
    required_autogpt_manifest_paths = {
        AUTOGPT_PROVIDER_PATH,
        AUTOGPT_DECISION_PATH,
        AUTOGPT_REFERENCE_PATH,
        AUTOGPT_EVIDENCE_PATH,
        AUTOGPT_RECONCILIATION_EVIDENCE_PATH,
        AUTOGPT_ENFORCEMENT_PATH,
        AUTOGPT_ADMISSION_PATH,
        AUTOGPT_GATE_PATH,
        AUTOGPT_TEST_PATH,
        "evidence/evidence-registry.json",
    }
    autogpt_overlay_requirements = {
        "provider_records": AUTOGPT_PROVIDER_PATH,
        "decision_records": AUTOGPT_DECISION_PATH,
        "upstream_reference_records": AUTOGPT_REFERENCE_PATH,
        "reference_evidence_records": AUTOGPT_EVIDENCE_PATH,
    }
    missing_autogpt_overlay_members = [
        {"inventory": key, "path": required}
        for key, required in autogpt_overlay_requirements.items()
        if required not in inventory.get(key, [])
    ]
    autogpt_manifest_missing = sorted(required_autogpt_manifest_paths - manifest_paths)
    autogpt_provider = loadj(root / AUTOGPT_PROVIDER_PATH) if (root / AUTOGPT_PROVIDER_PATH).is_file() else {}
    autogpt_evidence = loadj(root / AUTOGPT_EVIDENCE_PATH) if (root / AUTOGPT_EVIDENCE_PATH).is_file() else {}
    autogpt_reconciliation_evidence = loadj(root / AUTOGPT_RECONCILIATION_EVIDENCE_PATH) if (root / AUTOGPT_RECONCILIATION_EVIDENCE_PATH).is_file() else {}
    autogpt_admission = loadj(root / AUTOGPT_ADMISSION_PATH) if (root / AUTOGPT_ADMISSION_PATH).is_file() else {}
    cap028 = next((item for item in records if item.get("subject_id") == AUTOGPT_CAPABILITY_ID), {})
    if (
        autogpt.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt.get("gate_id") != AUTOGPT_GATE_ID
        or autogpt.get("capability_id") != AUTOGPT_CAPABILITY_ID
        or autogpt.get("classification") != "OPTIONAL_AGENTIC_WORKFLOW_REFERENCE_PROVIDER"
        or autogpt.get("reconciliation_status") != AUTOGPT_RECONCILIATION_STATUS
        or autogpt.get("runtime_activation_status") != "NOT_PROMOTED_REFERENCE_ONLY"
        or autogpt.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or autogpt.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or autogpt.get("new_capabilities") != 0
        or autogpt.get("new_architectural_authorities") != 0
        or autogpt.get("capability_count_after") != CAPABILITY_COUNT
        or AUTOGPT_GATE_ID not in projection_gates
        or AUTOGPT_GATE_ID not in policy_gates
        or missing_autogpt_overlay_members
        or autogpt_manifest_missing
        or autogpt_provider.get("id") != AUTOGPT_PROVIDER_ID
        or autogpt_provider.get("canonical_root") is not False
        or autogpt_provider.get("architectural_authority") is not False
        or autogpt_provider.get("new_capability") is not False
        or autogpt_provider.get("capability_count") != CAPABILITY_COUNT
        or "OPTIONAL_PROVIDER" not in autogpt_provider.get("classification", [])
        or autogpt_provider.get("runtime_activation_status") != "NOT_PROMOTED_REFERENCE_ONLY"
        or autogpt_evidence.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt_evidence.get("gate_id") != AUTOGPT_GATE_ID
        or autogpt_evidence.get("status") != "PASS"
        or autogpt_evidence.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or autogpt_reconciliation_evidence.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt_reconciliation_evidence.get("capability_id") != AUTOGPT_CAPABILITY_ID
        or autogpt_reconciliation_evidence.get("status") != "PASS"
        or autogpt_reconciliation_evidence.get("conclusion") != "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILIATION_PASS"
        or autogpt_admission.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt_admission.get("status") != "NOT_ADMITTED"
        or autogpt_admission.get("fail_closed") is not True
        or autogpt_admission.get("current_host_evidence_required") is not True
        or "FA3-DEC-AUTOGPT-2026-08-30" not in cap028.get("source_decision_ids", [])
        or AUTOGPT_EVIDENCE_PATH not in cap028.get("evidence_artifacts", [])
        or AUTOGPT_RECONCILIATION_EVIDENCE_PATH not in cap028.get("evidence_artifacts", [])
        or cap028.get("runtime_conformance") != "EVIDENCE-PENDING"
        or cap028.get("status") != "PENDING_CURRENT_HOST"
        or cap028.get("promotion_state") != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-023",
                "AutoGPT global release/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=autogpt.get("reconciliation_status"),
                runtime_activation_status=autogpt.get("runtime_activation_status"),
                missing_overlay_members=missing_autogpt_overlay_members,
                missing_manifest_paths=autogpt_manifest_missing,
                cap028_evidence_artifacts=cap028.get("evidence_artifacts", []),
            )
        )

    dac = projection.get("developer_agent_coordination_reconciliation", {})
    required_dac_manifest_paths = {
        DAC_CONTRACT_PATH,
        DAC_CONFORMANCE_PATH,
        DAC_DECISION_PATH,
        DAC_ENFORCEMENT_PATH,
        DAC_RUNTIME_PATH,
        DAC_GATE_PATH,
        DAC_TEST_PATH,
        DAC_COLLECTOR_PATH,
        DAC_EXAMPLE_PATH,
        DAC_RUNNER_PATH,
        "canonical/profiles/FA3-AGENT-EXEC-001.json",
    }
    missing_dac_overlay_members = []
    for key, required in {
        "contract_records": DAC_CONTRACT_PATH,
        "decision_records": DAC_DECISION_PATH,
        "profile_records": "canonical/profiles/FA3-AGENT-EXEC-001.json",
    }.items():
        if required not in inventory.get(key, []):
            missing_dac_overlay_members.append({"inventory": key, "path": required})
    dac_manifest_missing = sorted(required_dac_manifest_paths - manifest_paths)
    dac_contract = loadj(root / DAC_CONTRACT_PATH) if (root / DAC_CONTRACT_PATH).is_file() else {}
    dac_conformance = loadj(root / DAC_CONFORMANCE_PATH) if (root / DAC_CONFORMANCE_PATH).is_file() else {}
    dac_decision = loadj(root / DAC_DECISION_PATH) if (root / DAC_DECISION_PATH).is_file() else {}
    if (
        dac.get("profile_id") != DAC_PROFILE_ID
        or dac.get("contract_id") != DAC_CONTRACT_ID
        or dac.get("runtime_id") != DAC_RUNTIME_ID
        or dac.get("gate_id") != DAC_GATE_ID
        or dac.get("reconciliation_status") != DAC_RECONCILIATION_STATUS
        or dac.get("reference_e2e_status") != "CI_REFERENCE_RUNTIME_E2E_REQUIRED"
        or dac.get("current_host_production_claim") is not False
        or dac.get("new_capabilities") != 0
        or dac.get("new_architectural_authorities") != 0
        or dac.get("capability_count_after") != CAPABILITY_COUNT
        or DAC_GATE_ID not in projection_gates
        or DAC_GATE_ID not in policy_gates
        or missing_dac_overlay_members
        or dac_manifest_missing
        or dac_contract.get("id") != DAC_CONTRACT_ID
        or dac_contract.get("parent_profile") != DAC_PROFILE_ID
        or dac_contract.get("provider_neutral") is not True
        or dac_contract.get("new_capability") is not False
        or dac_contract.get("new_architectural_authority") is not False
        or dac_contract.get("capability_count") != CAPABILITY_COUNT
        or dac_conformance.get("id") != "FA3-DEVELOPER-AGENT-COORDINATION-RUNTIME-CONFORMANCE-001"
        or dac_conformance.get("runtime_id") != DAC_RUNTIME_ID
        or dac_conformance.get("runtime_version") != "0.1.0"
        or dac_conformance.get("status") != "REFERENCE_RUNTIME"
        or dac_conformance.get("executable_e2e", {}).get("current_host_production_claim") is not False
        or dac_decision.get("status") != "CANONICAL_CLOSED"
        or dac_decision.get("new_capabilities") != 0
        or dac_decision.get("new_architectural_authorities") != 0
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-024",
                "Developer-agent coordination global projection/runtime-E2E reconciliation invariant mismatch",
                reconciliation_status=dac.get("reconciliation_status"),
                missing_overlay_members=missing_dac_overlay_members,
                missing_manifest_paths=dac_manifest_missing,
            )
        )

    codex = projection.get("codex_reconciliation", {})
    required_codex_manifest_paths = {
        CODEX_PROVIDER_PATH,
        CODEX_REFERENCE_PATH,
        CODEX_CONTRACT_PATH,
        CODEX_ADMISSION_PATH,
        CODEX_ENFORCEMENT_PATH,
        CODEX_DECISION_PATH,
        CODEX_EVIDENCE_PATH,
        CODEX_ADAPTER_PATH,
        CODEX_GATE_PATH,
        CODEX_TEST_PATH,
        CODEX_COLLECTOR_PATH,
        CODEX_BOOTSTRAP_PATH,
        CODEX_RUNNER_PATH,
        CODEX_WORKFLOW_PATH,
        CODEX_RUNBOOK_PATH,
        CODEX_EXAMPLE_PATH,
        "evidence/evidence-registry.json",
    }
    missing_codex_overlay_members = []
    for key, required in {
        "provider_records": CODEX_PROVIDER_PATH,
        "decision_records": CODEX_DECISION_PATH,
        "upstream_reference_records": CODEX_REFERENCE_PATH,
        "reference_evidence_records": CODEX_EVIDENCE_PATH,
        "contract_records": CODEX_CONTRACT_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_codex_overlay_members.append({"inventory": key, "path": required})
    codex_manifest_missing = sorted(required_codex_manifest_paths - manifest_paths)
    codex_provider = loadj(root / CODEX_PROVIDER_PATH) if (root / CODEX_PROVIDER_PATH).is_file() else {}
    codex_reference = loadj(root / CODEX_REFERENCE_PATH) if (root / CODEX_REFERENCE_PATH).is_file() else {}
    codex_contract = loadj(root / CODEX_CONTRACT_PATH) if (root / CODEX_CONTRACT_PATH).is_file() else {}
    codex_admission = loadj(root / CODEX_ADMISSION_PATH) if (root / CODEX_ADMISSION_PATH).is_file() else {}
    codex_evidence = loadj(root / CODEX_EVIDENCE_PATH) if (root / CODEX_EVIDENCE_PATH).is_file() else {}
    cap028_codex = next((item for item in records if item.get("subject_id") == CODEX_CAPABILITY_ID), {})
    codex_projection_status = cap028_codex.get("codex_provider_projection_status", {})
    if (
        codex.get("provider_id") != CODEX_PROVIDER_ID
        or codex.get("contract_id") != CODEX_CONTRACT_ID
        or codex.get("admission_id") != CODEX_ADMISSION_ID
        or codex.get("gate_id") != CODEX_GATE_ID
        or codex.get("capability_id") != CODEX_CAPABILITY_ID
        or codex.get("classification") != "OPTIONAL_EXTERNAL_DEVELOPER_AGENT_PRODUCTION_CANDIDATE"
        or codex.get("reconciliation_status") != CODEX_RECONCILIATION_STATUS
        or codex.get("runtime_activation_status") != "NOT_ADMITTED_PENDING_CURRENT_HOST"
        or codex.get("current_host_production_e2e") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or codex.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or codex.get("new_capabilities") != 0
        or codex.get("new_architectural_authorities") != 0
        or codex.get("capability_count_after") != CAPABILITY_COUNT
        or CODEX_GATE_ID not in projection_gates
        or CODEX_GATE_ID not in policy_gates
        or missing_codex_overlay_members
        or codex_manifest_missing
        or codex_provider.get("id") != CODEX_PROVIDER_ID
        or codex_provider.get("canonical_root") is not False
        or codex_provider.get("architectural_authority") is not False
        or codex_provider.get("new_capability") is not False
        or codex_provider.get("capability_count") != CAPABILITY_COUNT
        or codex_provider.get("runtime_activation_status") != "NOT_ADMITTED_PENDING_CURRENT_HOST"
        or codex_provider.get("immutable_runtime_pin", {}).get("version") != "0.151.0"
        or codex_provider.get("immutable_runtime_pin", {}).get("release_commit") != "78c290807ce710180111df227df3b7a4fe845452"
        or codex_reference.get("id") != "FA3-CODEX-UPSTREAM-REFERENCE-2026-08-31"
        or codex_reference.get("release", {}).get("version") != "0.151.0"
        or codex_contract.get("id") != CODEX_CONTRACT_ID
        or codex_contract.get("parent_profile") != "FA3-AGENT-EXEC-001"
        or codex_admission.get("id") != CODEX_ADMISSION_ID
        or codex_admission.get("status") != "NOT_ADMITTED"
        or codex_admission.get("fail_closed") is not True
        or codex_admission.get("current_host_evidence_required") is not True
        or codex_evidence.get("provider_id") != CODEX_PROVIDER_ID
        or codex_evidence.get("gate_id") != CODEX_GATE_ID
        or codex_evidence.get("status") != "PASS"
        or codex_evidence.get("current_host_production_evidence") is not False
        or "FA3-DEC-CODEX-ADAPTER-2026-08-31" not in cap028_codex.get("source_decision_ids", [])
        or CODEX_EVIDENCE_PATH not in cap028_codex.get("evidence_artifacts", [])
        or cap028_codex.get("runtime_conformance") != "EVIDENCE-PENDING"
        or cap028_codex.get("status") != "PENDING_CURRENT_HOST"
        or cap028_codex.get("promotion_state") != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
        or codex_projection_status.get("provider_id") != CODEX_PROVIDER_ID
        or codex_projection_status.get("runtime_activation_status") != "NOT_ADMITTED_PENDING_CURRENT_HOST"
        or codex_projection_status.get("current_host_runtime_evidence") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-025",
                "Codex adapter global projection/current-host admission reconciliation invariant mismatch",
                reconciliation_status=codex.get("reconciliation_status"),
                runtime_activation_status=codex.get("runtime_activation_status"),
                current_host_production_e2e=codex.get("current_host_production_e2e"),
                missing_overlay_members=missing_codex_overlay_members,
                missing_manifest_paths=codex_manifest_missing,
                cap028_codex_projection_status=codex_projection_status,
            )
        )

    aisec = projection.get("ai_infra_guard_reconciliation", {})
    required_aisec_manifest_paths = {
        AISEC_PROFILE_PATH,
        AISEC_CONTRACT_PATH,
        AISEC_PROVIDER_PATH,
        AISEC_DECISION_PATH,
        AISEC_REFERENCE_PATH,
        AISEC_EVIDENCE_PATH,
        AISEC_ENFORCEMENT_PATH,
        AISEC_GATE_PATH,
        AISEC_TEST_PATH,
        AISEC_ADMISSION_PATH,
        AISEC_ADAPTER_PATH,
        AISEC_COLLECTOR_PATH,
        AISEC_BOOTSTRAP_PATH,
        AISEC_RUNNER_PATH,
        AISEC_WORKFLOW_PATH,
        "evidence/evidence-registry.json",
    }
    missing_aisec_overlay_members = []
    for key, required in {
        "profile_records": AISEC_PROFILE_PATH,
        "contract_records": AISEC_CONTRACT_PATH,
        "provider_records": AISEC_PROVIDER_PATH,
        "decision_records": AISEC_DECISION_PATH,
        "upstream_reference_records": AISEC_REFERENCE_PATH,
        "reference_evidence_records": AISEC_EVIDENCE_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_aisec_overlay_members.append({"inventory": key, "path": required})
    aisec_manifest_missing = sorted(required_aisec_manifest_paths - manifest_paths)
    aisec_profile = loadj(root / AISEC_PROFILE_PATH) if (root / AISEC_PROFILE_PATH).is_file() else {}
    aisec_contract = loadj(root / AISEC_CONTRACT_PATH) if (root / AISEC_CONTRACT_PATH).is_file() else {}
    aisec_provider = loadj(root / AISEC_PROVIDER_PATH) if (root / AISEC_PROVIDER_PATH).is_file() else {}
    aisec_evidence = loadj(root / AISEC_EVIDENCE_PATH) if (root / AISEC_EVIDENCE_PATH).is_file() else {}
    aisec_admission = loadj(root / AISEC_ADMISSION_PATH) if (root / AISEC_ADMISSION_PATH).is_file() else {}
    aisec_bindings = {
        cap_id: next((item for item in records if item.get("subject_id") == cap_id), {})
        for cap_id in AISEC_CAPABILITY_IDS
    }
    aisec_binding_invalid = []
    for cap_id, rec in aisec_bindings.items():
        if (
            "FA3-DEC-AI-INFRA-GUARD-2026-08-30" not in rec.get("source_decision_ids", [])
            or AISEC_EVIDENCE_PATH not in rec.get("evidence_artifacts", [])
            or rec.get("runtime_conformance") != "EVIDENCE-PENDING"
            or rec.get("status") != "PENDING_CURRENT_HOST"
            or rec.get("promotion_state") != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
        ):
            aisec_binding_invalid.append(cap_id)
    if (
        aisec.get("profile_id") != AISEC_PROFILE_ID
        or aisec.get("contract_id") != AISEC_CONTRACT_ID
        or aisec.get("provider_id") != AISEC_PROVIDER_ID
        or aisec.get("gate_id") != AISEC_GATE_ID
        or aisec.get("admission_id") != "FA3-AI-INFRA-GUARD-RUNTIME-ADMISSION-001"
        or aisec.get("adapter_id") != "FA3-AI-INFRA-GUARD-ADAPTER-001"
        or aisec.get("classification") != "OPTIONAL_REFERENCE_SECURITY_VALIDATION_PROVIDER"
        or aisec.get("reconciliation_status") != AISEC_RECONCILIATION_STATUS
        or aisec.get("reference_evidence_status") != "CI_CANONICAL_REGRESSION_PASS"
        or aisec.get("reference_evidence") != AISEC_EVIDENCE_PATH
        or aisec.get("runtime_activation_status") != "NOT_ADMITTED_PENDING_CURRENT_HOST"
        or aisec.get("runtime_surface") != "NATIVE_AI_INFRA_SCAN_CLI_ONLY"
        or aisec.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or aisec.get("current_host_runtime_promotion_claim") is not False
        or aisec.get("new_capabilities") != 0
        or aisec.get("new_architectural_authorities") != 0
        or aisec.get("capability_count_after") != CAPABILITY_COUNT
        or sorted(aisec.get("evidence_registry_capability_bindings", [])) != sorted(AISEC_CAPABILITY_IDS)
        or AISEC_GATE_ID not in projection_gates
        or AISEC_GATE_ID not in policy_gates
        or missing_aisec_overlay_members
        or aisec_manifest_missing
        or aisec_profile.get("id") != AISEC_PROFILE_ID
        or aisec_profile.get("new_capability") is not False
        or aisec_profile.get("new_architectural_authority") is not False
        or aisec_profile.get("capability_count") != CAPABILITY_COUNT
        or aisec_contract.get("id") != AISEC_CONTRACT_ID
        or aisec_contract.get("provider_neutral") is not True
        or aisec_provider.get("id") != AISEC_PROVIDER_ID
        or aisec_provider.get("canonical_root") is not False
        or aisec_provider.get("architectural_authority") is not False
        or aisec_provider.get("new_capability") is not False
        or aisec_provider.get("new_architectural_authority") is not False
        or aisec_provider.get("capability_count") != CAPABILITY_COUNT
        or aisec_provider.get("runtime_activation_status") != "NOT_ADMITTED_PENDING_CURRENT_HOST"
        or aisec_provider.get("runtime_admission") != "FA3-AI-INFRA-GUARD-RUNTIME-ADMISSION-001"
        or aisec_provider.get("adapter_id") != "FA3-AI-INFRA-GUARD-ADAPTER-001"
        or aisec_provider.get("runtime_surface") != "NATIVE_AI_INFRA_SCAN_CLI_ONLY"
        or aisec_admission.get("id") != "FA3-AI-INFRA-GUARD-RUNTIME-ADMISSION-001"
        or aisec_admission.get("provider_id") != AISEC_PROVIDER_ID
        or aisec_admission.get("adapter_id") != "FA3-AI-INFRA-GUARD-ADAPTER-001"
        or aisec_admission.get("status") != "NOT_ADMITTED"
        or aisec_admission.get("fail_closed") is not True
        or aisec_admission.get("current_host_evidence_required") is not True
        or aisec_admission.get("runtime_surface") != "NATIVE_AI_INFRA_SCAN_CLI_ONLY"
        or aisec_admission.get("immutable_runtime_pin", {}).get("release") != "v4.6.0"
        or aisec_admission.get("immutable_runtime_pin", {}).get("release_commit") != "e8931cc68001b66ad024fd87ef07394e9e96524a"
        or aisec.get("current_host_runtime_evidence") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or aisec.get("current_host_workflow") != AISEC_WORKFLOW_PATH
        or aisec_evidence.get("profile_id") != AISEC_PROFILE_ID
        or aisec_evidence.get("contract_id") != AISEC_CONTRACT_ID
        or aisec_evidence.get("provider_id") != AISEC_PROVIDER_ID
        or aisec_evidence.get("gate_id") != AISEC_GATE_ID
        or aisec_evidence.get("status") != "PASS"
        or aisec_evidence.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or aisec_evidence.get("current_host_runtime_promotion_claim") is not False
        or aisec_evidence.get("new_capabilities") != 0
        or aisec_evidence.get("new_architectural_authorities") != 0
        or aisec_evidence.get("capability_count_after") != CAPABILITY_COUNT
        or aisec_binding_invalid
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-026",
                "AI-Infra-Guard global release/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=aisec.get("reconciliation_status"),
                reference_evidence_status=aisec.get("reference_evidence_status"),
                missing_overlay_members=missing_aisec_overlay_members,
                missing_manifest_paths=aisec_manifest_missing,
                invalid_capability_bindings=aisec_binding_invalid,
            )
        )

    hybrid = projection.get("hybrid_editorial_reconciliation", {})
    required_hybrid_manifest_paths = {
        HYBRID_PROFILE_PATH,
        HYBRID_CONTRACT_PATH,
        HYBRID_KRITA_PROVIDER_PATH,
        HYBRID_KDENLIVE_PROVIDER_PATH,
        HYBRID_DECISION_PATH,
        HYBRID_GATE_RECORD_PATH,
        HYBRID_ENFORCEMENT_PATH,
        HYBRID_EVIDENCE_PATH,
        HYBRID_REFERENCE_RUNTIME_PATH,
        HYBRID_GATE_PATH,
        HYBRID_KDENLIVE_GATE_PATH,
        HYBRID_GLOBAL_ENFORCE_PATH,
        HYBRID_TEST_PATH,
        HYBRID_COLLECTOR_PATH,
        HYBRID_EXAMPLE_PATH,
        HYBRID_WORKFLOW_PATH,
        "evidence/evidence-registry.json",
    }
    missing_hybrid_overlay_members = []
    for key, required in {
        "profile_records": HYBRID_PROFILE_PATH,
        "contract_records": HYBRID_CONTRACT_PATH,
        "provider_records": HYBRID_KRITA_PROVIDER_PATH,
        "decision_records": HYBRID_DECISION_PATH,
        "reference_evidence_records": HYBRID_EVIDENCE_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_hybrid_overlay_members.append(
                {"inventory": key, "path": required}
            )

    hybrid_manifest_missing = sorted(
        required_hybrid_manifest_paths - manifest_paths
    )
    hybrid_profile = (
        loadj(root / HYBRID_PROFILE_PATH)
        if (root / HYBRID_PROFILE_PATH).is_file()
        else {}
    )
    hybrid_contract = (
        loadj(root / HYBRID_CONTRACT_PATH)
        if (root / HYBRID_CONTRACT_PATH).is_file()
        else {}
    )
    hybrid_krita = (
        loadj(root / HYBRID_KRITA_PROVIDER_PATH)
        if (root / HYBRID_KRITA_PROVIDER_PATH).is_file()
        else {}
    )
    hybrid_kdenlive = (
        loadj(root / HYBRID_KDENLIVE_PROVIDER_PATH)
        if (root / HYBRID_KDENLIVE_PROVIDER_PATH).is_file()
        else {}
    )
    hybrid_evidence = (
        loadj(root / HYBRID_EVIDENCE_PATH)
        if (root / HYBRID_EVIDENCE_PATH).is_file()
        else {}
    )
    hybrid_bindings = {
        cap_id: next(
            (
                item
                for item in records
                if item.get("subject_id") == cap_id
            ),
            {},
        )
        for cap_id in HYBRID_CAPABILITY_IDS
    }
    hybrid_binding_invalid = []
    for cap_id, record in hybrid_bindings.items():
        status = record.get("hybrid_editorial_projection_status", {})
        if (
            HYBRID_DECISION_ID not in record.get("source_decision_ids", [])
            or HYBRID_EVIDENCE_PATH
            not in record.get("evidence_artifacts", [])
            or record.get("runtime_conformance") != "EVIDENCE-PENDING"
            or record.get("status") != "PENDING_CURRENT_HOST"
            or record.get("promotion_state")
            != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
            or status.get("profile_id") != HYBRID_PROFILE_ID
            or status.get("contract_id") != HYBRID_CONTRACT_ID
            or status.get("gate_id") != HYBRID_GATE_ID
            or status.get("runtime_status") != "PENDING_CURRENT_HOST"
            or status.get("ci_reference_pass_does_not_promote_runtime")
            is not True
        ):
            hybrid_binding_invalid.append(cap_id)

    if (
        hybrid.get("profile_id") != HYBRID_PROFILE_ID
        or hybrid.get("contract_id") != HYBRID_CONTRACT_ID
        or sorted(hybrid.get("provider_ids", []))
        != sorted([
            HYBRID_KRITA_PROVIDER_ID,
            HYBRID_KDENLIVE_PROVIDER_ID,
        ])
        or hybrid.get("gate_id") != HYBRID_GATE_ID
        or hybrid.get("gateset_id") != HYBRID_GATESET_ID
        or hybrid.get("decision_id") != HYBRID_DECISION_ID
        or hybrid.get("reconciliation_status")
        != HYBRID_RECONCILIATION_STATUS
        or hybrid.get("reference_evidence")
        != HYBRID_EVIDENCE_PATH
        or hybrid.get("reference_evidence_status")
        != "CI_CANONICAL_EXECUTABLE_REFERENCE_E2E_PASS"
        or hybrid.get("current_host_runtime_evidence")
        != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or hybrid.get("current_host_runtime_promotion_claim") is not False
        or hybrid.get("new_capabilities") != 0
        or hybrid.get("new_architectural_authorities") != 0
        or hybrid.get("capability_count_after") != CAPABILITY_COUNT
        or sorted(
            hybrid.get("evidence_registry_capability_bindings", [])
        )
        != sorted(HYBRID_CAPABILITY_IDS)
        or HYBRID_GATESET_ID not in projection_gates
        or HYBRID_GATESET_ID not in policy_gates
        or missing_hybrid_overlay_members
        or hybrid_manifest_missing
        or hybrid_profile.get("id") != HYBRID_PROFILE_ID
        or hybrid_profile.get("status") != "CANONICAL"
        or hybrid_profile.get("new_capability") is not False
        or hybrid_profile.get("new_architectural_authority") is not False
        or hybrid_profile.get("capability_count") != CAPABILITY_COUNT
        or hybrid_contract.get("id") != HYBRID_CONTRACT_ID
        or hybrid_contract.get("provider_neutral") is not True
        or hybrid_contract.get("canonical_timeline_ir")
        != "OpenTimelineIO"
        or hybrid_krita.get("id") != HYBRID_KRITA_PROVIDER_ID
        or hybrid_krita.get("canonical_root") is not False
        or hybrid_krita.get("architectural_authority") is not False
        or hybrid_krita.get("new_capability") is not False
        or hybrid_krita.get("new_architectural_authority") is not False
        or hybrid_krita.get("capability_count") != CAPABILITY_COUNT
        or hybrid_kdenlive.get("id") != HYBRID_KDENLIVE_PROVIDER_ID
        or hybrid_kdenlive.get("architectural_authority") is not False
        or hybrid_kdenlive.get(
            "human_finishing_boundary", {}
        ).get("mode") != "HUMAN_FINISHING_NLE"
        or hybrid_kdenlive.get("ai_tools_policy")
        != "CLIENT_PROJECTION_ONLY_DELEGATE_THROUGH_EXISTING_FA3_CAPABILITIES"
        or hybrid_evidence.get("status") != "PASS"
        or hybrid_evidence.get("gate_id") != HYBRID_GATE_ID
        or hybrid_evidence.get("current_host_runtime_promotion_claim")
        is not False
        or hybrid_binding_invalid
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-027",
                (
                    "Hybrid editorial global release/inventory/evidence "
                    "reconciliation invariant mismatch"
                ),
                reconciliation_status=hybrid.get("reconciliation_status"),
                reference_evidence_status=hybrid.get(
                    "reference_evidence_status"
                ),
                missing_overlay_members=missing_hybrid_overlay_members,
                missing_manifest_paths=hybrid_manifest_missing,
                invalid_capability_bindings=hybrid_binding_invalid,
            )
        )


    marketing = projection.get("marketing_reconciliation", {})
    required_marketing_manifest_paths = {
        MARKETING_PROFILE_PATH,
        MARKETING_CONTRACT_PATH,
        MARKETING_I18N_PATH,
        MARKETING_DECISION_PATH,
        MARKETING_GATE_RECORD_PATH,
        MARKETING_ENFORCEMENT_PATH,
        MARKETING_REFERENCE_PATH,
        MARKETING_EVIDENCE_PATH,
        MARKETING_REFERENCE_RUNTIME_PATH,
        MARKETING_GATE_PATH,
        MARKETING_TEST_PATH,
        MARKETING_COLLECTOR_PATH,
        MARKETING_EXAMPLE_PATH,
        MARKETING_WORKFLOW_PATH,
        "src/fa3_enforce.py",
        "evidence/evidence-registry.json",
        *MARKETING_PROVIDER_PATHS,
    }
    marketing_overlay_requirements = {
        "profile_records": [MARKETING_PROFILE_PATH],
        "contract_records": [MARKETING_CONTRACT_PATH],
        "provider_records": list(MARKETING_PROVIDER_PATHS),
        "decision_records": [MARKETING_DECISION_PATH],
        "upstream_reference_records": [MARKETING_REFERENCE_PATH],
        "reference_evidence_records": [MARKETING_EVIDENCE_PATH],
    }
    missing_marketing_overlay_members = []
    for key, required_paths in marketing_overlay_requirements.items():
        for required in required_paths:
            if required not in inventory.get(key, []):
                missing_marketing_overlay_members.append(
                    {"inventory": key, "path": required}
                )
    marketing_manifest_missing = sorted(
        required_marketing_manifest_paths - manifest_paths
    )
    marketing_profile = (
        loadj(root / MARKETING_PROFILE_PATH)
        if (root / MARKETING_PROFILE_PATH).is_file()
        else {}
    )
    marketing_contract = (
        loadj(root / MARKETING_CONTRACT_PATH)
        if (root / MARKETING_CONTRACT_PATH).is_file()
        else {}
    )
    marketing_i18n = (
        loadj(root / MARKETING_I18N_PATH)
        if (root / MARKETING_I18N_PATH).is_file()
        else {}
    )
    marketing_reference = (
        loadj(root / MARKETING_REFERENCE_PATH)
        if (root / MARKETING_REFERENCE_PATH).is_file()
        else {}
    )
    marketing_evidence = (
        loadj(root / MARKETING_EVIDENCE_PATH)
        if (root / MARKETING_EVIDENCE_PATH).is_file()
        else {}
    )
    marketing_providers = {
        provider_id: loadj(
            root / f"canonical/providers/{provider_id}.json"
        )
        for provider_id in MARKETING_PROVIDER_IDS
        if (
            root / f"canonical/providers/{provider_id}.json"
        ).is_file()
    }
    marketing_provider_invalid = [
        provider_id
        for provider_id in MARKETING_PROVIDER_IDS
        if (
            provider_id not in marketing_providers
            or marketing_providers[provider_id].get("canonical_root")
            is not False
            or marketing_providers[provider_id].get(
                "architectural_authority"
            )
            is not False
            or marketing_providers[provider_id].get("new_capability")
            is not False
            or marketing_providers[provider_id].get(
                "new_architectural_authority"
            )
            is not False
            or marketing_providers[provider_id].get("capability_count")
            != CAPABILITY_COUNT
            or marketing_providers[provider_id].get(
                "runtime_activation_status"
            )
            != "NOT_ADMITTED_PENDING_CURRENT_HOST"
        )
    ]
    marketing_binding_invalid = []
    for cap_id in MARKETING_CAPABILITY_IDS:
        rec = next(
            (
                item
                for item in records
                if item.get("subject_id") == cap_id
            ),
            {},
        )
        status = rec.get("marketing_projection_status", {})
        if (
            MARKETING_DECISION_ID not in rec.get(
                "source_decision_ids", []
            )
            or MARKETING_EVIDENCE_PATH
            not in rec.get("evidence_artifacts", [])
            or rec.get("status") != "PENDING_CURRENT_HOST"
            or rec.get("promotion_state")
            != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
            or status.get("profile_id") != MARKETING_PROFILE_ID
            or status.get("gate_id") != MARKETING_GATE_ID
            or status.get("runtime_status") != "PENDING_CURRENT_HOST"
            or status.get(
                "ci_reference_pass_does_not_promote_runtime"
            )
            is not True
        ):
            marketing_binding_invalid.append(cap_id)

    marketing_sources = {
        item.get("repository"): item
        for item in marketing_reference.get("sources", [])
    }
    if (
        marketing.get("profile_id") != MARKETING_PROFILE_ID
        or marketing.get("contract_id") != MARKETING_CONTRACT_ID
        or marketing.get("i18n_policy_id") != MARKETING_I18N_ID
        or sorted(marketing.get("provider_ids", []))
        != sorted(MARKETING_PROVIDER_IDS)
        or marketing.get("gate_id") != MARKETING_GATE_ID
        or marketing.get("gateset_id") != MARKETING_GATESET_ID
        or marketing.get("decision_id") != MARKETING_DECISION_ID
        or marketing.get("reconciliation_status")
        != MARKETING_RECONCILIATION_STATUS
        or marketing.get("reference_evidence")
        != MARKETING_EVIDENCE_PATH
        or marketing.get("reference_evidence_status")
        != "CI_CANONICAL_EXECUTABLE_REFERENCE_E2E_PASS"
        or marketing.get("current_host_runtime_evidence")
        != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or marketing.get("current_host_runtime_promotion_claim")
        is not False
        or marketing.get("primary_locale") != "hu-HU"
        or marketing.get("fallback_locale") != "en"
        or marketing.get("new_capabilities") != 0
        or marketing.get("new_architectural_authorities") != 0
        or marketing.get("capability_count_after") != CAPABILITY_COUNT
        or sorted(
            marketing.get(
                "evidence_registry_capability_bindings", []
            )
        )
        != sorted(MARKETING_CAPABILITY_IDS)
        or MARKETING_GATESET_ID not in projection_gates
        or MARKETING_GATESET_ID not in policy_gates
        or missing_marketing_overlay_members
        or marketing_manifest_missing
        or marketing_profile.get("id") != MARKETING_PROFILE_ID
        or marketing_profile.get("new_capability") is not False
        or marketing_profile.get("new_architectural_authority")
        is not False
        or marketing_contract.get("id") != MARKETING_CONTRACT_ID
        or marketing_contract.get("provider_neutral") is not True
        or marketing_i18n.get("id") != MARKETING_I18N_ID
        or marketing_i18n.get("primary_locale") != "hu-HU"
        or marketing_i18n.get(
            "native_hungarian_ai_generation_required"
        )
        is not True
        or marketing_i18n.get(
            "translation_only_hungarian_pipeline_forbidden"
        )
        is not True
        or marketing_evidence.get("status") != "PASS"
        or marketing_evidence.get(
            "current_host_runtime_promotion_claim"
        )
        is not False
        or marketing_sources.get(
            "coreyhaines31/marketingskills", {}
        ).get("role")
        != (
            "UNTRUSTED_SCOPED_MARKETING_KNOWLEDGE_AND_PATTERN_SOURCE_"
            "NOT_EXECUTION_AUTHORITY"
        )
        or marketing_provider_invalid
        or marketing_binding_invalid
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-028",
                (
                    "Marketing global release/inventory/evidence "
                    "reconciliation invariant mismatch"
                ),
                reconciliation_status=marketing.get(
                    "reconciliation_status"
                ),
                missing_overlay_members=missing_marketing_overlay_members,
                missing_manifest_paths=marketing_manifest_missing,
                invalid_providers=marketing_provider_invalid,
                invalid_capability_bindings=marketing_binding_invalid,
            )
        )

    stability_sgm = projection.get("stability_sgm_reconciliation", {})
    required_stability_sgm_manifest_paths = {
        STABILITY_SGM_PROVIDER_PATH,
        STABILITY_SGM_CONTRACT_PATH,
        STABILITY_SGM_DECISION_PATH,
        STABILITY_SGM_REFERENCE_PATH,
        STABILITY_SGM_GATE_RECORD_PATH,
        STABILITY_SGM_ENFORCEMENT_PATH,
        STABILITY_SGM_EVIDENCE_PATH,
        STABILITY_SGM_GATE_PATH,
        STABILITY_SGM_TEST_PATH,
    }
    missing_stability_sgm_overlay_members = []
    for key, required in {
        "provider_records": STABILITY_SGM_PROVIDER_PATH,
        "contract_records": STABILITY_SGM_CONTRACT_PATH,
        "decision_records": STABILITY_SGM_DECISION_PATH,
        "upstream_reference_records": STABILITY_SGM_REFERENCE_PATH,
        "reference_evidence_records": STABILITY_SGM_EVIDENCE_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_stability_sgm_overlay_members.append({"inventory": key, "path": required})
    stability_sgm_manifest_missing = sorted(required_stability_sgm_manifest_paths - manifest_paths)
    stability_sgm_provider = (
        loadj(root / STABILITY_SGM_PROVIDER_PATH)
        if (root / STABILITY_SGM_PROVIDER_PATH).is_file()
        else {}
    )
    stability_sgm_evidence = (
        loadj(root / STABILITY_SGM_EVIDENCE_PATH)
        if (root / STABILITY_SGM_EVIDENCE_PATH).is_file()
        else {}
    )
    if (
        stability_sgm.get("provider_id") != STABILITY_SGM_PROVIDER_ID
        or stability_sgm.get("contract_id") != STABILITY_SGM_CONTRACT_ID
        or stability_sgm.get("gate_id") != STABILITY_SGM_GATE_ID
        or stability_sgm.get("reconciliation_status") != STABILITY_SGM_RECONCILIATION_STATUS
        or stability_sgm.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or stability_sgm.get("current_host_provider_runtime_evidence") is not False
        or stability_sgm.get("new_capabilities") != 0
        or stability_sgm.get("new_architectural_authorities") != 0
        or stability_sgm.get("capability_count_after") != CAPABILITY_COUNT
        or STABILITY_SGM_GATE_ID not in projection_gates
        or STABILITY_SGM_GATE_ID not in policy_gates
        or missing_stability_sgm_overlay_members
        or stability_sgm_manifest_missing
        or stability_sgm_provider.get("id") != STABILITY_SGM_PROVIDER_ID
        or stability_sgm_provider.get("architectural_authority") is not False
        or stability_sgm_provider.get("output_semantics", {}).get("canonical_geometry") is not False
        or stability_sgm_evidence.get("status") != "PASS"
        or stability_sgm_evidence.get("current_host_runtime_evidence") is not False
        or stability_sgm_evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-030",
                "Stability SGM global release/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=stability_sgm.get("reconciliation_status"),
                missing_overlay_members=missing_stability_sgm_overlay_members,
                missing_manifest_paths=stability_sgm_manifest_missing,
            )
        )

    opencut = projection.get("opencut_reconciliation", {})
    required_opencut_manifest_paths = {
        OPENCUT_PROFILE_PATH,
        OPENCUT_CONTRACT_PATH,
        OPENCUT_PROVIDER_PATH,
        OPENCUT_DECISION_PATH,
        OPENCUT_REFERENCE_PATH,
        OPENCUT_GATE_RECORD_PATH,
        OPENCUT_ENFORCEMENT_PATH,
        OPENCUT_ADMISSION_PATH,
        OPENCUT_EVIDENCE_PATH,
        OPENCUT_GATE_PATH,
        OPENCUT_TEST_PATH,
        "canonical/enforcement-policy.json",
        "evidence/evidence-registry.json",
        "src/fa3_enforce.py",
    }
    missing_opencut_overlay_members = []
    for key, required in {
        "profile_records": OPENCUT_PROFILE_PATH,
        "contract_records": OPENCUT_CONTRACT_PATH,
        "provider_records": OPENCUT_PROVIDER_PATH,
        "decision_records": OPENCUT_DECISION_PATH,
        "upstream_reference_records": OPENCUT_REFERENCE_PATH,
        "reference_evidence_records": OPENCUT_EVIDENCE_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_opencut_overlay_members.append({"inventory": key, "path": required})
    opencut_manifest_missing = sorted(required_opencut_manifest_paths - manifest_paths)
    opencut_provider = (
        loadj(root / OPENCUT_PROVIDER_PATH)
        if (root / OPENCUT_PROVIDER_PATH).is_file()
        else {}
    )
    opencut_evidence = (
        loadj(root / OPENCUT_EVIDENCE_PATH)
        if (root / OPENCUT_EVIDENCE_PATH).is_file()
        else {}
    )
    opencut_admission = (
        loadj(root / OPENCUT_ADMISSION_PATH)
        if (root / OPENCUT_ADMISSION_PATH).is_file()
        else {}
    )
    opencut_binding_invalid = []
    for capability_id in OPENCUT_CAPABILITY_IDS:
        record = next((item for item in records if item.get("subject_id") == capability_id), {})
        if (
            OPENCUT_DECISION_ID not in record.get("source_decision_ids", [])
            or OPENCUT_EVIDENCE_PATH not in record.get("evidence_artifacts", [])
            or record.get("status") != "PENDING_CURRENT_HOST"
            or record.get("opencut_programmable_editor_projection_status", {}).get("runtime_status")
            != OPENCUT_RUNTIME_STATUS
            or record.get("opencut_programmable_editor_projection_status", {}).get("current_host_runtime_evidence")
            != "NOT_CLAIMED"
        ):
            opencut_binding_invalid.append(capability_id)
    if (
        opencut.get("profile_id") != OPENCUT_PROFILE_ID
        or opencut.get("contract_id") != OPENCUT_CONTRACT_ID
        or opencut.get("provider_id") != OPENCUT_PROVIDER_ID
        or opencut.get("decision_id") != OPENCUT_DECISION_ID
        or opencut.get("gate_id") != OPENCUT_GATE_ID
        or opencut.get("capability_ids") != list(OPENCUT_CAPABILITY_IDS)
        or opencut.get("reconciliation_status") != OPENCUT_RECONCILIATION_STATUS
        or opencut.get("runtime_activation_status") != OPENCUT_RUNTIME_STATUS
        or opencut.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or opencut.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or opencut.get("new_capabilities") != 0
        or opencut.get("new_architectural_authorities") != 0
        or opencut.get("capability_count_after") != CAPABILITY_COUNT
        or OPENCUT_GATE_ID not in projection_gates
        or OPENCUT_GATE_ID not in policy_gates
        or missing_opencut_overlay_members
        or opencut_manifest_missing
        or opencut_binding_invalid
        or opencut_provider.get("id") != OPENCUT_PROVIDER_ID
        or opencut_provider.get("architectural_authority") is not False
        or opencut_provider.get("canonical_root") is not False
        or opencut_provider.get("new_capability") is not False
        or opencut_provider.get("hard_dependency") is not False
        or opencut_provider.get("exclusive_nle") is not False
        or opencut_provider.get("runtime_activation", {}).get("status") != OPENCUT_RUNTIME_STATUS
        or opencut_admission.get("status") != OPENCUT_RUNTIME_STATUS
        or opencut_admission.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or opencut_evidence.get("status") != "PASS"
        or opencut_evidence.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or opencut_evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-031",
                "OpenCut global release/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=opencut.get("reconciliation_status"),
                runtime_activation_status=opencut.get("runtime_activation_status"),
                missing_overlay_members=missing_opencut_overlay_members,
                missing_manifest_paths=opencut_manifest_missing,
                invalid_capability_bindings=opencut_binding_invalid,
            )
        )

    openhands = projection.get("openhands_reconciliation", {})
    required_openhands_manifest_paths = {
        OPENHANDS_PROVIDER_PATH,
        OPENHANDS_CONTRACT_PATH,
        OPENHANDS_DECISION_PATH,
        OPENHANDS_REFERENCE_PATH,
        OPENHANDS_GATE_RECORD_PATH,
        OPENHANDS_ENFORCEMENT_PATH,
        OPENHANDS_ADMISSION_PATH,
        OPENHANDS_EVIDENCE_PATH,
        OPENHANDS_GATE_PATH,
        OPENHANDS_TEST_PATH,
        "canonical/enforcement-policy.json",
        "evidence/evidence-registry.json",
        "src/fa3_enforce.py",
        "src/fa3_release_projection_gate.py",
        "tests/test_release_projection.py",
        ".github/workflows/fa3-permanent-enforcement.yml",
    }
    missing_openhands_overlay_members = []
    for key, required in {
        "provider_records": OPENHANDS_PROVIDER_PATH,
        "contract_records": OPENHANDS_CONTRACT_PATH,
        "decision_records": OPENHANDS_DECISION_PATH,
        "upstream_reference_records": OPENHANDS_REFERENCE_PATH,
        "reference_evidence_records": OPENHANDS_EVIDENCE_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_openhands_overlay_members.append({"inventory": key, "path": required})
    openhands_manifest_missing = sorted(required_openhands_manifest_paths - manifest_paths)
    openhands_provider = (
        loadj(root / OPENHANDS_PROVIDER_PATH)
        if (root / OPENHANDS_PROVIDER_PATH).is_file()
        else {}
    )
    openhands_evidence = (
        loadj(root / OPENHANDS_EVIDENCE_PATH)
        if (root / OPENHANDS_EVIDENCE_PATH).is_file()
        else {}
    )
    openhands_admission = (
        loadj(root / OPENHANDS_ADMISSION_PATH)
        if (root / OPENHANDS_ADMISSION_PATH).is_file()
        else {}
    )
    openhands_record = next(
        (item for item in records if item.get("subject_id") == OPENHANDS_CAPABILITY_ID),
        {},
    )
    openhands_projection_status = openhands_record.get(
        "openhands_provider_projection_status", {}
    )
    openhands_binding_invalid = not (
        OPENHANDS_DECISION_ID in openhands_record.get("source_decision_ids", [])
        and OPENHANDS_EVIDENCE_PATH in openhands_record.get("evidence_artifacts", [])
        and openhands_record.get("status") == "PENDING_CURRENT_HOST"
        and openhands_projection_status.get("provider_id") == OPENHANDS_PROVIDER_ID
        and openhands_projection_status.get("runtime_activation_status")
        == OPENHANDS_RUNTIME_STATUS
        and openhands_projection_status.get("current_host_runtime_evidence")
        == "NOT_CLAIMED"
    )
    if (
        openhands.get("provider_id") != OPENHANDS_PROVIDER_ID
        or openhands.get("contract_id") != OPENHANDS_CONTRACT_ID
        or openhands.get("decision_id") != OPENHANDS_DECISION_ID
        or openhands.get("gate_id") != OPENHANDS_GATE_ID
        or openhands.get("capability_id") != OPENHANDS_CAPABILITY_ID
        or openhands.get("reconciliation_status") != OPENHANDS_RECONCILIATION_STATUS
        or openhands.get("runtime_activation_status") != OPENHANDS_RUNTIME_STATUS
        or openhands.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or openhands.get("provider_runtime_required_for_global_promotion_when_disabled")
        is not False
        or openhands.get("new_capabilities") != 0
        or openhands.get("new_architectural_authorities") != 0
        or openhands.get("capability_count_after") != CAPABILITY_COUNT
        or OPENHANDS_GATE_ID not in projection_gates
        or OPENHANDS_GATE_ID not in policy_gates
        or missing_openhands_overlay_members
        or openhands_manifest_missing
        or openhands_binding_invalid
        or openhands_provider.get("id") != OPENHANDS_PROVIDER_ID
        or openhands_provider.get("architectural_authority") is not False
        or openhands_provider.get("canonical_root") is not False
        or openhands_provider.get("new_capability") is not False
        or openhands_provider.get("new_architectural_authority") is not False
        or openhands_provider.get("runtime_activation_status") != OPENHANDS_RUNTIME_STATUS
        or openhands_admission.get("status") != OPENHANDS_RUNTIME_STATUS
        or openhands_admission.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or openhands_admission.get("production_provider_admission") is not False
        or openhands_evidence.get("status") != "PASS"
        or openhands_evidence.get("current_host_provider_runtime_evidence") is not False
        or openhands_evidence.get("current_host_runtime_promotion_claim") is not False
        or openhands_evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-032",
                "OpenHands global release/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=openhands.get("reconciliation_status"),
                runtime_activation_status=openhands.get("runtime_activation_status"),
                missing_overlay_members=missing_openhands_overlay_members,
                missing_manifest_paths=openhands_manifest_missing,
                invalid_capability_binding=openhands_binding_invalid,
            )
        )


    loop_engineering = projection.get("loop_engineering_reconciliation", {})
    required_loop_manifest_paths = {
        LOOP_PROFILE_PATH,
        LOOP_CONTRACT_PATH,
        LOOP_PROVIDER_PATH,
        LOOP_DECISION_PATH,
        LOOP_REFERENCE_PATH,
        LOOP_GATE_RECORD_PATH,
        LOOP_ENFORCEMENT_PATH,
        LOOP_ADMISSION_PATH,
        LOOP_EVIDENCE_PATH,
        LOOP_REFERENCE_IMPL_PATH,
        LOOP_GATE_PATH,
        LOOP_TEST_PATH,
        "canonical/enforcement-policy.json",
        "evidence/evidence-registry.json",
        "src/fa3_enforce.py",
        "src/fa3_release_projection_gate.py",
        "tests/test_release_projection.py",
        ".github/workflows/fa3-permanent-enforcement.yml",
    }
    loop_inventory_requirements = {
        "profile_records": LOOP_PROFILE_PATH,
        "contract_records": LOOP_CONTRACT_PATH,
        "provider_records": LOOP_PROVIDER_PATH,
        "decision_records": LOOP_DECISION_PATH,
        "upstream_reference_records": LOOP_REFERENCE_PATH,
        "reference_evidence_records": LOOP_EVIDENCE_PATH,
    }
    missing_loop_overlay_members = [
        {"inventory": key, "path": path}
        for key, path in loop_inventory_requirements.items()
        if path not in inventory.get(key, [])
    ]
    loop_manifest_missing = sorted(required_loop_manifest_paths - manifest_paths)
    loop_provider = loadj(root / LOOP_PROVIDER_PATH) if (root / LOOP_PROVIDER_PATH).is_file() else {}
    loop_evidence = loadj(root / LOOP_EVIDENCE_PATH) if (root / LOOP_EVIDENCE_PATH).is_file() else {}
    loop_admission = loadj(root / LOOP_ADMISSION_PATH) if (root / LOOP_ADMISSION_PATH).is_file() else {}
    loop_record = next(
        (item for item in records if item.get("subject_id") == LOOP_CAPABILITY_ID),
        {},
    )
    loop_projection_status = loop_record.get("loop_engineering_provider_projection_status", {})
    loop_binding_invalid = not (
        LOOP_DECISION_ID in loop_record.get("source_decision_ids", [])
        and LOOP_EVIDENCE_PATH in loop_record.get("evidence_artifacts", [])
        and loop_record.get("status") == "PENDING_CURRENT_HOST"
        and loop_projection_status.get("provider_id") == LOOP_PROVIDER_ID
        and loop_projection_status.get("runtime_activation_status") == LOOP_RUNTIME_STATUS
        and loop_projection_status.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and loop_projection_status.get("reference_evidence") == LOOP_EVIDENCE_PATH
    )
    if (
        loop_engineering.get("profile_id") != LOOP_PROFILE_ID
        or loop_engineering.get("contract_id") != LOOP_CONTRACT_ID
        or loop_engineering.get("provider_id") != LOOP_PROVIDER_ID
        or loop_engineering.get("decision_id") != LOOP_DECISION_ID
        or loop_engineering.get("gate_id") != LOOP_GATE_ID
        or loop_engineering.get("capability_id") != LOOP_CAPABILITY_ID
        or loop_engineering.get("reconciliation_status") != LOOP_RECONCILIATION_STATUS
        or loop_engineering.get("runtime_activation_status") != LOOP_RUNTIME_STATUS
        or loop_engineering.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or loop_engineering.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or loop_engineering.get("reference_evidence_status") != "PASS"
        or loop_engineering.get("upstream_reference_commit") != LOOP_UPSTREAM_PIN
        or loop_engineering.get("new_capabilities") != 0
        or loop_engineering.get("new_architectural_authorities") != 0
        or loop_engineering.get("capability_count_after") != CAPABILITY_COUNT
        or LOOP_GATE_ID not in projection_gates
        or LOOP_GATE_ID not in policy_gates
        or missing_loop_overlay_members
        or loop_manifest_missing
        or loop_binding_invalid
        or loop_provider.get("id") != LOOP_PROVIDER_ID
        or loop_provider.get("architectural_authority") is not False
        or loop_provider.get("canonical_root") is not False
        or loop_provider.get("new_capability") is not False
        or loop_provider.get("new_architectural_authority") is not False
        or loop_provider.get("runtime_activation_status") != LOOP_RUNTIME_STATUS
        or loop_provider.get("immutable_upstream_tuple", {}).get("commit") != LOOP_UPSTREAM_PIN
        or loop_admission.get("status") != LOOP_RUNTIME_STATUS
        or loop_admission.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or loop_admission.get("production_provider_admission") is not False
        or loop_evidence.get("status") != "PASS"
        or loop_evidence.get("current_host_provider_runtime_evidence") is not False
        or loop_evidence.get("current_host_runtime_promotion_claim") is not False
        or loop_evidence.get("production_provider_admission_claim") is not False
        or loop_evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-036",
                "Closed-loop agent operations / Loop Engineering global release, inventory and evidence reconciliation invariant mismatch",
                reconciliation_status=loop_engineering.get("reconciliation_status"),
                runtime_activation_status=loop_engineering.get("runtime_activation_status"),
                missing_overlay_members=missing_loop_overlay_members,
                missing_manifest_paths=loop_manifest_missing,
                invalid_capability_binding=loop_binding_invalid,
            )
        )


    tdai = projection.get("tencentdb_agent_memory_reconciliation", {})
    tdai_required_paths = {TDAI_PROVIDER_PATH,TDAI_CONTRACT_PATH,TDAI_DECISION_PATH,TDAI_REFERENCE_PATH,TDAI_GATE_RECORD_PATH,TDAI_ENFORCEMENT_PATH,TDAI_ADMISSION_PATH,TDAI_EVIDENCE_PATH,TDAI_GATE_PATH,TDAI_TEST_PATH,"canonical/enforcement-policy.json","canonical/profiles/FA3-KNOWLEDGE-001.json","evidence/evidence-registry.json","src/fa3_enforce.py","src/fa3_release_projection_gate.py","tests/test_release_projection.py",".github/workflows/fa3-permanent-enforcement.yml"}
    tdai_inventory_requirements={"provider_records":[TDAI_PROVIDER_PATH],"contract_records":[TDAI_CONTRACT_PATH],"decision_records":[TDAI_DECISION_PATH],"upstream_reference_records":[TDAI_REFERENCE_PATH],"reference_evidence_records":[TDAI_EVIDENCE_PATH]}
    missing_tdai_inventory=[{"inventory":key,"path":path} for key,paths in tdai_inventory_requirements.items() for path in paths if path not in inventory.get(key,[])]
    missing_tdai_manifest=sorted(tdai_required_paths-manifest_paths)
    tdai_provider=loadj(root/TDAI_PROVIDER_PATH) if (root/TDAI_PROVIDER_PATH).is_file() else {}
    tdai_admission=loadj(root/TDAI_ADMISSION_PATH) if (root/TDAI_ADMISSION_PATH).is_file() else {}
    tdai_evidence=loadj(root/TDAI_EVIDENCE_PATH) if (root/TDAI_EVIDENCE_PATH).is_file() else {}
    invalid_tdai_bindings=[]
    for capability_id in TDAI_CAPABILITY_IDS:
        record=next((item for item in records if item.get("subject_id")==capability_id),{})
        ps=record.get("tencentdb_agent_memory_projection_status",{})
        if (TDAI_DECISION_ID not in record.get("source_decision_ids",[]) or TDAI_EVIDENCE_PATH not in record.get("evidence_artifacts",[]) or record.get("status")!="PENDING_CURRENT_HOST" or ps.get("provider_id")!=TDAI_PROVIDER_ID or ps.get("runtime_activation_status")!=TDAI_RUNTIME_STATUS or ps.get("current_host_runtime_evidence")!="NOT_CLAIMED" or ps.get("production_provider_admission") is not False): invalid_tdai_bindings.append(capability_id)
    if (tdai.get("provider_id")!=TDAI_PROVIDER_ID or tdai.get("contract_id")!=TDAI_CONTRACT_ID or tdai.get("decision_id")!=TDAI_DECISION_ID or tdai.get("gate_id")!=TDAI_GATE_ID or tdai.get("capability_bindings")!=list(TDAI_CAPABILITY_IDS) or tdai.get("reconciliation_status")!=TDAI_RECONCILIATION_STATUS or tdai.get("runtime_activation_status")!=TDAI_RUNTIME_STATUS or tdai.get("current_host_runtime_evidence")!="NOT_CLAIMED" or tdai.get("current_host_runtime_promotion_claim") is not False or tdai.get("production_provider_admission") is not False or tdai.get("provider_runtime_required_for_global_promotion_when_disabled") is not False or tdai.get("new_capabilities")!=0 or tdai.get("new_architectural_authorities")!=0 or tdai.get("capability_count_after")!=CAPABILITY_COUNT or TDAI_GATE_ID not in projection_gates or TDAI_GATE_ID not in policy_gates or missing_tdai_inventory or missing_tdai_manifest or invalid_tdai_bindings or tdai_provider.get("id")!=TDAI_PROVIDER_ID or tdai_provider.get("canonical_root") is not False or tdai_provider.get("architectural_authority") is not False or tdai_provider.get("new_capability") is not False or tdai_provider.get("new_architectural_authority") is not False or tdai_provider.get("runtime_activation_status")!=TDAI_RUNTIME_STATUS or tdai_admission.get("status")!=TDAI_RUNTIME_STATUS or tdai_admission.get("current_host_runtime_evidence")!="NOT_CLAIMED" or tdai_admission.get("production_provider_admission") is not False or tdai_evidence.get("status")!="PASS" or tdai_evidence.get("security_runtime_admission_pass") is not False or tdai_evidence.get("license_runtime_admission_pass") is not False or tdai_evidence.get("current_host_provider_runtime_evidence") is not False or tdai_evidence.get("production_provider_admission_claim") is not False):
        findings.append(finding("FA3-RELEASE-PROJECTION-034","TencentDB Agent Memory global release/inventory/evidence reconciliation invariant mismatch",reconciliation_status=tdai.get("reconciliation_status"),runtime_activation_status=tdai.get("runtime_activation_status"),missing_inventory=missing_tdai_inventory,missing_manifest_paths=missing_tdai_manifest,invalid_capability_bindings=invalid_tdai_bindings))

    voice = projection.get("voice_synthesis_reconciliation", {})
    voice_required_paths = {
        VOICE_PROFILE_PATH,
        VOICE_CONTRACT_PATH,
        VOICE_ADMISSION_PATH,
        VOICE_DECISION_PATH,
        VOICE_REFERENCE_PATH,
        VOICE_ENFORCEMENT_PATH,
        VOICE_EVIDENCE_PATH,
        VOICE_GATE_PATH,
        VOICE_TEST_PATH,
        *VOICE_PROVIDER_PATHS,
    }
    voice_inventory_requirements = {
        "profile_records": [VOICE_PROFILE_PATH],
        "contract_records": [VOICE_CONTRACT_PATH],
        "provider_records": list(VOICE_PROVIDER_PATHS),
        "decision_records": [VOICE_DECISION_PATH],
        "upstream_reference_records": [VOICE_REFERENCE_PATH],
        "reference_evidence_records": [VOICE_EVIDENCE_PATH],
    }
    missing_voice_inventory = [
        {"inventory": key, "path": path}
        for key, paths in voice_inventory_requirements.items()
        for path in paths
        if path not in inventory.get(key, [])
    ]
    missing_voice_manifest = sorted(voice_required_paths - manifest_paths)
    voice_providers = [loadj(root / path) if (root / path).is_file() else {} for path in VOICE_PROVIDER_PATHS]
    voice_evidence = loadj(root / VOICE_EVIDENCE_PATH) if (root / VOICE_EVIDENCE_PATH).is_file() else {}
    invalid_voice_bindings = []
    for capability_id in VOICE_CAPABILITY_IDS:
        record = next((item for item in records if item.get("subject_id") == capability_id), {})
        if (
            VOICE_DECISION_ID not in record.get("source_decision_ids", [])
            or VOICE_EVIDENCE_PATH not in record.get("evidence_artifacts", [])
            or record.get("status") != "PENDING_CURRENT_HOST"
        ):
            invalid_voice_bindings.append(capability_id)
    if (
        voice.get("profile_id") != VOICE_PROFILE_ID
        or voice.get("contract_id") != VOICE_CONTRACT_ID
        or voice.get("admission_id") != VOICE_ADMISSION_ID
        or voice.get("decision_id") != VOICE_DECISION_ID
        or voice.get("gate_id") != VOICE_GATE_ID
        or voice.get("provider_ids") != list(VOICE_PROVIDER_IDS)
        or voice.get("capability_bindings") != list(VOICE_CAPABILITY_IDS)
        or voice.get("reconciliation_status") != VOICE_RECONCILIATION_STATUS
        or voice.get("current_host_runtime_evidence") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or voice.get("hungarian_quality_evidence") != "PENDING_DEDICATED_HU_HU_GOLDEN_CORPUS"
        or voice.get("current_host_runtime_promotion_claim") is not False
        or voice.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or voice.get("new_capabilities") != 0
        or voice.get("new_architectural_authorities") != 0
        or voice.get("capability_count_after") != CAPABILITY_COUNT
        or VOICE_GATE_ID not in projection_gates
        or VOICE_GATE_ID not in policy_gates
        or missing_voice_inventory
        or missing_voice_manifest
        or invalid_voice_bindings
        or any(provider.get("id") != provider_id for provider, provider_id in zip(voice_providers, VOICE_PROVIDER_IDS))
        or any(provider.get("canonical_root") is not False or provider.get("architectural_authority") is not False or provider.get("new_capability") is not False for provider in voice_providers)
        or voice_evidence.get("result") != "PASS"
        or voice_evidence.get("current_host_production_claim") is not False
        or voice_evidence.get("hungarian_quality_claim") is not False
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-033",
                "Voice synthesis portfolio global release/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=voice.get("reconciliation_status"),
                missing_inventory=missing_voice_inventory,
                missing_manifest_paths=missing_voice_manifest,
                invalid_capability_bindings=invalid_voice_bindings,
            )
        )


    gpuk = projection.get("gpu_kernel_runtime_reconciliation", {})
    gpuk_required_paths = {
        GPUK_PROFILE_PATH, GPUK_CONTRACT_PATH, GPUK_AMPERE_PROVIDER_PATH,
        GPUK_DEEPGEMM_PROVIDER_PATH, GPUK_DECISION_PATH, GPUK_REFERENCE_PATH,
        GPUK_EVIDENCE_PATH, GPUK_ENFORCEMENT_PATH, GPUK_ADMISSION_PATH,
        GPUK_GATE_RECORD_PATH, GPUK_CURRENT_HOST_GATE_RECORD_PATH, GPUK_GATE_PATH,
        GPUK_DISPATCH_PATH, GPUK_TEST_PATH, GPUK_COLLECTOR_PATH, GPUK_BENCH_PATH,
        "canonical/enforcement-policy.json", "evidence/evidence-registry.json",
        "src/fa3_enforce.py", "src/fa3_release_projection_gate.py",
    }
    missing_gpuk_manifest = sorted(gpuk_required_paths - manifest_paths)
    gpuk_profile = loadj(root / GPUK_PROFILE_PATH) if (root / GPUK_PROFILE_PATH).is_file() else {}
    gpuk_contract = loadj(root / GPUK_CONTRACT_PATH) if (root / GPUK_CONTRACT_PATH).is_file() else {}
    gpuk_ampere = loadj(root / GPUK_AMPERE_PROVIDER_PATH) if (root / GPUK_AMPERE_PROVIDER_PATH).is_file() else {}
    gpuk_deepgemm = loadj(root / GPUK_DEEPGEMM_PROVIDER_PATH) if (root / GPUK_DEEPGEMM_PROVIDER_PATH).is_file() else {}
    gpuk_reference = loadj(root / GPUK_REFERENCE_PATH) if (root / GPUK_REFERENCE_PATH).is_file() else {}
    gpuk_evidence = loadj(root / GPUK_EVIDENCE_PATH) if (root / GPUK_EVIDENCE_PATH).is_file() else {}
    gpuk_admission = loadj(root / GPUK_ADMISSION_PATH) if (root / GPUK_ADMISSION_PATH).is_file() else {}
    invalid_gpuk_bindings = []
    for capability_id in GPUK_CAPABILITY_IDS:
        record = next((item for item in records if item.get("subject_id") == capability_id), {})
        ps = record.get("gpu_kernel_runtime_projection_status", {})
        if (
            GPUK_DECISION_ID not in record.get("source_decision_ids", [])
            or GPUK_EVIDENCE_PATH not in record.get("evidence_artifacts", [])
            or record.get("status") != "PENDING_CURRENT_HOST"
            or ps.get("profile_id") != GPUK_PROFILE_ID
            or ps.get("gate_id") != GPUK_GATE_ID
            or ps.get("current_host_runtime_evidence") != "NOT_CLAIMED"
            or ps.get("production_provider_admission") is not False
            or ps.get("ampere_sm86_status") != "REQUIRED_SUPPORTED_PENDING_REAL_CURRENT_HOST_E2E"
            or ps.get("deepgemm_status") != "INELIGIBLE_CURRENT_SM86"
            or ps.get("global_runtime_promotion_claim") is not False
        ):
            invalid_gpuk_bindings.append(capability_id)
    reference_host = gpuk_admission.get("reference_host", {})
    if (
        gpuk.get("profile_id") != GPUK_PROFILE_ID
        or gpuk.get("contract_id") != GPUK_CONTRACT_ID
        or gpuk.get("decision_id") != GPUK_DECISION_ID
        or gpuk.get("gate_id") != GPUK_GATE_ID
        or gpuk.get("provider_ids") != [GPUK_AMPERE_PROVIDER_ID, GPUK_DEEPGEMM_PROVIDER_ID]
        or gpuk.get("capability_bindings") != list(GPUK_CAPABILITY_IDS)
        or gpuk.get("evidence_registry_capability_bindings") != list(GPUK_CAPABILITY_IDS)
        or gpuk.get("reconciliation_status") != GPUK_RECONCILIATION_STATUS
        or gpuk.get("runtime_activation_status") != "SM86_PROVIDER_NOT_ADMITTED_DEEPGEMM_INELIGIBLE"
        or gpuk.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or gpuk.get("current_host_runtime_promotion_claim") is not False
        or gpuk.get("new_capabilities") != 0
        or gpuk.get("new_architectural_authorities") != 0
        or gpuk.get("capability_count_after") != CAPABILITY_COUNT
        or GPUK_GATE_ID not in projection_gates
        or GPUK_GATE_ID not in policy_gates
        or missing_gpuk_manifest
        or invalid_gpuk_bindings
        or gpuk_profile.get("id") != GPUK_PROFILE_ID
        or gpuk_profile.get("requirement") != "MUST"
        or gpuk_profile.get("canonical_root") is not False
        or gpuk_profile.get("new_capability") is not False
        or gpuk_profile.get("new_architectural_authority") is not False
        or gpuk_profile.get("capability_count") != CAPABILITY_COUNT
        or gpuk_contract.get("id") != GPUK_CONTRACT_ID
        or gpuk_contract.get("provider_neutral") is not True
        or gpuk_ampere.get("id") != GPUK_AMPERE_PROVIDER_ID
        or gpuk_ampere.get("architectural_authority") is not False
        or gpuk_ampere.get("target_architectures") != ["SM86"]
        or gpuk_ampere.get("runtime_activation_status") != "BLOCKED_PENDING_REAL_T7910_SM86_CORRECTNESS_BENCHMARK_ROLLBACK_EVIDENCE"
        or gpuk_deepgemm.get("id") != GPUK_DEEPGEMM_PROVIDER_ID
        or gpuk_deepgemm.get("architectural_authority") is not False
        or set(gpuk_deepgemm.get("observed_architecture_support", [])) != {"SM90", "SM100"}
        or gpuk_deepgemm.get("runtime_activation_status") != "DENIED_ON_CURRENT_HOST_UNSUPPORTED_SM86"
        or gpuk_deepgemm.get("immutable_upstream", {}).get("commit") != GPUK_DEEPGEMM_PIN
        or gpuk_reference.get("primary_snapshot", {}).get("commit") != GPUK_DEEPGEMM_PIN
        or gpuk_reference.get("floating_main_allowed_as_promotion_evidence") is not False
        or gpuk_evidence.get("status") != "PASS"
        or gpuk_evidence.get("current_host_provider_runtime_evidence") is not False
        or gpuk_evidence.get("current_host_runtime_promotion_claim") is not False
        or gpuk_admission.get("hardware_semantics") != "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT"
        or reference_host.get("cpu") != "2x Intel Xeon E5-2696 v4 @ 2.20 GHz"
        or reference_host.get("physical_cores") != 44
        or reference_host.get("logical_cpus") != 88
        or reference_host.get("expected_numa_domains") != 2
        or "RTX 3080" not in reference_host.get("compute_gpu", "")
        or gpuk_admission.get("current_host_provider_disposition", {}).get(GPUK_DEEPGEMM_PROVIDER_ID) != "DENIED_UNSUPPORTED_SM86"
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-035",
                "GPU kernel runtime/DeepGEMM global release, hardware, inventory and evidence reconciliation invariant mismatch",
                reconciliation_status=gpuk.get("reconciliation_status"),
                runtime_activation_status=gpuk.get("runtime_activation_status"),
                missing_manifest_paths=missing_gpuk_manifest,
                invalid_capability_bindings=invalid_gpuk_bindings,
            )
        )


    vplc = projection.get("video_provider_lifecycle_reconciliation", {})
    vplc_required_paths = {
        VPLC_PROFILE_PATH, VPLC_CONTRACT_PATH, VPLC_OPEN_SORA_PROVIDER_PATH,
        VPLC_HELIOS_PROVIDER_PATH, VPLC_DECISION_PATH, VPLC_REFERENCE_PATH,
        VPLC_GATE_RECORD_PATH, VPLC_ENFORCEMENT_PATH, VPLC_ADMISSION_PATH,
        VPLC_EVIDENCE_PATH, VPLC_GATE_PATH, VPLC_TEST_PATH,
        "canonical/video-enforcement.json", "canonical/enforcement-policy.json",
        "evidence/evidence-registry.json", "src/fa3_enforce.py",
        "src/fa3_release_projection_gate.py", "README.md",
        ".github/workflows/fa3-permanent-enforcement.yml",
    }
    missing_vplc_manifest = sorted(vplc_required_paths - manifest_paths)
    vplc_profile = loadj(root / VPLC_PROFILE_PATH) if (root / VPLC_PROFILE_PATH).is_file() else {}
    vplc_contract = loadj(root / VPLC_CONTRACT_PATH) if (root / VPLC_CONTRACT_PATH).is_file() else {}
    vplc_open_sora = loadj(root / VPLC_OPEN_SORA_PROVIDER_PATH) if (root / VPLC_OPEN_SORA_PROVIDER_PATH).is_file() else {}
    vplc_helios = loadj(root / VPLC_HELIOS_PROVIDER_PATH) if (root / VPLC_HELIOS_PROVIDER_PATH).is_file() else {}
    vplc_reference = loadj(root / VPLC_REFERENCE_PATH) if (root / VPLC_REFERENCE_PATH).is_file() else {}
    vplc_evidence = loadj(root / VPLC_EVIDENCE_PATH) if (root / VPLC_EVIDENCE_PATH).is_file() else {}
    vplc_admission = loadj(root / VPLC_ADMISSION_PATH) if (root / VPLC_ADMISSION_PATH).is_file() else {}
    video_enforcement = loadj(root / "canonical/video-enforcement.json") if (root / "canonical/video-enforcement.json").is_file() else {}
    invalid_vplc_bindings = []
    for capability_id in VPLC_CAPABILITY_IDS:
        record = next((item for item in records if item.get("subject_id") == capability_id), {})
        ps = record.get("pku_yuan_video_provider_lifecycle_projection_status", {})
        if (
            VPLC_DECISION_ID not in record.get("source_decision_ids", [])
            or VPLC_EVIDENCE_PATH not in record.get("evidence_artifacts", [])
            or record.get("status") != "PENDING_CURRENT_HOST"
            or record.get("promotion_state") != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
            or ps.get("profile_id") != VPLC_PROFILE_ID
            or ps.get("contract_id") != VPLC_CONTRACT_ID
            or ps.get("provider_ids") != list(VPLC_PROVIDER_IDS)
            or ps.get("gate_id") != VPLC_GATE_ID
            or ps.get("current_host_runtime_evidence") != "NOT_CLAIMED"
            or ps.get("production_provider_admission") is not False
            or ps.get("ci_reference_pass_does_not_promote_runtime") is not True
        ):
            invalid_vplc_bindings.append(capability_id)
    if (
        vplc.get("profile_id") != VPLC_PROFILE_ID
        or vplc.get("contract_id") != VPLC_CONTRACT_ID
        or vplc.get("provider_ids") != list(VPLC_PROVIDER_IDS)
        or vplc.get("decision_id") != VPLC_DECISION_ID
        or vplc.get("gate_id") != VPLC_GATE_ID
        or vplc.get("executable_gate_id") != VPLC_EXECUTABLE_GATE_ID
        or vplc.get("capability_bindings") != list(VPLC_CAPABILITY_IDS)
        or vplc.get("reconciliation_status") != VPLC_RECONCILIATION_STATUS
        or vplc.get("reference_evidence") != VPLC_EVIDENCE_PATH
        or vplc.get("reference_evidence_status") != "CI_REFERENCE_EXECUTABLE_REGRESSION_PASS"
        or vplc.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or vplc.get("production_provider_admission") is not False
        or vplc.get("current_host_runtime_promotion_claim") is not False
        or vplc.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or vplc.get("new_capabilities") != 0
        or vplc.get("new_architectural_authorities") != 0
        or vplc.get("capability_count_after") != CAPABILITY_COUNT
        or VPLC_GATE_ID not in projection_gates
        or VPLC_GATE_ID not in policy_gates
        or missing_vplc_manifest
        or invalid_vplc_bindings
        or vplc_contract.get("id") != VPLC_CONTRACT_ID
        or vplc_contract.get("provider_neutral") is not True
        or vplc_open_sora.get("id") != VPLC_OPEN_SORA_PROVIDER_ID
        or vplc_open_sora.get("canonical_root") is not False
        or vplc_open_sora.get("architectural_authority") is not False
        or vplc_open_sora.get("upstream", {}).get("immutable_commit") != VPLC_OPEN_SORA_PIN
        or vplc_open_sora.get("runtime_activation_status") != "NOT_ADMITTED_REFERENCE_ONLY_PENDING_LICENSE_BACKEND_CURRENT_HOST"
        or vplc_open_sora.get("license_admission", {}).get("mode") != "FAIL_CLOSED_METADATA_DRIFT"
        or vplc_helios.get("id") != VPLC_HELIOS_PROVIDER_ID
        or vplc_helios.get("canonical_root") is not False
        or vplc_helios.get("architectural_authority") is not False
        or vplc_helios.get("upstream", {}).get("immutable_commit") != VPLC_HELIOS_PIN
        or vplc_helios.get("runtime_activation_status") != "NOT_ADMITTED_PENDING_MODEL_LICENSE_RESOURCE_CURRENT_HOST_E2E"
        or vplc_helios.get("resource_policy", {}).get("host_ram_and_cgroup_preflight_required") is not True
        or vplc_reference.get("open_sora_plan", {}).get("immutable_observed_commit") != VPLC_OPEN_SORA_PIN
        or vplc_reference.get("helios", {}).get("immutable_observed_commit") != VPLC_HELIOS_PIN
        or vplc_reference.get("promotion_evidence") is not False
        or vplc_evidence.get("status") != "PASS"
        or vplc_evidence.get("regression_cases_total") != 30
        or vplc_evidence.get("regression_cases_passed") != 30
        or vplc_evidence.get("current_host_provider_runtime_evidence") is not False
        or vplc_evidence.get("production_provider_admission_claim") is not False
        or vplc_admission.get("production_provider_admission") is not False
        or vplc_admission.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or vplc_admission.get("global_promotion_claim") is not False
        or VPLC_CONTRACT_ID not in vplc_profile.get("contracts", [])
        or not all(provider_id in vplc_profile.get("providers", []) for provider_id in VPLC_PROVIDER_IDS)
        or video_enforcement.get("provider_lifecycle_gate") != VPLC_GATE_ID
        or video_enforcement.get("provider_lifecycle_contract") != VPLC_CONTRACT_ID
        or not all(provider_id in video_enforcement.get("provider_ids", []) for provider_id in VPLC_PROVIDER_IDS)
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-036",
                "PKU-Yuan video provider lifecycle/backend/cache global reconciliation invariant mismatch",
                reconciliation_status=vplc.get("reconciliation_status"),
                missing_manifest_paths=missing_vplc_manifest,
                invalid_capability_bindings=invalid_vplc_bindings,
            )
        )

    missing = []
    drift = []
    for entry in manifest:
        rel = entry.get("path")
        expected = entry.get("git_blob_sha")
        if not rel or not expected:
            drift.append(rel)
            continue
        path = root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        actual = git_blob_sha(path)
        if actual != expected:
            drift.append({"path": rel, "expected": expected, "actual": actual})

    if missing:
        findings.append(finding("FA3-RELEASE-PROJECTION-009", "Projected file missing", count=len(missing), sample=missing[:20]))
    if drift:
        findings.append(finding("FA3-RELEASE-PROJECTION-010", "Projected Git-blob identity drift", count=len(drift), sample=drift[:20]))

    self_hash = projection.get("self_hash_policy", {})
    if (
        self_hash.get("excluded_path") != PROJECTION_PATH
        or self_hash.get("reason") != "SELF_REFERENTIAL_HASH_EXCLUSION"
        or not (root / PROJECTION_PATH).is_file()
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-011", "Projection self-hash exclusion is invalid"))

    if (
        decision.get("id") != "FA3-DEC-UNIFIED-POST-V3.0.11-PROJECTION-2026-08-30"
        or decision.get("status") != "CANONICAL"
        or decision.get("capability_count_after") != CAPABILITY_COUNT
        or decision.get("new_capabilities") != 0
        or decision.get("new_architectural_authorities") != 0
        or decision.get("projection_id") != PROJECTION_ID
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-012", "Canonical projection decision invariant mismatch"))

    promotion = projection.get("promotion", {})
    if (
        promotion.get("fail_closed") is not True
        or promotion.get("current_host_evidence_required") is not True
        or promotion.get("acceptance_criteria_required") != 19
        or promotion.get("document_only_promotion_forbidden") is not True
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-013", "Promotion safety semantics weakened"))

    tracked_surface = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == PROJECTION_PATH or is_mutable_runtime_path(rel):
            continue
        tracked_surface.append(rel)
    unmanifested = sorted(set(tracked_surface) - manifest_paths)
    if unmanifested:
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-014",
                "Repository release-surface contains unmanifested file",
                count=len(unmanifested),
                sample=unmanifested[:20],
            )
        )

    scope = projection.get("manifest_scope", {})
    if (
        scope.get("repository_release_surface_complete") is not True
        or scope.get("self_excluded_path") != PROJECTION_PATH
        or scope.get("mutable_runtime_evidence_receipts_excluded") is not True
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-015", "Manifest scope contract mismatch"))

    snapshot = projection.get("source_snapshot", {})
    snapshot_head = snapshot.get("pre_projection_head_sha")
    facts = None
    if (
        snapshot.get("snapshot_semantics") != SNAPSHOT_SEMANTICS
        or snapshot.get("baseline_commit_sha") != BASE_COMMIT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-016",
                "Source snapshot semantics or baseline anchor mismatch",
            )
        )

    try:
        facts = collect_git_snapshot_facts(root, snapshot_head)
    except Exception as exc:
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-016",
                "Source snapshot Git facts unavailable",
                error=str(exc),
            )
        )

    if facts is not None:
        lineage_preserved = (
            facts.get("snapshot_is_ancestor_of_current_head") is True
            or facts.get("snapshot_release_surface_equivalent_except_projection") is True
        )
        if (
            facts.get("snapshot_head_sha") != snapshot_head
            or facts.get("baseline_is_ancestor") is not True
            or not lineage_preserved
        ):
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-016",
                    "Source snapshot lineage mismatch",
                    snapshot_head=snapshot_head,
                    current_head=facts.get("current_head_sha"),
                    snapshot_is_ancestor=facts.get("snapshot_is_ancestor_of_current_head"),
                    release_surface_equivalent_except_projection=facts.get(
                        "snapshot_release_surface_equivalent_except_projection"
                    ),
                )
            )

        if (
            snapshot.get("pre_projection_root_tree_sha") != facts.get("root_tree_sha")
            or snapshot.get("pre_projection_canonical_tree_sha") != facts.get("canonical_tree_sha")
        ):
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-017",
                    "Source snapshot tree identity drift",
                    expected_root_tree=facts.get("root_tree_sha"),
                    declared_root_tree=snapshot.get("pre_projection_root_tree_sha"),
                    expected_canonical_tree=facts.get("canonical_tree_sha"),
                    declared_canonical_tree=snapshot.get("pre_projection_canonical_tree_sha"),
                )
            )

        expected_delta = {
            "commits_ahead_of_v3_0_11_conformance_commit": facts.get("commit_count"),
            "total_post_baseline_commits": facts.get("commit_count"),
            "delta_file_count": facts.get("delta_file_count"),
            "delta_added_files": facts.get("delta_added_files"),
            "delta_modified_files": facts.get("delta_modified_files"),
            "delta_removed_files": facts.get("delta_removed_files"),
            "delta_other_files": facts.get("delta_other_files"),
        }
        delta_mismatches = {
            key: {"expected": expected, "declared": snapshot.get(key)}
            for key, expected in expected_delta.items()
            if snapshot.get(key) != expected
        }
        if delta_mismatches:
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-018",
                    "Source snapshot Git-delta metadata drift",
                    mismatches=delta_mismatches,
                )
            )

        inventory = projection.get("overlay_inventory", {})
        count_mismatches = {
            key: {"expected": expected, "declared": inventory.get(key)}
            for key, expected in facts.get("area_counts", {}).items()
            if inventory.get(key) != expected
        }
        if count_mismatches:
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-019",
                    "Overlay inventory count drift",
                    mismatches=count_mismatches,
                )
            )

        record_mismatches = {}
        for key, expected in facts.get("record_lists", {}).items():
            declared = sorted(inventory.get(key, []))
            if declared != expected:
                record_mismatches[key] = {
                    "expected_count": len(expected),
                    "declared_count": len(declared),
                    "missing": sorted(set(expected) - set(declared))[:20],
                    "extra": sorted(set(declared) - set(expected))[:20],
                }
        if record_mismatches:
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-020",
                    "Overlay inventory record set is incomplete or stale",
                    mismatches=record_mismatches,
                )
            )

    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.release-projection-gate-report.v1",
        "projection_id": PROJECTION_ID,
        "base_release": BASE_RELEASE,
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "details": {
            "manifest_entries": len(manifest),
            "tracked_release_surface_files": len(tracked_surface),
            "canonical_capability_count": CAPABILITY_COUNT,
            "mandatory_reference_gates": len(projection_gates),
            "source_graph_sha256": EXPECTED_SOURCE_GRAPH_SHA256,
            "projection_semantics": projection.get("projection_semantics"),
            "snapshot_anchor": snapshot_head,
            "snapshot_commit_count": facts.get("commit_count") if facts else None,
            "snapshot_delta_files": facts.get("delta_file_count") if facts else None,
            "snapshot_is_ancestor": facts.get("snapshot_is_ancestor_of_current_head") if facts else None,
            "snapshot_release_surface_equivalent_except_projection": facts.get(
                "snapshot_release_surface_equivalent_except_projection"
            ) if facts else None,
            "kanboard_reconciliation": kanboard.get("reconciliation_status"),
            "presenton_reconciliation": presenton.get("reconciliation_status"),
            "presenton_current_host_production_e2e": presenton.get("current_host_production_e2e"),
            "autogpt_reconciliation": autogpt.get("reconciliation_status"),
            "autogpt_runtime_activation_status": autogpt.get("runtime_activation_status"),
            "developer_agent_coordination_reconciliation": dac.get("reconciliation_status"),
            "codex_reconciliation": codex.get("reconciliation_status"),
            "codex_current_host_production_e2e": codex.get("current_host_production_e2e"),
            "ai_infra_guard_reconciliation": aisec.get("reconciliation_status"),
            "ai_infra_guard_reference_evidence_status": aisec.get("reference_evidence_status"),
            "ai_infra_guard_current_host_runtime_evidence": aisec.get("current_host_runtime_evidence"),
            "hybrid_editorial_reconciliation": hybrid.get("reconciliation_status"),
            "marketing_reconciliation": marketing.get("reconciliation_status"),
            "stability_sgm_reconciliation": stability_sgm.get("reconciliation_status"),
            "opencut_reconciliation": opencut.get("reconciliation_status"),
            "opencut_runtime_activation_status": opencut.get("runtime_activation_status"),
            "openhands_reconciliation": openhands.get("reconciliation_status"),
            "openhands_runtime_activation_status": openhands.get("runtime_activation_status"),
            "loop_engineering_reconciliation": loop_engineering.get("reconciliation_status"),
            "loop_engineering_runtime_activation_status": loop_engineering.get("runtime_activation_status"),
            "tencentdb_agent_memory_reconciliation": tdai.get("reconciliation_status"),
            "tencentdb_agent_memory_runtime_activation_status": tdai.get("runtime_activation_status"),
            "voice_synthesis_reconciliation": voice.get("reconciliation_status"),
            "voice_synthesis_current_host_runtime_evidence": voice.get("current_host_runtime_evidence"),
            "voice_synthesis_hungarian_quality_evidence": voice.get("hungarian_quality_evidence"),
            "video_provider_lifecycle_reconciliation": vplc.get("reconciliation_status"),
            "video_provider_lifecycle_current_host_runtime_evidence": vplc.get("current_host_runtime_evidence"),
        },
    }
    writej(root / "reports/release-projection-gate-report.json", report)
    return report
