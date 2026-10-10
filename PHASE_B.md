# Vynalth AI DNS: development-only private candidate

**STOP: no live Oracle deployment, writes, transfers, testing, cleanup or timer
changes are authorized.** See [impact/deviation inventory](LIVE_VM_IMPACT.md).
All subsequent work is local/CI. Keep Draft PR1; never merge/deploy automatically.

Vynalth AI DNS — Vynalth AI Secure Recursive DNS Resolver.
Hostname dns.vynalthai.com, private server100.95.65.20, approved Windows
client100.85.132.14/32. PTR20.65.95.100.in-addr.arpa. returns dns.vynalthai.com.
Only this full owner is overridden, with no public DNS or broad reverse change.
The label is informational, not authenticated server identity.

## Immutable candidate identities

Config SHA256: `e20308ba789cd7aebeb0a4e009c5df120a0523ebf9a8891176a8b67ddd6c5b1b`.
Candidate post-boot baseline SHA256:
`cbb29c44eebd8d3423dffffe99009c1f3cbaa2e5325439b81a7a73a3aa84820b`.
The new20-file [manifest](plans/phase-b-service.sha256) pins config, baseline,
source generator, deployment/rollback/confirmation, client controller and probe.
Old d2e4c258 configuration and pre-reboot baseline are not current authorization.
Original post-boot evidence bytes were verified against5e1b7207...bc4b3; baseline
remains human-review-required, never automatically approved. See
[post-boot evidence](POST_BOOT_REVIEW.md), [full config](plans/phase-b-unbound.conf),
[actual config diff](plans/phase-b-unbound.diff), [validation](VALIDATION.md).

Retain independent validator/iterator/root hints, DNSSEC, no upstream forwarders,
default-refuse ACLs, localhost/approved client only,127.0.0.1+100.95.65.20 UDP/TCP53,
no public listener, AppArmor, rebinding protection, QNAME minimisation,1232-byte
UDP bound,20qps/client,16/32MiB caches,128 query slots,384MiB/64tasks/1024FD limits,
finite15000ms private reply-age bound and no individual query logging.
Never use permissive validation/zero discard timeout or promote15000ms publicly.

## Global deadline: no new140s window after preflight

`scripts/private-transaction.py` starts client monotonic T0 before Git checks,
SSH, clock probe or verification. ALL command execution/network/verification/
deployment/acceptance/receipt-transfer/confirmation consume the same140s budget.
Each subprocess is bounded by the remaining global time, never a reset deadline.

An authenticated read-only server monotonic/boot probe is conservatively mapped
to the client deadline: server emission time + client remaining time at receipt
-1s safety margin. Reply latency makes this deadline earlier. It is boot-bound;
malformed/missing clock context fails closed. Clock rates must remain monotonic
and sufficiently stable for the margin; no unconditional hard-real-time or
arbitrary VM clock/suspend guarantee is claimed. Future approved acceptance must
verify clock assumptions. No new live timing test was run after the stop.

The deploy script requires this mapped deadline/probe boot ID as arguments;
it cannot fabricate server-start+140 as the sole end-to-end bound. Confirmation
requires both global mapped deadline and server-local elapsed<140. Complete
one-shot receipt plus current config/process/limits/AppArmor/listener/management/
installed-rollback integrity must pass. No missing/failed/late record can confirm.
Submit confirmation before client120s; SSH connects within4s, remote confirmation
is capped15s and local RPC19s. The reserve is stricter, not a relaxed global bound.

Independent180s timer arms before active writes and must pass readiness checks.
Snapshot records boot/start/global deadline/config hash. Installed rollback is
root-owned0700 and all private recovery calls force `--service-only`, preventing
legacy firewall fallback if the marker disappears. Missing marker blocks confirm.
Rollback restores original config/settings, preserves unrelated drop-ins and
uses a PID-suffixed archive to avoid same-second collisions. Errors/signals invoke
recovery; the timer stays armed through atomic confirmation. After confirmed-*
commit it remains armed until180s, then no-ops because no pending snapshot exists.
Never cancel protection early, retry, force confirm or start another transaction
while its timer remains active. Lost confirmation reply is UNKNOWN: inspect under
separate approval, never assume PASS or automatically retry.

| Ordered acceptance | Per-query cap | Required result |
|---|---:|---|
| Private PTR UDP/TCP | 2s | exactly dns.vynalthai.com. |
| First-use valid/bogus DNSSEC UDP | 15s | NOERROR+AD / SERVFAIL without AD |
| Separate warm UDP/TCP valid/bogus | 2s | same codes/flags, >=4 measured hits |
| A/AAAA/TCP/NXDOMAIN/root DNSKEY/standard | 5s | expected records/codes/flags |
| Bogus CD diagnostic UDP/TCP | 5s | NOERROR+CD, no AD; never validation PASS |
| Unapproved127.0.0.2 UDP/TCP | 2s | REFUSED both |

Acceptance cap100s AND remaining global reserve; restart40s; global confirmation
strict<140s; rollback180s. First-use count must be one readiness query. Extra
nslookup/manual tests belong AFTER protected acceptance/confirmation. Real second
unapproved tailnet client, Windows display and private live DNS remain PENDING.

## Future execution reference: NOT authorized, DO NOT RUN now

First obtain explicit approval for actual full commit, new config hash, approved
post-boot baseline,20-file bundle, protected procedure and source staging. Oracle
working HEAD was24aa2d0 at last check and was not staged to this candidate.
Require clean matching GitHub/Windows/VM commits, all hashes, exact fresh60s
two-sample baseline, idle maintenance/locks and >15min known schedule, NTP,
enforcing profile, original listeners/drop-ins, approved private SSH/Tailscale,
retained session/recovery and no pending transaction. Drift requires new review.
Do not disable updates, reboot or alter management/network/public DNS.

Only after that separate authorization, the global controller is the sole
documented coordinator (the old unbounded PowerShell sequence is superseded):

```powershell
python scripts/private-transaction.py --execute-authorized-private-trial `
  --commit '<ACTUAL_REVIEWED_FULL_COMMIT>' `
  --config-sha256 e20308ba789cd7aebeb0a4e009c5df120a0523ebf9a8891176a8b67ddd6c5b1b `
  --baseline-sha256 cbb29c44eebd8d3423dffffe99009c1f3cbaa2e5325439b81a7a73a3aa84820b `
  --ssh-key 'C:\Users\lynne\Downloads\ssh-key-2026-10-09 (1).key' `
  --out artifacts/private-transaction.json
```

Flag/placeholder is not human approval. No code here has been run against Oracle
after the stop. On failure, the future authorized coordinator attempts service-
only recovery once; disconnected recovery relies on the independent timer.
Recovery may outlive140s but cannot authorize late confirmation. Actual service/
snapshot state must be inspected before claiming rollback or deployment success.

## Separate firewall proposal: not approved for application

[The proposed dedicated table](plans/phase-b-firewall.nft) passed VM `nft --check`.
There is currently no `vynalth_dns` table, so the exact proposed change is adding
this entire table; existing Oracle and Tailscale tables would be retained.

Its input hook runs at priority -10 before the existing iptables-nft filter hook.
Accept in one base chain does not override a later chain's rejection; a drop in
this chain is final even if Tailscale later accepts. Consequently the proposal
explicitly allows loopback, established/related traffic, ICMP/ICMPv6, observed
UDP 41641 encrypted transport, and DHCP from `169.254.169.254` on `enp0s6`.
Private DNS requires both `tailscale0` and approved source/destination addresses.
No blanket `tailscale0` input accept is introduced. Tailnet SSH is explicit.

`preserve_existing_public_ssh=true` retains current host TCP 22 access on
non-Tailscale interfaces while recovery is unresolved; it does not add an OCI
ingress rule or permit other tailnet SSH clients in the project table.
The host's existing unrestricted TCP 22 rule remains a security risk. A later
separate SSH restriction needs explicit approval and verified recovery.

The project table would block new Tailscale peer API ports and rpcbind. Confirm
which tailnet features are needed before approval. Outbound Tailscale/DERP uses
the unchanged output policy; forwarding tables and Oracle InstanceServices are
not edited. New Tailscale ports/backend/netfilter changes require re-audit.

Do not use `scripts/install.sh` for this service-only phase: it also installs
packages and applies firewall changes. Firewall approval requires the whole
reviewed diff, working OCI serial-console/other independent recovery, full
security-list/NSG attachment inventory, tested rollback and approved feature
impact. These gates are not complete. No firewall apply command is authorized.

## Cost boundary

Monthly target remains RM0. No resource, reservation, paid add-on or subscription
was created or changed. A1 1 OCPU/6 GiB and existing public IP are user-supplied
inventory; tenancy-wide free allocation, boot storage, public IP pricing,
egress and current invoice have not been verified. This is not a RM0 guarantee.
All additional paid resources and Spectrum functionality require pricing and
explicit approval. No Terraform apply/destroy is part of this plan.
