# FA3 AI Studio app-provider recipes

This directory is the only repository-controlled recipe surface used by `scripts/fa3-app-provisioner.py` for first-use application materialization.

A catalog entry is not enough to execute an install. The corresponding recipe must also exist here (or in the installed `/usr/share/fa3/app-providers` projection), must match the requested canonical app ID, and must explicitly disable shell execution.

Minimal recipe shape:

```json
{
  "schema": "fa3.app-provider-recipe.v1",
  "app_id": "example-app",
  "admission": "APPROVED",
  "shell": false,
  "install": {
    "argv": ["/absolute/approved/installer", "--non-interactive"],
    "requires_privilege": false
  },
  "launch": {
    "argv": ["/absolute/approved/application"]
  }
}
```

Rules:

- recipes are repository-controlled artifacts, not user-created GUI data;
- `argv` is executed with `shell=False`;
- no source URL is accepted from the GUI or provisioner CLI;
- privilege elevation is explicit and uses the host authentication boundary;
- missing, malformed, unknown, or unapproved recipes fail closed;
- provider-specific preflight, dependency, security, and conformance checks belong in the approved installer invoked by the recipe;
- a successful install must not be promoted to release evidence until the provider-specific conformance and evidence gates pass.
