# Architecture

Phase B approved test client → OCI public IPv4 (only if approved and billing verified)
→ existing VCN/subnet + reviewed security lists/NSGs → host nftables → Unbound UDP/TCP 53.
Unbound → root servers → TLD servers → authoritative servers; no forward-zone.
DNSSEC uses the Ubuntu dns-root-data initial anchor, then RFC5011 managed state.
DNSSEC requires accurate system time; validate chrony/systemd-timesyncd before acceptance.

Phase C target: global clients → Spectrum UDP/TCP 53 → origin restricted to
verified Spectrum egress addresses → identity-preserving listener → Unbound.
This path is deliberately NOT implemented as a deployable public policy yet.

## Client identity blocker

Cloudflare UDP Simple Proxy Protocol is a 38-byte prefix with magic 0x56EC,
IPv6 or IPv4-mapped addresses and network-order ports. Unbound's documented
native listener accepts PROXYv2, a different wire format; Ubuntu's installed
version must be checked independently. Direct SPP → Unbound is not compatible.
TCP PROXYv2 support also requires version verification and fixture/live testing.
Do not enable any proxy protocol on this repository's ordinary DNS listener.

A future reviewed adapter must validate trusted transport peers, strictly decode
SPP, preserve source identity into ACLs/rate limits, bound response association
state and correctly encapsulate return datagrams. Merely stripping the prefix
and forwarding everything from localhost loses identity and is unacceptable.
Do not open recursion to Cloudflare ranges and mistake that for client authorization.
No custom adapter is shipped or claimed tested here.

## Network and resilience

Re-use discovered VCN/subnet. Existing security lists and NSGs are additive;
a restrictive NSG cannot cancel a permissive security list. Review effective
IPv4/IPv6 ingress and egress, all VNIC attachments, 0/0 routes, IGW enabled state,
public subnet flags and image architecture. If existing security lists are open,
stop and propose a separately approved network change.
Allow only approved admin hosts on SSH/53; egress requires UDP/TCP 53 to arbitrary
authoritative infrastructure, time sync and HTTPS package updates. No NAT/LB created.
Host firewall adds its own table, retaining existing OCI/host tables.

A single small VM is a single failure domain. For production require separately
approved secondary origin, capacity in a distinct failure domain, billing-covered
health checks/failover and failure drills. Health checks must test UDP/TCP answers,
DNSSEC and recursion, not merely open port 53. Do not promise global Anycast or SLA.

Sources (verified 2026-10-10):
- https://developers.cloudflare.com/spectrum/reference/simple-proxy-protocol-header/
- https://developers.cloudflare.com/spectrum/how-to/enable-proxy-protocol/
- https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html
