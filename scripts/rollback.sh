#!/usr/bin/env bash
set -euo pipefail
backup=/var/lib/vynalth-dns/rollback
test -d "$backup" || exit 0
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
