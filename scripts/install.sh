#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run as root on an approved Ubuntu 24.04 VM'; exit 1; }
# shellcheck source=/dev/null
source /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 24.04 ]] || exit 1
[[ $# == 1 && -d $1 ]] || { echo 'Usage: sudo bash scripts/install.sh artifacts/rendered'; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
rendered=$(realpath "$1")
apt-get update
apt-get install -y unbound dns-root-data nftables dnsutils python3 unattended-upgrades
# Refuse missing trust data; never replace an RFC5011-managed anchor on redeploy.
if [[ ! -s /var/lib/unbound/root.key ]]; then
  install -o unbound -g unbound -m 0644 /usr/share/dns/root.key /var/lib/unbound/root.key
fi
test -s /usr/share/dns/root.hints
unbound-checkconf "$rendered/unbound.conf"
nft --check --file "$rendered/firewall.nft"
backup=/var/lib/vynalth-dns/rollback
mkdir -p /var/lib/vynalth-dns
[[ ! -e $backup ]] || { echo 'Previous deployment pending confirmation/rollback'; exit 1; }
mkdir -m 0700 "$backup"
cp -a /etc/unbound/unbound.conf "$backup/unbound.conf"
if nft list table inet vynalth_dns > "$backup/firewall.nft" 2>/dev/null; then
  touch "$backup/had-table"
fi
cp -a /etc/systemd/system/vynalth-firewall.service "$backup/" 2>/dev/null || true
cp -a /etc/vynalth-dns.nft "$backup/" 2>/dev/null || true
cp -a /etc/systemd/system/unbound.service.d/vynalth.conf "$backup/unbound-limits.conf" 2>/dev/null || true
cp -a /usr/local/lib/vynalth-dns/firewall-load.sh "$backup/" 2>/dev/null || true
cp -a "$root/scripts/rollback.sh" /var/lib/vynalth-dns/rollback.sh
# Automatic rollback protects SSH; confirmation must come from a fresh SSH session.
systemd-run --unit=vynalth-rollback --on-active=180s /bin/bash /var/lib/vynalth-dns/rollback.sh
trap '/bin/bash /var/lib/vynalth-dns/rollback.sh' ERR
batch=$(mktemp)
if nft list table inet vynalth_dns >/dev/null 2>&1; then
  echo 'delete table inet vynalth_dns' > "$batch"
fi
cat "$rendered/firewall.nft" >> "$batch"
nft --check --file "$batch"
nft --file "$batch"
rm "$batch"
install -m 0644 "$rendered/firewall.nft" /etc/vynalth-dns.nft
install -m 0644 "$root/scripts/vynalth-firewall.service" /etc/systemd/system/vynalth-firewall.service
mkdir -p /usr/local/lib/vynalth-dns
install -m 0755 "$root/scripts/firewall-load.sh" /usr/local/lib/vynalth-dns/firewall-load.sh
install -m 0644 "$rendered/unbound.conf" /etc/unbound/unbound.conf
mkdir -p /etc/systemd/system/unbound.service.d
install -m 0644 "$root/scripts/unbound-limits.conf" /etc/systemd/system/unbound.service.d/vynalth.conf
systemctl daemon-reload
systemctl enable vynalth-firewall.service
systemctl restart unbound
dig @127.0.0.1 localhost +time=2 +tries=1 | grep -q 'status: NOERROR'
echo 'Verify fresh SSH and approved external UDP/TCP clients within 180 seconds.'
echo 'Then: sudo bash scripts/confirm.sh ; otherwise rollback runs automatically.'
