#!/usr/bin/env bash
# Local/CI reads only. No SSH, deployment, service or network operations.
set -euo pipefail
cd "$(dirname "$0")/.."
for file in scripts/deploy-private.sh scripts/confirm.sh scripts/rollback.sh tests/local_rollback_files.sh; do
 bash -n "$file"
done
echo 'PASS Bash syntax for current private transaction/rollback files'
sha256sum --check plans/phase-b-service.sha256
sha256sum --check plans/identity-review.sha256
