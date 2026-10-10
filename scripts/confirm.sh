#!/usr/bin/env bash
set -euo pipefail
# Serialize confirmation against a timer that has already begun rollback.
exec 9>/var/lib/vynalth-dns/transaction.lock
flock -x 9
test -d /var/lib/vynalth-dns/rollback
systemctl stop vynalth-rollback.timer
mv /var/lib/vynalth-dns/rollback "/var/lib/vynalth-dns/confirmed-$(date +%s)"
echo 'Policy confirmed; retained backup for manual recovery.'
