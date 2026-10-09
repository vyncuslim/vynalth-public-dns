#!/usr/bin/env bash
set -euo pipefail
test -d /var/lib/vynalth-dns/rollback
systemctl stop vynalth-rollback.timer
mv /var/lib/vynalth-dns/rollback "/var/lib/vynalth-dns/confirmed-$(date +%s)"
echo 'Policy confirmed; retained backup for manual recovery.'
