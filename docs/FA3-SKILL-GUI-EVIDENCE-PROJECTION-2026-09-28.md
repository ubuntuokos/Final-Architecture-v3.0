# FA3 Control Center: Skill Fabric evidence projection

This GUI change is stacked above the task preflight and verified snapshot PRs.
It reuses `Fa3RepositoryModel` and the existing `ContextInspectorPage` and
`AgentActionCenterPage`, rather than adding a second skill management UI.

The model reads only the existing
`reports/skill-fabric-gate-report.json` report. It validates the gate ID and
exposes only whitelisted status/regression fields. Missing, malformed, or
unexpected reports remain UNVERIFIED. The current-host field is deliberately
NOT_VERIFIED: a static/reference report cannot promote live runtime evidence.

The GUI does not approve a skill, invoke a provider, mutate the registry or
declare current-host PASS. There is no new architectural authority.
Qt/QML is added to the existing Control Center and keeps Wayland/X11 support;
no KDE-specific or accelerator requirement. GUI CI includes a reference Qt
build; it is not a physical target-host deployment claim.
