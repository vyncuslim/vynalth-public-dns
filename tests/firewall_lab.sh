#!/usr/bin/env bash
# Root-only isolated network/mount namespaces. No host firewall/service changes.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
if [[ ${1:-} != --inside ]]; then
  [[ $EUID == 0 ]] || { echo 'Run with sudo in the authorized local lab'; exit 1; }
  exec unshare --net --mount bash "$0" --inside
fi
mount --make-rprivate /
mkdir -p /run/netns
mount -t tmpfs tmpfs /run/netns
ip link set lo up
ip netns add client
ip link add origin0 type veth peer name client0
ip link set client0 netns client
ip addr add 198.18.0.1/24 dev origin0
ip link set origin0 up
ip netns exec client ip addr add 198.18.0.2/24 dev client0
ip netns exec client ip link set client0 up
ip netns exec client ip link set lo up
# Already permitted by Ubuntu's enforcing Unbound profile. No profile changes.
lab_parent=/var/lib/unbound
[[ -d $lab_parent ]] || lab_parent=/tmp
lab=$(mktemp -d "$lab_parent/vynalth-net-test.XXXXXX")
dns_pid=''
ssh_pid=''
cleanup() {
  [[ -z $dns_pid ]] || kill "$dns_pid" 2>/dev/null || true
  [[ -z $ssh_pid ]] || kill "$ssh_pid" 2>/dev/null || true
  ip netns del client || true
  rm -rf "$lab"
}
trap cleanup EXIT
printf '%s\n' '{"listen":"198.18.0.1","clients":["198.18.0.2/32"],"ssh_clients":["198.18.0.2/32"],"ip_ratelimit":20}' > "$lab/config.json"
python3 "$repo/scripts/render.py" "$lab/config.json" --out "$lab"
# No RFC5011 state writes in shared host filesystem.
data_dir=${DNS_ROOT_DATA:-/usr/share/dns}
cp "$data_dir/root.key" "$lab/root.key"
sed -i "s|/var/lib/unbound/root.key|$lab/root.key|; s|username: \"unbound\"|username: \"\"|" "$lab/unbound.conf"
sed -i 's|control-enable: yes|control-enable: no|' "$lab/unbound.conf"
sed -i "s|/usr/share/dns/root.hints|$data_dir/root.hints|" "$lab/unbound.conf"
sed -i "s|directory: \"/etc/unbound\"|directory: \"$lab\"|" "$lab/unbound.conf"
printf '\nserver:\n    pidfile: "%s/unbound.pid"\n    use-syslog: no\n    local-zone: "fixture.test." static\n    local-data: "a.fixture.test. 300 IN A 203.0.113.7"\n' "$lab" >> "$lab/unbound.conf"
nft --check -f "$lab/firewall.nft"
nft -f "$lab/firewall.nft"
unbound-checkconf "$lab/unbound.conf"
unbound -d -c "$lab/unbound.conf" > "$lab/unbound.log" 2>&1 &
dns_pid=$!
# TCP probe on SSH port tests network restrictions, NOT sshd authentication.
python3 -m http.server 22 --bind 198.18.0.1 > /dev/null 2>&1 &
ssh_pid=$!
sleep 1
for transport in +notcp +tcp; do
  answer=$(ip netns exec client dig @198.18.0.1 a.fixture.test A "$transport" +short +time=1 +tries=1)
  [[ $answer == 203.0.113.7 ]]
done
ip netns exec client python3 -c "import socket; s=socket.create_connection(('198.18.0.1',22),timeout=1); s.close()"
ip netns exec client ip addr del 198.18.0.2/24 dev client0
ip netns exec client ip addr add 198.18.0.3/24 dev client0
for transport in +notcp +tcp; do
  if ip netns exec client dig @198.18.0.1 a.fixture.test A "$transport" +time=1 +tries=1 >/dev/null 2>&1; then
    echo 'FAIL unauthorized DNS connection'; exit 1
  fi
done
ip netns exec client python3 -c "import socket
try:
    socket.create_connection(('198.18.0.1',22),timeout=1)
except (TimeoutError, OSError):
    pass
else:
    raise SystemExit('FAIL unauthorized SSH network connection')"
echo 'PASS isolated nftables: approved DNS UDP/TCP + SSH port; unapproved clients blocked'
