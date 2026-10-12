#!/usr/bin/env bash
set -euo pipefail
batch=$(mktemp)
trap 'rm -f "$batch"' EXIT
if nft list table inet vynalth_dns >/dev/null 2>&1; then
  echo 'delete table inet vynalth_dns' > "$batch"
fi
cat /etc/vynalth-dns.nft >> "$batch"
nft --check --file "$batch"
nft --file "$batch"
