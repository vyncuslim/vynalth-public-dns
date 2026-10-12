#!/usr/bin/env bash
set -euo pipefail
# Confirmation must never move a snapshot while rollback is restoring it.
exec 9>/var/lib/vynalth-dns/transaction.lock
flock -x 9
backup=/var/lib/vynalth-dns/rollback
test -d "$backup" || exit 0
if [[ ${1:-} == --service-only || -e $backup/service-only ]]; then
  # Detect snapshot corruption before replacing any active service files.
  (cd "$backup" && sha256sum --check snapshot.sha256)
  (cd "$backup" && cmp snapshot.sha256 <(sha256sum unbound.conf; if [[ -f unbound-private-limits.conf ]]; then sha256sum unbound-private-limits.conf; fi))
  cp -a "$backup/unbound.conf" /etc/unbound/unbound.conf
  if [[ -f $backup/unbound-private-limits.conf ]]; then
    cp -a "$backup/unbound-private-limits.conf" /etc/systemd/system/unbound.service.d/private.conf
  else
    rm -f /etc/systemd/system/unbound.service.d/private.conf
  fi
  systemctl daemon-reload
  timeout 40 systemctl restart unbound
  mv -T "$backup" "/var/lib/vynalth-dns/rolled-back-$(date +%s)-$$"
  exit 0
fi
batch=$(mktemp)
if nft list table inet vynalth_dns >/dev/null 2>&1; then
  echo 'delete table inet vynalth_dns' > "$batch"
fi
if [[ -e $backup/had-table ]]; then cat "$backup/firewall.nft" >> "$batch"; fi
nft --file "$batch"
rm "$batch"
cp -a "$backup/unbound.conf" /etc/unbound/unbound.conf
if [[ -f $backup/vynalth-firewall.service ]]; then
  cp -a "$backup/vynalth-firewall.service" /etc/systemd/system/
  cp -a "$backup/vynalth-dns.nft" /etc/vynalth-dns.nft
else
  systemctl disable vynalth-firewall.service || true
  rm -f /etc/systemd/system/vynalth-firewall.service /etc/vynalth-dns.nft
fi
systemctl daemon-reload
if [[ -f $backup/unbound-limits.conf ]]; then
  cp -a "$backup/unbound-limits.conf" /etc/systemd/system/unbound.service.d/vynalth.conf
else
  rm -f /etc/systemd/system/unbound.service.d/vynalth.conf
fi
if [[ -f $backup/firewall-load.sh ]]; then
  cp -a "$backup/firewall-load.sh" /usr/local/lib/vynalth-dns/firewall-load.sh
else
  rm -f /usr/local/lib/vynalth-dns/firewall-load.sh
fi
systemctl daemon-reload
systemctl restart unbound
mv "$backup" "/var/lib/vynalth-dns/rolled-back-$(date +%s)"
