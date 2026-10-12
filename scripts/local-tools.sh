#!/usr/bin/env bash
# Extract distribution packages into the user cache; do not install/start services.
set -euo pipefail
tool_dir="$HOME/.cache/vynalth-dns-tools"
mkdir -p "$tool_dir"
cd "$tool_dir"
apt-get download unbound dns-root-data libprotobuf-c1 libevent-2.1-7t64 libhiredis1.1.0 python3-dnspython nftables libnftables1 libnftnl11 libmnl0 libxtables12
for package in ./*.deb; do dpkg-deb -x "$package" root; done
export PATH="$tool_dir/root/usr/sbin:$PATH"
export LD_LIBRARY_PATH="$tool_dir/root/usr/lib/x86_64-linux-gnu"
export PYTHONPATH="$tool_dir/root/usr/lib/python3/dist-packages"
export DNS_ROOT_DATA="$tool_dir/root/usr/share/dns"
unbound -V
cd "${1:?pass repository absolute Linux path}"
python3 tests/local_runtime.py
shellcheck scripts/*.sh
shellcheck tests/*.sh
if [[ ${2:-} == --firewall ]]; then bash tests/firewall_lab.sh; fi
