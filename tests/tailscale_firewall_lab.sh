#!/usr/bin/env bash
# Simulated Tailscale interface/iptables ordering, never touches host policy.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
if [[ ${1:-} != --inside ]]; then
  [[ $EUID == 0 ]] || exit 1
  exec unshare --net --mount bash "$0" --inside
fi
mount --make-rprivate /
mkdir -p /run/netns
mount -t tmpfs tmpfs /run/netns
ip link set lo up
for client in tail physical; do ip netns add "$client"; done
lab=$(mktemp -d /var/lib/unbound/vynalth-tail-test.XXXXXX)
dns_pid=''
ssh_pid=''
cleanup() {
  [[ -z $dns_pid ]] || kill "$dns_pid" 2>/dev/null || true
  [[ -z $ssh_pid ]] || kill "$ssh_pid" 2>/dev/null || true
  for client in tail physical; do ip netns del "$client" || true; done
  rm -rf "$lab"
}
trap cleanup EXIT
ip link add tailscale0 type veth peer name tail0
ip link set tail0 netns tail
ip addr add 100.95.65.20/10 dev tailscale0
ip link set tailscale0 up
ip netns exec tail ip addr add 100.85.132.14/10 dev tail0
ip netns exec tail ip link set tail0 up
ip netns exec tail ip link set lo up
ip link add enp0s6 type veth peer name physical0
ip link set physical0 netns physical
ip addr add 198.18.0.1/24 dev enp0s6
ip link set enp0s6 up
ip netns exec physical ip addr add 198.18.0.2/24 dev physical0
ip netns exec physical ip addr add 100.85.132.14/32 dev physical0
ip netns exec physical ip link set physical0 up
ip netns exec physical ip link set lo up
ip netns exec physical ip route add 100.95.65.20/32 via 198.18.0.1
python3 "$repo/scripts/render.py" "$repo/config.private.example.json" --out "$lab"
cp /usr/share/dns/root.key "$lab/root.key"
sed -i "s|/var/lib/unbound/root.key|$lab/root.key|; s|username: \"unbound\"|username: \"\"|; s|directory: \"/etc/unbound\"|directory: \"$lab\"|; s|control-enable: yes|control-enable: no|" "$lab/unbound.conf"
printf '\nserver:\n    pidfile: "%s/unbound.pid"\n    use-syslog: no\n    local-zone: "fixture.test." static\n    local-data: "a.fixture.test. 300 IN A 203.0.113.7"\n' "$lab" >> "$lab/unbound.conf"
nft --check -f "$lab/firewall.nft"
nft -f "$lab/firewall.nft"
# A later base chain's broad tailnet accept cannot undo our earlier drop.
nft 'add table inet simulated_tailscale'
nft 'add chain inet simulated_tailscale input { type filter hook input priority 0; policy accept; }'
nft 'add rule inet simulated_tailscale input iifname "tailscale0" accept'
unbound-checkconf "$lab/unbound.conf"
unbound -d -c "$lab/unbound.conf" > "$lab/unbound.log" 2>&1 &
dns_pid=$!
python3 -m http.server 22 --bind 100.95.65.20 > /dev/null 2>&1 &
ssh_pid=$!
sleep 1
for transport in +notcp +tcp; do
  [[ $(ip netns exec tail dig @100.95.65.20 a.fixture.test A "$transport" +short +time=1 +tries=1) == 203.0.113.7 ]]
  # Correct IP on a physical interface must not impersonate the tailnet client.
  if ip netns exec physical dig -b 100.85.132.14 @100.95.65.20 a.fixture.test A "$transport" +time=1 +tries=1 >/dev/null 2>&1; then
    echo 'FAIL physical source spoof accepted'; exit 1
  fi
done
ip netns exec tail python3 -c "import socket; socket.create_connection(('100.95.65.20',22),timeout=1).close()"
ip netns exec tail ip addr del 100.85.132.14/10 dev tail0
ip netns exec tail ip addr add 100.85.132.15/10 dev tail0
for transport in +notcp +tcp; do
  if ip netns exec tail dig @100.95.65.20 a.fixture.test A "$transport" +time=1 +tries=1 >/dev/null 2>&1; then
    echo 'FAIL unapproved tailnet DNS accepted'; exit 1
  fi
done
ip netns exec tail python3 -c "import socket
try:
    socket.create_connection(('100.95.65.20',22),timeout=1)
except (TimeoutError, OSError):
    pass
else:
    raise SystemExit('FAIL unapproved tailnet SSH accepted')"
echo 'PASS simulated Tailscale chain ordering: approved DNS/SSH, physical spoof and unapproved tailnet denied'
