#!/usr/bin/env bash
# Service-only deployment after explicit approval of the exact rendered hash.
# Never updates packages, firewall rules, SSH, Tailscale, trust anchors or hints.
set -euo pipefail
[[ $EUID == 0 && $# == 6 ]] || { echo 'Usage: sudo bash scripts/deploy-private.sh RENDERED_DIR APPROVED_CONFIG_SHA256 APPROVED_BASELINE_SHA256 SSH_CONNECTION SERVER_GLOBAL_DEADLINE_MONOTONIC CLOCK_PROBE_BOOT_ID'; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
rendered=$(realpath "$1")
# Review commits include a checksum manifest for config, limits and transaction code.
(cd "$root" && sha256sum --check plans/phase-b-service.sha256)
sha256sum --check "$root/plans/phase-b-active.sha256"
[[ $(find /etc/unbound/unbound.conf.d -maxdepth 1 -name '*.conf' | wc -l) == 2 ]] || { echo 'Active include set changed; re-review required'; exit 1; }
[[ -z $(systemctl show unbound -p DropInPaths --value) ]] || { echo 'Active unit drop-ins changed; re-review required'; exit 1; }
[[ $(sha256sum "$rendered/unbound.conf" | cut -d ' ' -f1) == "$2" ]] || { echo 'Approved hash mismatch'; exit 1; }
cmp "$rendered/unbound.conf" "$root/plans/phase-b-unbound.conf"
unbound-checkconf "$rendered/unbound.conf"
test -S /run/unbound.ctl
systemctl is-active --quiet unbound
systemctl is-active --quiet tailscaled
ip -4 addr show dev tailscale0 | grep -q '100.95.65.20/'
# Avoid timer/confirmation races: never reuse a pending deployment snapshot.
backup=/var/lib/vynalth-dns/rollback
mkdir -p /var/lib/vynalth-dns
# Serialize active writes against confirmation/recovery and concurrent controllers.
exec 9>/var/lib/vynalth-dns/transaction.lock
flock -n -x 9 || { echo 'Another transaction/recovery holds the lock'; exit 1; }
if systemctl is-active --quiet vynalth-rollback.timer || systemctl is-active --quiet vynalth-rollback.service; then
  echo 'Existing protection still active; do not reuse or stop it'; exit 1
fi
"$root/.venv/bin/python" "$root/scripts/verify-post-boot.py" "$3" "$4"
[[ ! -e $backup ]] || { echo 'Pending deployment exists'; exit 1; }
mkdir -m 0700 "$backup"
touch "$backup/service-only"
cp -a /etc/unbound/unbound.conf "$backup/unbound.conf"
if [[ -f /etc/systemd/system/unbound.service.d/private.conf ]]; then
  cp -a /etc/systemd/system/unbound.service.d/private.conf "$backup/unbound-private-limits.conf"
fi
install -o root -g root -m 0700 "$root/scripts/rollback.sh" /var/lib/vynalth-dns/rollback.sh
"$root/.venv/bin/python" -c 'import json,time,sys; from pathlib import Path; now=time.monotonic(); boot=Path("/proc/sys/kernel/random/boot_id").read_text().strip(); deadline=float(sys.argv[3]); assert boot==sys.argv[4] and now < deadline < now+140; Path(sys.argv[1]).write_text(json.dumps({"started_monotonic":now,"global_deadline_monotonic":deadline,"boot_id":boot,"config_sha256":sys.argv[2]}))' "$backup/transaction.json" "$2" "$5" "$6"
(cd "$backup" && sha256sum unbound.conf > snapshot.sha256; if [[ -f unbound-private-limits.conf ]]; then sha256sum unbound-private-limits.conf >> snapshot.sha256; fi)
trap 'flock -u 9; /bin/bash /var/lib/vynalth-dns/rollback.sh --service-only; exit 1' ERR TERM INT
systemd-run --unit=vynalth-rollback --on-active=180s --timer-property=AccuracySec=1s /bin/bash /var/lib/vynalth-dns/rollback.sh --service-only
"$root/.venv/bin/python" "$root/scripts/check-rollback-timer.py"
# Arming/readiness time is part of the original global budget, never a new window.
"$root/.venv/bin/python" -c 'import json,time; from pathlib import Path; row=json.loads(Path("/var/lib/vynalth-dns/rollback/transaction.json").read_text()); assert Path("/proc/sys/kernel/random/boot_id").read_text().strip()==row["boot_id"] and time.monotonic()<row["global_deadline_monotonic"]'
install -m 0644 "$rendered/unbound.conf" /etc/unbound/unbound.conf
mkdir -p /etc/systemd/system/unbound.service.d
install -m 0644 "$root/scripts/unbound-private-limits.conf" /etc/systemd/system/unbound.service.d/private.conf
systemctl daemon-reload
timeout 40 systemctl restart unbound
dig @127.0.0.1 localhost +time=2 +tries=1 | grep -q 'status: NOERROR'
echo 'Verify Windows private UDP/TCP DNS and fresh SSH within 180s, then run scripts/confirm.sh.'
