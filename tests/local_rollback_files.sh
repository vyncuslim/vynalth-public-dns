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
 'daemon-reload'|'restart unbound') printf '%s\n' "$*" >> /var/lib/calls ;;
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
