#!/usr/bin/env python3
"""Fail-closed FA3 AI Studio application provisioner.

The provisioner accepts only canonical application IDs. It never accepts a repository URL,
package URL, shell fragment, or arbitrary command from the GUI. Install/launch commands
must come from repository-controlled provider recipes and are executed with shell=False.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CATALOG_NAME = "FA3-AI-STUDIO-APP-CATALOG-001.json"
APP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class ProvisioningError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 78) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvisioningError(f"cannot read trusted metadata: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProvisioningError(f"trusted metadata must be a JSON object: {path}")
    return data


def discover_repo_root(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("FA3_REPO_ROOT"):
        candidates.append(Path(os.environ["FA3_REPO_ROOT"]))
    candidates.extend([Path.cwd(), Path(__file__).resolve().parent.parent])

    for candidate in candidates:
        candidate = candidate.expanduser().resolve()
        for current in (candidate, *candidate.parents):
            if (current / "canonical" / CATALOG_NAME).is_file():
                return current
    return None


def locate_catalog(repo_root: Path | None) -> Path:
    candidates: list[Path] = []
    if repo_root:
        candidates.append(repo_root / "canonical" / CATALOG_NAME)
    candidates.extend(
        [
            Path("/usr/share/fa3/canonical") / CATALOG_NAME,
            Path("/usr/local/share/fa3/canonical") / CATALOG_NAME,
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    raise ProvisioningError("canonical AI Studio application catalog not found", 66)


def load_application(catalog_path: Path, app_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not APP_ID_RE.fullmatch(app_id):
        raise ProvisioningError("invalid application identifier", 64)
    catalog = _load_json(catalog_path)
    if catalog.get("catalog_mode") != "ALLOWLIST" or catalog.get("user_defined_entries_allowed") is not False:
        raise ProvisioningError("catalog fail-closed policy check failed", 77)

    apps = catalog.get("applications")
    if not isinstance(apps, list):
        raise ProvisioningError("catalog applications field is invalid")
    for app in apps:
        if isinstance(app, dict) and app.get("id") == app_id:
            if app.get("admission") != "APPROVED":
                raise ProvisioningError("application is not approved", 77)
            if app.get("install_mode") != "FIRST_USE":
                raise ProvisioningError("application is not admitted for first-use provisioning", 77)
            if app.get("direct_source_install_allowed") is not False:
                raise ProvisioningError("application violates direct-source installation policy", 77)
            return catalog, app
    raise ProvisioningError("application is not present in the canonical allowlist", 77)


def locate_recipe(repo_root: Path | None, app: dict[str, Any]) -> Path:
    recipe_name = app.get("provider_recipe")
    if not isinstance(recipe_name, str) or not recipe_name or Path(recipe_name).name != recipe_name:
        raise ProvisioningError("provider recipe name is missing or unsafe")

    candidates: list[Path] = []
    if repo_root:
        candidates.append(repo_root / "deployment" / "app-providers" / recipe_name)
    candidates.extend(
        [
            Path("/usr/share/fa3/app-providers") / recipe_name,
            Path("/usr/local/share/fa3/app-providers") / recipe_name,
        ]
    )
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise ProvisioningError("approved provider recipe is not materialized", 78)


def validate_recipe(recipe: dict[str, Any], app_id: str) -> None:
    if recipe.get("schema") != "fa3.app-provider-recipe.v1":
        raise ProvisioningError("provider recipe schema mismatch")
    if recipe.get("app_id") != app_id:
        raise ProvisioningError("provider recipe app_id mismatch")
    if recipe.get("admission") != "APPROVED":
        raise ProvisioningError("provider recipe is not approved", 77)
    if recipe.get("shell") is not False:
        raise ProvisioningError("provider recipe must explicitly disable shell execution", 77)


def safe_argv(operation: dict[str, Any]) -> list[str]:
    argv = operation.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        raise ProvisioningError("provider operation argv is missing or invalid")
    if any("\x00" in item for item in argv):
        raise ProvisioningError("provider operation contains an invalid argument")

    executable = argv[0]
    if Path(executable).is_absolute():
        if not Path(executable).is_file():
            raise ProvisioningError(f"provider executable not found: {executable}", 69)
    else:
        resolved = shutil.which(executable)
        if not resolved:
            raise ProvisioningError(f"provider executable not found: {executable}", 69)
        argv = [resolved, *argv[1:]]
    return argv


def clean_environment() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("LD_PRELOAD", "PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    return env


def state_dir() -> Path:
    configured = os.environ.get("FA3_APP_STATE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    xdg_state = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg_state).expanduser() if xdg_state else Path.home() / ".local" / "state"
    return (base / "fa3" / "app-state").resolve()


def write_install_marker(app_id: str, recipe_path: Path) -> None:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / f"{app_id}.json"
    payload = {
        "schema": "fa3.app-install-state.v1",
        "app_id": app_id,
        "state": "INSTALLED",
        "recipe": recipe_path.name,
    }
    temporary = marker.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(marker)


def probe_installed(app: dict[str, Any]) -> bool:
    probes = app.get("probe_executables", [])
    if isinstance(probes, list):
        for probe in probes:
            if isinstance(probe, str) and probe and shutil.which(probe):
                return True
    return (state_dir() / f"{app.get('id')}.json").is_file()


def run_install(app_id: str, app: dict[str, Any], recipe_path: Path) -> int:
    if app.get("installable") is not True:
        raise ProvisioningError("application is not installable on demand", 77)
    recipe = _load_json(recipe_path)
    validate_recipe(recipe, app_id)
    operation = recipe.get("install")
    if not isinstance(operation, dict):
        raise ProvisioningError("provider recipe has no install operation")
    argv = safe_argv(operation)

    if operation.get("requires_privilege") is True and os.geteuid() != 0:
        pkexec = shutil.which("pkexec")
        if not pkexec:
            raise ProvisioningError("privileged install requires pkexec", 69)
        argv = [pkexec, *argv]

    completed = subprocess.run(argv, shell=False, env=clean_environment(), check=False)
    if completed.returncode != 0:
        raise ProvisioningError(f"provider installation failed with exit code {completed.returncode}", completed.returncode or 1)
    write_install_marker(app_id, recipe_path)
    print(json.dumps({"app_id": app_id, "operation": "install", "result": "PASS"}))
    return 0


def run_launch(app_id: str, app: dict[str, Any], recipe_path: Path) -> int:
    if not probe_installed(app):
        raise ProvisioningError("application is not installed", 77)
    recipe = _load_json(recipe_path)
    validate_recipe(recipe, app_id)
    operation = recipe.get("launch")
    if not isinstance(operation, dict):
        raise ProvisioningError("provider recipe has no launch operation")
    argv = safe_argv(operation)
    subprocess.Popen(argv, shell=False, env=clean_environment(), start_new_session=True, close_fds=True)
    print(json.dumps({"app_id": app_id, "operation": "launch", "result": "STARTED"}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FA3 curated application provisioner")
    parser.add_argument("--repo-root", help="FA3 repository root; used only to locate trusted metadata")
    parser.add_argument("operation", choices=("status", "install", "launch"))
    parser.add_argument("app_id")
    args = parser.parse_args(argv)

    try:
        repo_root = discover_repo_root(args.repo_root)
        catalog_path = locate_catalog(repo_root)
        _, app = load_application(catalog_path, args.app_id)
        if args.operation == "status":
            print(json.dumps({"app_id": args.app_id, "installed": probe_installed(app)}))
            return 0

        recipe_path = locate_recipe(repo_root, app)
        if args.operation == "install":
            return run_install(args.app_id, app, recipe_path)
        return run_launch(args.app_id, app, recipe_path)
    except ProvisioningError as exc:
        print(json.dumps({"result": "DENY", "error": str(exc)}), file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
