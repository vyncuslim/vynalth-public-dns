#!/usr/bin/env bash
# Real 180s systemd timer, isolated file mounts, stub service commands.
# Never restarts production Unbound or changes host config/firewall.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
[[ $EUID == 0 ]] || { echo 'Run with sudo on the authorized systemd lab host'; exit 1; }
if [[ ${1:-} == --inside ]]; then
  lab=$(realpath "$2")
  [[ $lab == /var/lib/unbound/vynalth-rollback-test.* && -f $lab/lab-marker ]] || exit 1
  # This entry point is only legal inside the timer's new mount namespace.
  [[ $(readlink /proc/self/ns/mnt) != $(cat "$lab/host-mount-ns") ]] || exit 1
  mount --make-rprivate /
  # Keep the lab reachable after the private /var/lib bind hides its host path.
  mount -t tmpfs tmpfs /tmp
  mkdir /tmp/vynalth-rollback-lab
  mount --bind "$lab" /tmp/vynalth-rollback-lab
  lab=/tmp/vynalth-rollback-lab
  mount --bind "$lab/etc-unbound" /etc/unbound
  mount --bind "$lab/system-units" /etc/systemd/system
  mount --bind "$lab/var-lib" /var/lib
  export PATH="$lab/bin:$PATH"
  bash "$lab/rollback.sh"
  exit 0
fi
systemctl is-active --quiet unbound
lab=$(mktemp -d /var/lib/unbound/vynalth-rollback-test.XXXXXX)
unit="vynalth-rollback-test-$$"
cleanup() {
  systemctl stop "$unit.timer" "$unit.service" >/dev/null 2>&1 || true
  rm -rf "$lab"
}
trap cleanup EXIT
touch "$lab/lab-marker"
readlink /proc/self/ns/mnt > "$lab/host-mount-ns"
mkdir -p "$lab/etc-unbound" "$lab/system-units/unbound.service.d" "$lab/var-lib/vynalth-dns/rollback" "$lab/bin"
cp -a /etc/unbound/unbound.conf "$lab/original.conf"
cp "$repo/scripts/rollback.sh" "$lab/rollback.sh"
cat > "$lab/bin/systemctl" <<'SHIM'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  'daemon-reload'|'restart unbound') printf '%s\n' "$*" >> /var/lib/vynalth-dns/service-calls ;;
  *) echo 'Unexpected systemctl operation in isolated rollback test' >&2; exit 1 ;;
esac
SHIM
chmod 0700 "$lab/bin/systemctl"
# Any accidental firewall operation fails rather than reaching the host binary.
printf '#!/usr/bin/env bash\nexit 99\n' > "$lab/bin/nft"
chmod 0700 "$lab/bin/nft"
backup="$lab/var-lib/vynalth-dns/rollback"
touch "$backup/service-only"
cp -a "$lab/original.conf" "$backup/unbound.conf"
printf '[Service]\nMemoryMax=256M\nTasksMax=32\n' > "$lab/original-private.conf"
cp -a "$lab/original-private.conf" "$backup/unbound-private-limits.conf"
printf 'unrelated unit setting\n' > "$lab/system-units/unbound.service.d/unrelated.conf"
cp -a "$repo/plans/phase-b-unbound.conf" "$lab/etc-unbound/unbound.conf"
cp -a "$repo/scripts/unbound-private-limits.conf" "$lab/system-units/unbound.service.d/private.conf"
prod_pid=$(systemctl show unbound -p MainPID --value)
start=$(date +%s)
systemd-run --unit="$unit" --on-active=180s --timer-property=AccuracySec=1s \
  /usr/bin/unshare --mount /bin/bash "$repo/tests/service_rollback_lab.sh" --inside "$lab"
echo "Waiting for isolated timer $unit; production PID=$prod_pid"
for _ in $(seq 1 220); do
  [[ -d $backup ]] || break
  sleep 1
done
[[ ! -d $backup ]]
elapsed=$(( $(date +%s) - start ))
[[ $elapsed -ge 180 && $elapsed -le 220 ]]
cmp "$lab/original.conf" "$lab/etc-unbound/unbound.conf"
cmp "$lab/original-private.conf" "$lab/system-units/unbound.service.d/private.conf"
grep -qx 'unrelated unit setting' "$lab/system-units/unbound.service.d/unrelated.conf"
[[ $(cat "$lab/var-lib/vynalth-dns/service-calls") == $'daemon-reload\nrestart unbound' ]]
[[ $(systemctl show "$unit.service" -p Result --value) == success ]]
# Originally absent private drop-in must be removed, with the original config restored.
mkdir -m 0700 "$backup"
touch "$backup/service-only"
cp -a "$lab/original.conf" "$backup/unbound.conf"
cp -a "$repo/plans/phase-b-unbound.conf" "$lab/etc-unbound/unbound.conf"
unshare --mount bash "$repo/tests/service_rollback_lab.sh" --inside "$lab"
cmp "$lab/original.conf" "$lab/etc-unbound/unbound.conf"
[[ ! -f $lab/system-units/unbound.service.d/private.conf ]]
[[ $(systemctl show unbound -p MainPID --value) == "$prod_pid" ]]
systemctl is-active --quiet unbound
echo "PASS actual timer after ${elapsed}s: exact config/settings restored; absent drop-in removed; production PID unchanged"
echo 'Service daemon-reload/restart calls were stubbed inside isolated mounts; production recovery remains unexecuted.'
