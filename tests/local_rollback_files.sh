#!/usr/bin/env bash
# Local/CI namespace only. No actual daemon, firewall or timer operations.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
if [[ ${1:-} != --inside ]]; then
  [[ $EUID == 0 ]] || { echo 'Root is required on the LOCAL test host'; exit 1; }
  lab=$(mktemp -d /tmp/vynalth-local-rollback.XXXXXX)
  trap 'rm -rf "$lab"' EXIT
  mkdir -p "$lab/etc/unbound" "$lab/etc/systemd/system/unbound.service.d" "$lab/varlib" "$lab/bin"
  cp "$repo/scripts/rollback.sh" "$lab/rollback.sh"
  readlink /proc/self/ns/mnt > "$lab/host-ns"
  unshare --mount bash "$0" --inside "$lab"
  exit
fi
lab=$(realpath "$2")
[[ $lab == /tmp/vynalth-local-rollback.* && -f $lab/rollback.sh ]]
[[ $(readlink /proc/self/ns/mnt) != $(cat "$lab/host-ns") ]]
mount --make-rprivate /
mount --bind "$lab/etc" /etc
mount --bind "$lab/varlib" /var/lib
cat > "$lab/bin/systemctl" <<'SHIM'
#!/bin/bash
case "$*" in
 'daemon-reload'|'restart unbound') printf '%s\n' "$*" >> /var/lib/calls
   [[ "$*" != 'restart unbound' || ${VYNALTH_LAB_FAIL_RESTART:-0} != 1 ]] ;;
 *) exit 90 ;;
esac
SHIM
printf '#!/bin/bash\nexit 99\n' > "$lab/bin/nft"
chmod 0700 "$lab/bin/systemctl" "$lab/bin/nft"
export PATH="$lab/bin:$PATH"
for previous in present absent; do
 for marker in present absent; do
  backup=/var/lib/vynalth-dns/rollback
  mkdir -p "$backup"
  printf 'original configuration\n' > "$backup/unbound.conf"
  printf 'candidate configuration\n' > /etc/unbound/unbound.conf
  printf 'candidate limits\n' > /etc/systemd/system/unbound.service.d/private.conf
  printf 'unrelated setting\n' > /etc/systemd/system/unbound.service.d/unrelated.conf
  [[ $marker != present ]] || touch "$backup/service-only"
  [[ $previous != present ]] || printf 'original limits\n' > "$backup/unbound-private-limits.conf"
  (cd "$backup" && sha256sum unbound.conf > snapshot.sha256; if [[ -f unbound-private-limits.conf ]]; then sha256sum unbound-private-limits.conf >> snapshot.sha256; fi)
  bash "$lab/rollback.sh" --service-only
  grep -qx 'original configuration' /etc/unbound/unbound.conf
  grep -qx 'unrelated setting' /etc/systemd/system/unbound.service.d/unrelated.conf
  if [[ $previous == present ]]; then
   grep -qx 'original limits' /etc/systemd/system/unbound.service.d/private.conf
  else
   test ! -e /etc/systemd/system/unbound.service.d/private.conf
  fi
  [[ ! -d $backup ]]
  echo "PASS actual file restore: prior=$previous marker=$marker; service calls stubbed; nft prohibited"
 done
done
before=$(wc -l < /var/lib/calls)
bash "$lab/rollback.sh" --service-only
[[ $(wc -l < /var/lib/calls) == "$before" ]]
echo 'PASS no pending snapshot: timer callback does not touch service'
for fault in missing-manifest corrupt-config extra-limits restart-failed; do
 backup=/var/lib/vynalth-dns/rollback
 mkdir -p "$backup"
 printf 'original configuration\n' > "$backup/unbound.conf"
 (cd "$backup" && sha256sum unbound.conf > snapshot.sha256)
 printf 'candidate configuration\n' > /etc/unbound/unbound.conf
 case $fault in
  missing-manifest) rm "$backup/snapshot.sha256" ;;
  corrupt-config) printf 'corrupt\n' > "$backup/unbound.conf" ;;
  extra-limits) printf 'unrecorded\n' > "$backup/unbound-private-limits.conf" ;;
  restart-failed) export VYNALTH_LAB_FAIL_RESTART=1 ;;
 esac
 if bash "$lab/rollback.sh" --service-only > /dev/null 2>&1; then
  echo "FAIL $fault accepted"; exit 1
 fi
 test -d "$backup"
 if [[ $fault == restart-failed ]]; then
  grep -qx 'original configuration' /etc/unbound/unbound.conf
 else
  grep -qx 'candidate configuration' /etc/unbound/unbound.conf
 fi
 unset VYNALTH_LAB_FAIL_RESTART
 # Disposable local fixture only; preserve the host and real historical backup.
 rm -r "$backup"
 echo "PASS recovery failure retained pending evidence: $fault"
done
