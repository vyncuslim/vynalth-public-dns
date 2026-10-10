# Vynalth AI DNS: review-ready development candidate, not deployed

**STOP all Oracle writes, transfers, tests, cleanup and timer operations.**
The earlier isolation ran on the live VM and violated the development boundary.
See [LIVE_VM_IMPACT.md](LIVE_VM_IMPACT.md) for the explicit deviation, prior
cleanup, retained paths/processes/units and uncertain current status. No new
Oracle command was issued after the stop; only existing SSH output was read.
Further audit/cleanup/testing/deployment requires separate human approval.

Product **Vynalth AI DNS â€” Vynalth AI Secure Recursive DNS Resolver**.
Private server100.95.65.20; approved Windows clients100.85.132.14/32 and100.75.232.110/32;
informational hostname dns.vynalthai.com. Starting actual GitHub HEAD was
9bc27af72a1a2229d440f025caf2aefa777a784e; it was safely fast-forwarded, not overwritten.

## Immutable identities

Configuration SHA256:
`d6db3048b2c8dce15bf3ebe50be89ce12680345f48ce72eb466b715d29317634`.
Candidate post-boot baseline SHA256:
`cbb29c44eebd8d3423dffffe99009c1f3cbaa2e5325439b81a7a73a3aa84820b`.
Current21-file [service manifest](plans/phase-b-service.sha256) and
[review evidence manifest](plans/identity-review.sha256) use actual bytes.
Old d2e4c258 config and pre-reboot baseline are historical, not authorization.
See [full config](plans/phase-b-unbound.conf), [diff](plans/phase-b-unbound.diff),
[candidate report](plans/integration/candidate-report.json).

The renderer opts into the exact private listener/hostname and computes only:

```unbound
    local-zone: "20.65.95.100.in-addr.arpa." static
    local-data: "20.65.95.100.in-addr.arpa. 3600 IN PTR dns.vynalthai.com."
```

This full owner covers no other valid IPv4 PTR owner. No public private-address
A/AAAA/PTR, broad reverse override, MagicDNS/SSH hostname or authoritative change.
Static data answers locally; absence in that static zone gives NXDOMAIN/NODATA.
[Official Unbound documentation](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html).
Real package behavior was tested before the stop. nslookup label is informational,
not authenticated identity. Exact UTF-8/LF rendering is tested on Windows.

DNSSEC/validator+iterator/root hints/no-forwarding, default-refuse ACLs, approved
source+localhost, private-only UDP/TCP listeners, AppArmor policy, rebinding,
QNAME minimisation,1232-byte responses,20qps/client,16/32MiB caches,128 slots,
384MiB/64tasks/1024FD and minimal logging are retained. Finite15000ms is private
only; no zero discard/permissive validation/public promotion. Added retention
and abuse exposure still require a separate public resource/security review.

## Post-boot baseline evidence: not automatically approved

Original Oracle artifacts/post-boot-capture.json was available before the stop.
Read-only retrieval matched the supplied full SHA256:
`5e1b72073fa74dbd975601a513fa1b5c9e34ac773b45ebdc88863239d82bc4b3`.
Unmodified bytes are in plans/integration/post-boot-capture.json. Two fingerprints
equal: kernel7.0.0-1013-oracle, PID984, boot06c41b28-e22e-4540-8bd7-61b91fcaf465,
unbound(enforce), no reboot flag/operational failures. Later10:50:09UTC sample
matched, NTP=yes and no maintenance failures. Current state is NOT REINSPECTED.
The baseline remains explicitly review-only/human-approval-required. Do not
auto-refresh it or substitute a PID. No further maintenance reboot is authorized.

One early read-only invocation emitted a generic failure without a field receipt;
its exact cause is unproven. Detailed later snapshot matched. The checker now
sets repository cwd explicitly and emits drift/maintenance/clock/reboot fields;
a direct pre-stop invocation passed. This did not authorize deployment or turn
the initial failed invocation into PASS.

## Current transaction protections

See [PHASE_B.md](PHASE_B.md) for the superseding end-to-end coordinator.
Client monotonic T0 precedes ALL command/network/verification time. The remaining
global140s budget bounds every command. A read-only authenticated monotonic/boot
probe conservatively maps the deadline to the server, including response latency
and a1s margin. Server confirmation requires that deadline AND local elapsed<140;
missing clock context never falls back to a fresh server140s window. Clock-rate/
suspend assumptions require review and future authorized acceptance; no absolute
hard-real-time availability claim is made. Submit before120s, remote confirm15s,
RPC19s, acceptance<=100s/remaining global budget. Lost reply is UNKNOWN/no retry.

Independent180s rollback before writes must pass actual readiness. Installed
rollback is root-owned0700; all private recovery forces --service-only so a lost
marker cannot trigger legacy firewall code. Full PASS inventory/PTR/DNSSEC flags/
codes/cache/ACL evidence and current config/process/limits/AppArmor/listener/
management/installed-rollback integrity are required. Errors/signals recover.
Confirmation keeps protection armed through atomic snapshot commit; at180s the
timer no-ops if no pending snapshot remains. Archive PID suffix prevents same-
second collision. No stop/cancel/force/automatic retry is permitted.

## Actual testing and its limits

Latest local Windows suite: **48 unit tests PASS**. Local WSL private-mount actual
rollback file tests: **4 cases PASS** (prior limits present/absent, marker present/
absent), plus no-pending-snapshot callback PASS; service calls stubbed, nft
prohibited. A same-second archive collision first failed and was fixed/tested.
Python compilation, Bash syntax, YAML, rendered equality and21-file hashes PASS.
Local WSL has no Unbound; latest full service/clock protocol is NOT runtime-tested
there. CI account is billing-blocked, not PASS. Shellcheck absent/NOT TESTED.
No Oracle rerun of post-stop changes. Root-owned installation/global deadline/
archive fix therefore have local/contract evidence, not final live ARM acceptance.

Before the stop,38Windows/38Oracle ARM64 tests passed on the then-current code;
these are historical results. Enforcing Unbound tests passed PTR UDP/TCP,
unrelated reverse with/without identity, A/AAAA, valid/bogus/CD DNSSEC, NXDOMAIN,
approved loopback/unapproved A+PTR refusal, cache, rebinding, truncation/TCP
fallback, bounded local outage/recovery/restart/rate test. The platform choice
was a deviation, even though functional results were recorded.

Historical384MiB/64-task/1024FD enforcing/no-forwarder fixture cold cases returned
valid/bogus results at6.008725â€“6.016141s, distinct warm hits measured. Independent
recursion valid cloudflare.com UDP/TCP NOERROR+AD1.111152/0.521043s; bogus
dnssec-failed.org SERVFAIL without AD2.468710/2.941162s. Timeout never counts as
rejection success. Original live timeout exact cause remains uncertain;1900ms
expiry mechanism was reproduced previously. These are not Windows acceptance.
Two real180s laboratory restores reported PASS before/post existing SSH completion;
latest181.403s monotonic/182s integer observation. Production service operations
were stubbed, fingerprints reported unchanged. Current residual impact unknown.

All raw historical/final local evidence is in plans/integration/. No production
Unbound deployment/restart/config change was observed, but host filesystem/
resource/transient-unit/log activity did occur. See the impact inventory. Do not
claim current absence of processes or delete remaining artifacts without approval.

## Windows acceptance: PENDING, reference only

Only after separate protected deployment approval/acceptance/confirmation:

```powershell
Resolve-DnsName -Name '20.65.95.100.in-addr.arpa.' -Type PTR -Server 100.95.65.20 -DnsOnly
nslookup -timeout=2 -retry=1 -type=PTR 20.65.95.100.in-addr.arpa. 100.95.65.20
nslookup -timeout=5 -retry=1 vyncuslim.com 100.95.65.20
```

PTR success: NOERROR, exactly dns.vynalthai.com. Display success: Server:
dns.vynalthai.com, Address:100.95.65.20 and actual dynamic vyncuslim.com A/AAAA.
Never hardcode illustrative IPs. Wrong/missing PTR/server address/timeout fails.
UnKnown despite correct PTR is a pending client display issue, not crypto proof.
Extra manual queries occur after cold acceptance; the controller owns first-use
queries. Windows live display/Tailscale DNS/second unapproved tailnet client:
**NOT TESTED / PENDING LIVE ACCEPTANCE**.

## Blockers / approvals

Human review of exact full commit/config/baseline/21-file bundle/procedure;
separate read-only impact audit, then itemized cleanup approval if wanted; new
approved source staging and private trial only after that review. No old approval
covers current code. Oracle repository was24aa2d0 when last checked, not staged.
No reboot, SSH/firewall/Tailscale/OCI/Spectrum/public DNS/OS-policy/paid resource,
install.sh or Terraform authorization. Independent console/current recovery,
latest live state/clock behavior and complete Windows acceptance remain unknown.
RM0 is an unverified budget target. Keep PR Draft, stop at review, never merge.

## Two-device development update

The current candidate authorizes Windows 100.85.132.14/32 and OPPO Android
100.75.232.110/32 for DNS only. Windows remains the sole SSH administrator.
See ANDROID_DNS.md and the latest VALIDATION.md section. Previous live receipts
are historical; they do not validate this modified configuration or approve
the post-boot baseline. No Oracle access occurred during this update.
