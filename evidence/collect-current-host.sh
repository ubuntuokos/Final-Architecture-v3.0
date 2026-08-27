#!/usr/bin/env bash
# Read-only FA3 current-host evidence collector. It intentionally does NOT implement Linux Recovery/Rebuild.
set -euo pipefail
OUT="${1:-./fa3-current-host-evidence-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT/raw"
run(){ local n="$1"; shift; { printf '$ '; printf '%q ' "$@"; printf '\n'; "$@"; } >"$OUT/raw/$n.txt" 2>&1 || true; }
run date date --iso-8601=seconds
run uname uname -a
run os-release cat /etc/os-release
run lscpu lscpu -J
command -v numactl >/dev/null && run numa numactl --hardware
run meminfo cat /proc/meminfo
run cgroup-stat stat -fc %T /sys/fs/cgroup
run cgroup-tree find /sys/fs/cgroup -maxdepth 2 -type f -name 'cgroup.controllers' -o -name 'cpuset.cpus.effective'
run lsblk lsblk -J -o NAME,KNAME,TYPE,SIZE,FSTYPE,UUID,WWN,MOUNTPOINTS
run findmnt findmnt -J
command -v ip >/dev/null && run ip-link ip -j link
command -v ip >/dev/null && run ip-address ip -j address
command -v ip >/dev/null && run ip-route ip -j route
command -v nvidia-smi >/dev/null && run nvidia-summary nvidia-smi --query-gpu=uuid,pci.bus_id,name,driver_version,memory.total --format=csv,noheader
command -v nvidia-smi >/dev/null && run nvidia-topology nvidia-smi topo -m
run systemd-version systemd --version
run failed-units systemctl --failed --no-pager
run services systemctl list-units --type=service --state=running --no-pager
if command -v nft >/dev/null; then run nft-rules nft -j list ruleset; fi
if command -v pw-dump >/dev/null; then run pipewire pw-dump; fi
if command -v sysctl >/dev/null; then
  run vm-state sysctl vm.nr_hugepages vm.nr_overcommit_hugepages vm.compaction_proactiveness vm.extfrag_threshold kernel.numa_balancing
fi
# Only executable/version discovery; never read credential stores or secret-bearing environment/config files.
for c in python3 git podman docker ollama llama-server llama-cli ffmpeg kdenlive blender ardour; do
  if command -v "$c" >/dev/null; then { command -v "$c"; "$c" --version 2>&1 | head -20 || true; } >"$OUT/raw/tool-$c.txt"; fi
done
python3 - "$OUT" <<'PY'
import hashlib,json,os,platform,socket,sys,time
from pathlib import Path
out=Path(sys.argv[1]); files=[]
for p in sorted((out/'raw').glob('*')):
    b=p.read_bytes(); files.append({'path':str(p.relative_to(out)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
obj={'schema':'fa3.host-fingerprint.evidence.v1','status':'COLLECTED_UNVALIDATED','signed':False,'host':socket.gethostname(),'platform':platform.platform(),'collected_at_epoch':int(time.time()),'secret_collection':'PROHIBITED','linux_recovery_rebuild_projection':'OUT_OF_SCOPE','files':files}
(out/'host-fingerprint.json').write_text(json.dumps(obj,indent=2)+'\n')
(out/'SHA256SUMS').write_text(''.join(f"{x['sha256']}  {x['path']}\n" for x in files))
PY
printf 'Collected read-only evidence at %s\n' "$OUT"
printf 'This is COLLECTED_UNVALIDATED, not PASS. Validation/acceptance must still run.\n'
