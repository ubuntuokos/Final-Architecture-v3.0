#!/usr/bin/env python3
"""Render opt-in FA3 PR Watch service and read-only GitHub App manifest.

Only writes nonsecret files under the repository reports/ directory. No GitHub
registration, systemd installation, network or credentials are involved.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

from fa3_pr_watch import PRWatchDenied,REPO

EVENTS=("pull_request","issues","issue_comment",
        "pull_request_review","check_run","workflow_run")
PERMISSIONS={"metadata":"read","contents":"read","issues":"read",
             "pull_requests":"read","checks":"read","actions":"read"}


def validated_endpoint(url:str)->str:
    if not isinstance(url,str) or len(url)>512 or not url.isascii():
        raise PRWatchDenied("WEBHOOK_ENDPOINT_INVALID")
    p=urllib.parse.urlparse(url)
    if (p.scheme!="https" or not p.hostname or p.username is not None
            or p.password is not None or p.query or p.fragment
            or p.path!="/github" or p.hostname.endswith((".invalid",".localhost",".local"))
            or p.hostname in ("localhost","127.0.0.1","::1")):
        raise PRWatchDenied("HTTPS_APPROVED_RELAY_REQUIRED")
    try:
        if p.port is not None and p.port not in (443,8443):
            raise PRWatchDenied("HTTPS_RELAY_PORT_NOT_ADMITTED")
    except ValueError:
        raise PRWatchDenied("WEBHOOK_ENDPOINT_INVALID") from None
    return url


def render(repo_root:Path,github_repo:str,webhook_url:str)->dict:
    root=Path(repo_root).resolve()
    if (not isinstance(github_repo,str) or not REPO.fullmatch(github_repo)
            or not (root/"canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").is_file()):
        raise PRWatchDenied("FA3_ROOT_OR_REPOSITORY_INVALID")
    root_text=str(root)
    if re.search(r"[\s%;\"\\]",root_text):
        raise PRWatchDenied("SYSTEMD_ROOT_REQUIRES_SAFE_ABSOLUTE_PATH")
    url=validated_endpoint(webhook_url)
    template=root/"deployment/pr-watch/fa3-pr-watch.service"
    unit=template.read_text()
    if unit.count("__FA3_REPO_ROOT__")!=2 or unit.count("__FA3_GITHUB_REPOSITORY__")!=1:
        raise PRWatchDenied("SYSTEMD_TEMPLATE_DRIFT")
    unit=unit.replace("__FA3_REPO_ROOT__",root_text).replace(
        "__FA3_GITHUB_REPOSITORY__",github_repo)
    manifest={
        "name":"FA3 PR Watch (read-only)",
        "url":"https://github.com/"+github_repo,
        "hook_attributes":{"url":url,"active":True},
        "public":False,
        "default_permissions":PERMISSIONS,
        "default_events":list(EVENTS),
        "request_oauth_on_install":False,
    }
    output=root/"reports/pr-watch"
    if output.is_symlink():raise PRWatchDenied("REPORT_DIRECTORY_SYMLINK")
    output.mkdir(parents=True,exist_ok=True)
    if not output.is_dir() or output.is_symlink():
        raise PRWatchDenied("REPORT_DIRECTORY_INVALID")
    unit_out=output/"fa3-pr-watch.service"
    manifest_out=output/"github-app-manifest.json"
    for path in (unit_out,manifest_out):
        if path.is_symlink():raise PRWatchDenied("REPORT_PATH_SYMLINK")
    unit_out.write_text(unit,encoding="utf-8")
    manifest_out.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    unit_out.chmod(0o644)
    manifest_out.chmod(0o644)
    return {"status":"PREPARED_NOT_INSTALLED","unit":str(unit_out),
            "manifest":str(manifest_out),"secrets_collected":False,
            "github_app_registered":False,"service_started":False,
            "requires_explicit_admin_provisioning":True}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--github-repo",required=True)
    p.add_argument("--webhook-url",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(render(a.repo_root,a.github_repo,a.webhook_url),sort_keys=True))
        return 0
    except (PRWatchDenied,OSError,ValueError) as exc:
        code=exc.code if isinstance(exc,PRWatchDenied) else "RENDER_FAILED"
        print(json.dumps({"status":"DENIED","code":code}),file=sys.stderr)
        return 2

if __name__=="__main__":raise SystemExit(main())
