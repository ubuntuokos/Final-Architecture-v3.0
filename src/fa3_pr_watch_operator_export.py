#!/usr/bin/env python3
"""Explicit read-only cross-UID PR Watch view; private event replay cache stays 0600.

Only an opt-in dedicated service may export the allowlisted operator fields to
a service-owned 0750 directory / 0640 file for an explicitly admitted group.
"""
import json
import os
import stat
import tempfile
from pathlib import Path

from fa3_pr_watch import ProjectionStore, PRWatchDenied

SCHEMA="fa3.pr-watch-operator-export.v1"
FIELDS=("external_key","repository","number","kind","title","revision",
        "head_sha","base_sha","last_event","observed_at","reconciliation_state")


def export_operator_view(store:ProjectionStore,path:Path)->dict:
    path=Path(path)
    if not path.is_absolute() or path.is_symlink() or path.parent.is_symlink():
        raise PRWatchDenied("OPERATOR_EXPORT_PATH_UNSAFE")
    parent=path.parent
    if not parent.is_dir():
        raise PRWatchDenied("OPERATOR_EXPORT_DIRECTORY_MISSING")
    info=parent.stat()
    if (info.st_uid!=os.geteuid() or info.st_gid!=os.getegid()
            or stat.S_IMODE(info.st_mode)!=0o750):
        raise PRWatchDenied("OPERATOR_EXPORT_GROUP_BOUNDARY_INVALID")
    if path.exists():
        info=path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_gid!=os.getegid():
            raise PRWatchDenied("OPERATOR_EXPORT_FILE_BOUNDARY_INVALID")
    source=store.operator_projection()
    if source.get("authority") is not False or source.get("execution_enabled") is not False:
        raise PRWatchDenied("OPERATOR_EXPORT_SOURCE_AUTHORITY_DRIFT")
    items={}
    for item in source["items"]:
        key=item["external_key"]
        if key in items:
            raise PRWatchDenied("DUPLICATE_OPERATOR_KEY")
        items[key]={field:item[field] for field in FIELDS if field in item}
        items[key]["canonical_work_item_id"]=None
    out={"schema":SCHEMA,"status":"OBSERVATION_ONLY",
         "authority":False,"execution_enabled":False,
         "operator_export":True,"redacted":True,
         "last_observed_at":source.get("last_observed_at",""),"items":items}
    fd,tmp=tempfile.mkstemp(prefix=".operator-",dir=parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as fh:
            os.fchmod(fh.fileno(),0o640)
            json.dump(out,fh,sort_keys=True,ensure_ascii=False)
            fh.write("\n");fh.flush();os.fsync(fh.fileno())
        os.replace(tmp,path)
        dfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
        return {"status":"EXPORTED_REFERENCE_VIEW","count":len(items),
                "credential_values_collected":False,
                "authority":False}
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
