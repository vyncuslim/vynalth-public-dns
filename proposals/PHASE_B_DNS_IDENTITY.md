# Phase B private DNS identity: implemented candidate, not deployed

Product: **Vynalth AI DNS — Vynalth AI Secure Recursive DNS Resolver**.
Hostname **dns.vynalthai.com**, private server100.95.65.20 and approved Windows
client100.85.132.14/32 remain unchanged. See [current candidate review](../POST_BOOT_REVIEW.md).

The generator and full proposed config now contain only PTR owner
20.65.95.100.in-addr.arpa. -> dns.vynalthai.com. The fragment documents those
lines; do not apply it separately. No broad reverse override, public A/AAAA/PTR,
authoritative DNS, MagicDNS, OS hostname, routing, SSH or firewall change.
The nslookup Server label is informational and client-dependent, not authenticated
identity. Keep hide-identity/hide-version; do not expose CHAOS identity/version.

New config SHA256:
`e20308ba789cd7aebeb0a4e009c5df120a0523ebf9a8891176a8b67ddd6c5b1b`.
The old d2e4c258 hash did not cover PTR and is historical. The updated18-file
manifest covers the full config and integrated timer/confirmation/baseline guards.
Default-refuse ACLs, private listeners, DNSSEC/iterator/root hints, AppArmor,
rebinding protection, bounded resources/timeouts and private-only15000ms remain.

Isolated Ubuntu ARM64 tests cover syntax, exact UDP/TCP PTR, unrelated reverse
with/without identity, approved loopback and unauthorized A/PTR refusal, A/AAAA,
valid/bogus/CD DNSSEC, NXDOMAIN, cache and timeout behavior. Production is unchanged.
Actual Windows display, Tailscale DNS access and a second unapproved tailnet
client remain **NOT TESTED / PENDING LIVE ACCEPTANCE**.

After separate deployment approval and protected acceptance/confirmation only:

```powershell
nslookup -timeout=2 -retry=1 -type=PTR 20.65.95.100.in-addr.arpa. 100.95.65.20
nslookup -timeout=5 -retry=1 vyncuslim.com 100.95.65.20
```

Expected PTR dns.vynalthai.com.; expected Server label on clients honoring PTR.
A/AAAA answers are dynamic, never hardcoded. Extra manual queries must run after
first-use acceptance; the controller itself checks both PTR transports without
warming root/TLD caches. Wrong/missing/timed-out identity never counts as PASS.

No prior approval covers these changes. Review the actual full GitHub/Windows/VM
commit, new config hash, reviewed post-boot baseline,18-file bundle, one-shot
acceptance and explicit changed timer/confirmation design. Independent180s
rollback before writes,100s acceptance, full PASS and strict<140s confirmation
remain mandatory. No deployment, merge, reload, restart, reboot, paid resource
or public DNS action is authorized by this document.
