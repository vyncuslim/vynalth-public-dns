#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
tool_dir="$HOME/.cache/vynalth-terraform"
mkdir -p "$tool_dir"
cd "$tool_dir"
case $(uname -m) in
  x86_64) arch=amd64 ;;
  aarch64) arch=arm64 ;;
  *) echo 'Unsupported local test architecture'; exit 1 ;;
esac
file="terraform_1.9.8_linux_${arch}.zip"
curl -fLsS "https://releases.hashicorp.com/terraform/1.9.8/$file" -o "$file"
curl -fLsS https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_SHA256SUMS -o SHA256SUMS
grep " $file$" SHA256SUMS | sha256sum --check
python3 -m zipfile -e "$file" .
chmod +x terraform
./terraform -chdir="$repo/terraform" fmt -check
./terraform -chdir="$repo/terraform" init -backend=false
./terraform -chdir="$repo/terraform" validate
