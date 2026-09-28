# FA3: Display GPU AI admission

The display GPU serves the UI by default. Two independent conditions permit AI use:

1. Sole GPU: a trusted live inventory shows that no other GPU and no NPU are present. Normal central Model Router selection, verified HRB display reserve, and HRB lease are still mandatory.
2. Additional GPU/NPU present: the application must provide an affirmative user selection for the exact application, task, Router-selected model, and stable display GPU identity. The choice is not global and cannot enable automatic augmentation, load balancing or silent device/model fallback. A second GPU/NPU that is present but unavailable still triggers this requirement.

## Application and authority boundary

An application offering this feature must show the proposed model, task and GPU and record an explicit selection with its reason and a unique intent ID. Applications submit typed intent; they do not assign devices. The HRB obtains and revalidates trusted live topology, verifies display and VRAM reserve, and owns admission, reservation and authenticated leases. The central Model Router owns model/provider/runtime selection. A model mismatch or topology change requires denial/revalidation rather than silent substitution.

The pure evaluator is src/fa3_display_gpu_admission.py. HRB reservation-plan evaluation can supply a trusted_hardware_inventory keyword. A display-GPU assignment must carry workload_binding: application_id, task_id, model_id, display_reserve_confirmed, and verified router_binding (route, provider, runtime and physical model). With another GPU/NPU, it also requires application_selection with source APPLICATION_USER_SELECTION, approved true, automatic false, allow_fallback false, intent_id, reason and matching application/task/model/device identifiers.

## Hardware Audit

CPU-only remains valid; accelerator count is 0..N. GPU and NPU families, backend and display server are not globally pinned. Use stable discovered device IDs, not transient GPU ordinals. Display safety reserve is mandatory. The FA3 Donor & Reference Registry was queried; no external code is imported.

## Runtime evidence boundary

Policy evaluation checks the structure and consistency of inputs, NOT their authentication. Provider/application JSON must never be accepted as verified HRB inventory, display-reserve proof or Router admission proof. The integrating HRB/Router services must authenticate these separately and enforce the same policy again at lease issuance/renewal. The current PR includes a reservation-level gate and static regressions; until the production HRB lease path and current-host execution are evidenced, policy PASS is not an end-to-end runtime PASS.
