#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from typing import Any
DETECTOR_VERSION="1.0.0"
MANIFEST_NAMES={"package.json","pyproject.toml","requirements.txt","Cargo.toml","go.mod","pubspec.yaml","pom.xml","build.gradle","build.gradle.kts","Gemfile","composer.json","deno.json","deno.jsonc"}
EXT_LANG={".py":"python",".ts":"typescript",".tsx":"typescript",".js":"javascript",".jsx":"javascript",".rs":"rust",".go":"go",".java":"java",".kt":"kotlin",".cs":"dotnet",".dart":"dart",".rb":"ruby",".php":"php"}
def _sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def fingerprint(root:Path,max_files:int=10000)->dict[str,Any]:
    root=Path(root).resolve();languages=set();frameworks=set();manifests=[];evidence=[];count=0
    for base,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not d.startswith(".") and not (Path(base)/d).is_symlink())
        for name in sorted(names):
            count+=1
            if count>max_files:raise RuntimeError("workspace scan file limit exceeded")
            p=Path(base)/name
            if p.is_symlink():continue
            rel=p.relative_to(root).as_posix();lang=EXT_LANG.get(p.suffix.lower())
            if lang:languages.add(lang)
            if name in MANIFEST_NAMES or name.startswith(("next.config.","vite.config.","nuxt.config.","svelte.config.")):
                try:raw=p.read_bytes()
                except OSError:continue
                manifests.append(rel);evidence.append(f"{rel}:{_sha(raw)}")
                if name=="package.json":
                    try:
                        obj=json.loads(raw.decode("utf-8"));deps={}
                        for k in ("dependencies","devDependencies","peerDependencies"):
                            if isinstance(obj.get(k),dict):deps.update(obj[k])
                        for pkg,label in (("react","react"),("next","nextjs"),("vue","vue"),("nuxt","nuxt"),("svelte","svelte"),("@angular/core","angular"),("astro","astro"),("three","threejs"),("playwright","playwright")):
                            if pkg in deps:frameworks.add(label)
                    except (ValueError,UnicodeDecodeError):pass
                lower=raw[:200000].decode("utf-8","ignore").lower()
                if name=="pyproject.toml":
                    for pkg,label in (("django","django"),("fastapi","fastapi"),("flask","flask")):
                        if pkg in lower:frameworks.add(label)
    return {"schema":"fa3.project-stack-fingerprint.v1","detector_version":DETECTOR_VERSION,"languages":sorted(languages),"frameworks":sorted(frameworks),"manifests":sorted(manifests),"evidence_digest":_sha("\n".join(sorted(evidence)).encode()),"scanned_files":count,"execution_performed":False,"network_used":False}
def eligible_skill_ids(fp:dict[str,Any],skill_records:list[dict[str,Any]],task_classes:list[str]|None=None)->list[str]:
    langs=set(fp.get("languages",[]));frameworks=set(fp.get("frameworks",[]));tasks={x.lower() for x in (task_classes or [])};out=[]
    for r in skill_records:
        if r.get("admission_status")!="ADMITTED":continue
        e=r.get("eligibility",{});rl=set(e.get("languages",[]));rf=set(e.get("frameworks",[]));rt={str(x).lower() for x in e.get("task_classes",[])}
        if rl and not rl.issubset(langs):continue
        if rf and not rf.issubset(frameworks):continue
        if rt and not (tasks and rt.intersection(tasks)):continue
        out.append(r["skill_id"])
    return sorted(out)
