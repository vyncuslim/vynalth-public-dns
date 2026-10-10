# Phase B optional DNS identity — review-only proposal

Status: **proposed, NOT integrated or authorized for deployment**.
Product label: **Vynalth AI DNS**.
Resolver display hostname: **dns.vynalthai.com**.
Existing private service IPv4: **100.95.65.20**.
Existing approved client (not newly authorized here): **100.85.132.14/32**.

## Scope and expected behavior

When a Windows client runs `nslookup vyncuslim.com 100.95.65.20`,
nslookup commonly tries a reverse PTR lookup of the **specified DNS server's IP**
to populate the `Server:` field. The private PTR answer would map
`20.65.95.100.in-addr.arpa.` to `dns.vynalthai.com.`.
The display is client-dependent and is not cryptographic server identity.

The proposal only teaches the **private Unbound resolver** one reverse DNS
record for its own Tailscale IP. No public authoritative DNS zone, NIC, routing,
Tailscale MagicDNS, OCI DNS, firewall or new public TCP/UDP port 53 changes.
Keep original default-deny client ACLs, DNSSEC validator, `hide-identity: yes`
and `hide-version: yes` unchanged. Do **not** expose a CHAOS TXT identity
as a substitute for PTR.

See [phase-b-dns-identity.conf](phase-b-dns-identity.conf) for the candidate
`server:` fragment. The zone is intentionally scoped to the full **single
reverse record owner**, not all of `100.64.0.0/10`. Do not add a public
`dns.vynalthai.com A/AAAA` pointing at the private address, nor claim public
reverse DNS delegation of the RFC 6598 Tailscale address. A forward record is
not necessary for the intended display behavior; separately evaluate forward
resolution and DNSSEC effects if forward/reverse consistency is later needed.

## Review and validation gates

1. Review the intended private IP, name and reverse octet order; check that
   `dns.vynalthai.com` is not already used for something incompatible.
2. In an **isolated Unbound process/test config only**, append the fragment to
   a copy of the reviewed private config. Run `unbound-checkconf` on that
   copy, and exercise the exact PTR and unrelated reverse lookups with UDP/TCP.
   Do not touch `/etc/unbound`, live DNS listeners, systemd or the VM network
   during this review.
3. Validate answers for `dig @127.0.0.1 -x 100.95.65.20` in the isolated
   resolver context. Expected: `NOERROR`, one PTR
   `dns.vynalthai.com.`; unrelated PTR resolution must remain unchanged.
   If the test resolver uses a nonstandard IP or port, target that endpoint
   instead of the live production listener.
4. When the private service is separately approved and successfully deployed,
   Windows acceptance should include `nslookup vyncuslim.com 100.95.65.20`
   and `nslookup -type=PTR 20.65.95.100.in-addr.arpa. 100.95.65.20`.
   Expect the PTR answer and, on clients honoring reverse lookup, a
   `Server: dns.vynalthai.com` label. The label is **not** a security
   guarantee, and it must not be treated as a prerequisite to trust.
5. Extend the one-shot bounded acceptance controller/checklist **before**
   any implementation approval. Preserve the hard 180-second independent
   rollback and the strictly-under-140-second confirmation bound; no
   extra unbudgeted retries, ad-hoc confirmations or CD bypass. Re-run all
   existing DNSSEC valid/bogus, timeout, ACL-denial and transport tests.

## Immutable approval boundary

The existing reviewed `plans/phase-b-unbound.conf` and 13-file
`plans/phase-b-service.sha256` are **unchanged** by this proposal. Its
old rendered config SHA256
`d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`
**does not include the PTR record**. Do not deploy the snippet separately,
manually edit production Unbound, or falsely claim the old hash covers it.

To implement, first integrate the fragment into the proposed full config and
rendering source, regenerate both configuration hash and bundle manifest,
extend repeatable tests/acceptance scripts, validate rollback and capture a
new reviewed post-reboot fingerprint. Then review exact GitHub/Windows/VM
commit and obtain **fresh explicit authorization** for one private-only trial.
No deployment, automatic merge, reload, restart, reboot or public DNS is
authorized by adding this proposal to GitHub.
