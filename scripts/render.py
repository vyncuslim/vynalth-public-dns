"""Render development-only resolver/firewall policy. Never enables public recursion."""
import argparse
import ipaddress
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def host_network(value):
    net = ipaddress.ip_network(value, strict=True)
    if net.prefixlen != net.max_prefixlen or net.network_address.is_unspecified or net.network_address.is_multicast:
        raise ValueError("development clients must be individual /32 or /128 hosts")
    return net

def render(config):
    addr = ipaddress.ip_address(config["listen"])
    if addr.is_unspecified or addr.is_multicast:
        raise ValueError("listen must be a specific local address")
    ipv6 = config.get("ipv6", False)
    if not isinstance(ipv6, bool):
        raise ValueError("ipv6 must be boolean")
    if addr.version == 6 and not ipv6:
        raise ValueError("IPv6 listener requires ipv6=true")
    clients = [host_network(x) for x in config.get("clients", [])]
    ssh = [host_network(x) for x in config.get("ssh_clients", [])]
    if any(x.version == 6 for x in clients + ssh) and not ipv6:
        raise ValueError("IPv6 clients require ipv6=true")
    rate = config.get("ip_ratelimit", 20)
    if type(rate) is not int or not 1 <= rate <= 100:
        raise ValueError("ip_ratelimit must be 1..100")
    tailscale = config.get('tailscale')
    interface = None
    if tailscale:
        interface = tailscale.get('interface', 'tailscale0')
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}', interface):
            raise ValueError('Invalid Tailscale interface')
        if addr not in ipaddress.ip_network('100.64.0.0/10'):
            raise ValueError('Tailscale deployment must use a specific Tailscale IPv4 listener')
        if any(x.version != 4 or x.network_address not in ipaddress.ip_network('100.64.0.0/10') for x in clients + ssh):
            raise ValueError('Tailscale SSH/DNS clients must be individual tailnet IPv4 hosts')
        port = tailscale.get('udp_port', 41641)
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Invalid observed Tailscale transport port')
    dhcp = config.get('dhcp4')
    if dhcp:
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}', dhcp['interface']):
            raise ValueError('Invalid DHCP interface')
        dhcp_server = ipaddress.IPv4Address(dhcp['server'])
    preserve_ssh = config.get('preserve_existing_public_ssh', False)
    if type(preserve_ssh) is not bool:
        raise ValueError('Public SSH preservation must be boolean')
    conf = (ROOT / "unbound/base.conf").read_text()
    conf += '\nserver:\n    interface: ' + str(addr) + '\n'
    if not addr.is_loopback:
        conf += '    interface: 127.0.0.1\n'
    conf += f'    do-ip6: {"yes" if ipv6 else "no"}\n    ip-ratelimit: {rate}\n'
    conf += ''.join(f'    access-control: {x} allow\n' for x in clients)
    identity = config.get('dns_identity')
    if identity is not None:
        # Private identity is deliberately a single owner, never a broad reverse zone.
        if not tailscale or identity != {'address': str(addr), 'hostname': 'dns.vynalthai.com.'}:
            raise ValueError('DNS identity requires the matching private listener and reviewed hostname')
        if str(addr) != '100.95.65.20':
            raise ValueError('DNS identity is only approved for the Vynalth private server')
        owner = addr.reverse_pointer + '.'
        conf += f'    local-zone: "{owner}" static\n'
        conf += f'    local-data: "{owner} 3600 IN PTR {identity["hostname"]}"\n'
    # Dedicated table; no flush ruleset, no modification to OCI/provider firewall.
    rules = ['table inet vynalth_dns {', ' chain input {',
             '  type filter hook input priority -10; policy drop;',
             '  iifname "lo" accept', '  ct state invalid drop',
             '  ct state established,related accept',
             '  ip protocol icmp accept', '  meta l4proto ipv6-icmp accept']
    if tailscale:
        # Encrypted WireGuard transport, NOT recursive DNS authorization.
        rules.append(f'  iifname != "{interface}" udp dport {port} accept')
    if dhcp:
        rules.append(f'  iifname "{dhcp["interface"]}" ip saddr {dhcp_server} udp sport 67 udp dport 68 accept')
    if preserve_ssh:
        # Review-only migration option, preserves existing host exposure.
        physical_only = f'iifname != "{interface}" ' if interface else ''
        rules.append(f'  {physical_only}tcp dport 22 ct state new accept comment "preserve existing SSH pending recovery review"')
    prefix = f'iifname "{interface}" ' if interface else ''
    for x in ssh:
        family = 'ip' if x.version == 4 else 'ip6'
        rules.append(f'  {prefix}{family} saddr {x} tcp dport 22 ct state new accept')
    for x in clients:
        family = 'ip' if x.version == 4 else 'ip6'
        for protocol in ('udp', 'tcp'):
            destination = f'ip daddr {addr} ' if interface else ''
            rules.append(f'  {prefix}{family} saddr {x} {destination}{protocol} dport 53 limit rate {rate}/second burst {rate * 2} packets accept')
    rules.extend([' }', '}'])
    return conf, '\n'.join(rules) + '\n'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('--out', type=Path, default=Path('artifacts/rendered'))
    args = parser.parse_args()
    conf, firewall = render(json.loads(args.config.read_text()))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'unbound.conf').write_bytes(conf.encode('utf-8'))
    (args.out / 'firewall.nft').write_bytes(firewall.encode('utf-8'))

if __name__ == '__main__':
    main()
