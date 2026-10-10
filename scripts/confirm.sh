#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || { echo 'Usage: sudo bash scripts/confirm.sh COMPLETE_PASS_RECEIPT.json SSH_CONNECTION'; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
(cd "$root" && sha256sum --check plans/phase-b-service.sha256)
# Serialize confirmation against a timer that has already begun rollback.
exec 9>/var/lib/vynalth-dns/transaction.lock
flock -x 9
test -d /var/lib/vynalth-dns/rollback
test -f /var/lib/vynalth-dns/rollback/service-only
trap 'flock -u 9; /bin/bash /var/lib/vynalth-dns/rollback.sh --service-only; exit 1' ERR TERM INT
(cd /var/lib/vynalth-dns/rollback && sha256sum --check snapshot.sha256)
(cd /var/lib/vynalth-dns/rollback && cmp snapshot.sha256 <(sha256sum unbound.conf; if [[ -f unbound-private-limits.conf ]]; then sha256sum unbound-private-limits.conf; fi))
"$root/.venv/bin/python" "$root/scripts/confirmation-check.py" "$1" "$2"
systemctl is-active --quiet vynalth-rollback.timer
# Keep the timer armed through the atomic confirmation commit. At its deadline
# rollback.sh sees no pending snapshot and exits without touching the service.
"$root/.venv/bin/python" "$root/scripts/confirmation-check.py" "$1" "$2" --deadline-only
mv -T /var/lib/vynalth-dns/rollback "/var/lib/vynalth-dns/confirmed-$(date +%s)-$$"
echo 'Policy confirmed; retained backup. Timer remains armed and will no-op at its deadline.'
