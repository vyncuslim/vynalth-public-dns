# OPPO A5 Pro: private DNS preparation, NOT enabled

**PENDING LIVE ACCEPTANCE. No Oracle SSH/transfers/tests/deployment, Tailscale
administration, phone settings or public DNS changes were performed.**
Product Vynalth AI DNS, hostname dns.vynalthai.com, server100.95.65.20.
Windows100.85.132.14/32 and OPPO100.75.232.110/32 are the only external recursive
clients in this candidate. Android receives DNS access, not SSH authorization.
Localhost/default-refuse/IPv4-only private listeners and DNSSEC remain intact.

## User-reported OPPO observations (review comment6098859695)

Source: [owner review,2026-10-10](https://github.com/vyncuslim/vynalth-public-dns/pull/1#issuecomment-6098859695).
These are **user-reported**, not independently rerun by Codex. OPPO source
100.75.232.110, Termux BIND dig9.20.24, explicit queries only; default DNS was
not changed:

```text
dig @100.95.65.20 vyncuslim.com A +time=5 +tries=1
connection refused; no servers could be reached
Other attempts: timed out (5s)

dig @1.1.1.1 vyncuslim.com A +time=5 +tries=1
NOERROR; ANSWER:2; Query time:76ms
104.18.17.55 / 104.18.16.55 (observed, not test constants)
```

Vynalth Android DNS is **UNAVAILABLE in the reported probes**. The successful
same-phone control proves direct DNS can work, not a working Tailscale UDP/TCP53
path. Earlier overlay ping and localhost-only listener evidence are historical.
Refusal/timeout alone cannot identify current listener/firewall/packet-path cause.
`~ $` prompt and `;;` output pasted into Bash produce unrelated shell errors.
Local simulation PASS remains valid for its isolated scope; real acceptance is
**PENDING LIVE ACCEPTANCE**, not PASS. Do not repeat private probes before the
service is enabled, change Private DNS DoT hostname or blanket DNS Override.

Next: separately authorized [read-only audit](ORACLE_READ_ONLY_AUDIT.md), then
the sequential [approval gates](PHASE_B_APPROVAL_CHECKLIST.md). No live host
access or action was performed for this follow-up.

## Failure diagnosis / implementation

User reports Tailscale connectivity works but dig gets connection refused. The
historical production service evidence showed localhost-only listeners; private deployment
has not occurred. Adding an ACL in Git does not open the existing listener.
Transport refusal is not DNS RCODE REFUSED or a successful DNSSEC rejection.
We did not access Oracle to reconfirm its current state; retained laboratory/
process/impact review remains separately pending in LIVE_VM_IMPACT.md.

Both exact /32 ACLs are generated in config.private.example.json. Renderer rejects
missing/extra/duplicate clients in the identified private candidate. No /10/all-
tailnet allow, wildcard/public interface, permissive validator or zero discard.
Per-client20qps now permits up to40qps across two devices;128 pending slots and
384MiB/64tasks/1024FD limits remain. The finite15000ms retention is still private
only and needs a separate abuse/resource review for any public promotion.
Root PTR20.65.95.100.in-addr.arpa. remains dns.vynalthai.com.; other reverse owners
are not overridden. No private addresses published in authoritative DNS.

## Acceptance schedule: Android does not extend the Windows transaction

The protected Windows17-query/cold-warm/cache/ACL procedure is unchanged. Global
T0 still precedes all commands/network/verification; confirmation strictly<140s,
acceptance<=100s/remaining budget, independent rollback180s. No timer cancellation,
fresh time window, second confirmation run or automatic retry is added.

Keep the phone from querying this resolver during the protected Windows cold
checks. Do not set system/global DNS or run mobile dig while that transaction is
pending. Unexpected prior queries still fail first-use Windows acceptance.

After separately authorized Windows private-service confirmation only, run the
**separately approved DNS-only Android release gate**. It does not deploy, confirm,
SSH, flush cache, touch timers or change settings. Its ten single-shot queries
have a45s total cap and32s sum of per-query limits: A/AAAA UDP/TCP, PTR UDP/TCP,
valid/bogus DNSSEC UDP/TCP. It binds the actual phone source100.75.232.110. It fails
on timeout/wrong signature/result/insufficient remaining time; no silent retry.
Server cache may already be warm: no cold claim or cache-hit assertion from
phone latency. A mobile receipt cannot replace the Windows confirmation receipt.

Android/system-wide rollout remains BLOCKED until this mobile gate passes. A
Windows-only service confirmation is not a claim that both devices work. If the
phone fails after Windows confirmation, stop rollout and request an explicit
service-recovery decision; do not cancel timers or automatically redeploy/undo an
already confirmed transaction. Latest real two-device network acceptance is not
performed by the local synthetic tests.

With approved phone test tools (Python/dnspython and repository tests/acceptance.py
available in a local checkout), AFTER that separate authorization:

```sh
python scripts/mobile-acceptance.py --authorized-post-confirmation-test \
  --deadline-seconds 45 --out artifacts/oppo-private-dns.json
dig @100.95.65.20 vyncuslim.com A +time=5 +tries=1
dig @100.95.65.20 vyncuslim.com AAAA +tcp +time=5 +tries=1
dig @100.95.65.20 -x 100.95.65.20 +time=2 +tries=1
```

These extra manual queries are post-transaction diagnostics, not additional
unbudgeted protected acceptance. Answers are dynamic, never hardcoded. Expected
PTR dns.vynalthai.com.; valid signed answers NOERROR+AD; bogus SERVFAIL without
AD. Timeout/refusal/transport failure is FAIL, not validation success.

## System-wide preparation: admin change still requires separate approval

Before any change, record phone Tailscale DNS preference, native Private DNS
mode/provider, Wi-Fi/cellular DNS settings and prior tailnet nameservers/override.
Test direct DNS on both devices first. Inventory EVERY device affected by global
policy: this resolver rejects all other IPs, so a tailnet-wide override can break
unapproved devices. Do not widen ACLs or switch override to make tests pass.

Tailscale can distribute nameservers and override local DNS; its client can opt
out of tailnet DNS. After deployment/health/affected-client review and explicit
admin approval,100.95.65.20 may be configured as the intended nameserver and the
phone's DNS preference enabled. Do **not** enable global Override now or while
any affected client lacks authorization/health. Actual OPPO UI/version behavior
and application bypass must be checked; a dig query to a specific IP does not
prove system-wide use. [Tailscale DNS](https://tailscale.com/docs/reference/dns-in-tailscale),
[client preferences](https://tailscale.com/docs/features/client/manage-preferences?tab=android).

Android's native Private DNS provider-hostname mode uses DNS-over-TLS. This
candidate implements UDP/TCP53, not DoT853/certificate validation. Do not enter
dns.vynalthai.com in that field unless a separately implemented/tested/approved
DoT service exists. Do not disable an existing privacy setting automatically.
[Android's DoT documentation](https://android-developers.googleblog.com/2018/04/dns-over-tls-support-in-android-p.html).

## Restore previous DNS if connectivity fails

Stop the mobile rollout. Restore the recorded phone DNS preference and native
Private DNS mode/provider, not an invented fallback. Where available, opt the
phone out of Tailscale DNS while preserving its VPN/management session. Re-test
normal Wi-Fi/cellular DNS/internet. For an approved tailnet-admin change, restore
the recorded previous nameservers/override under that scope; do not reset or
reauthenticate Tailscale or change other users' settings without approval.
If management is lost, follow the approved recovery plan; no automatic root
firewall/SSH/network edits. Retain failure evidence and request human review.

Current device acceptance/system-wide DNS are **PENDING LIVE ACCEPTANCE**.

## Negative-response compatibility update

See [negative DNS/DNSSEC investigation](DNS_NEGATIVE_INVESTIGATION.md). NOERROR with no requested
RRset can be legitimate NODATA; timeout is never SERVFAIL. Local signed/unsigned
and Compact Denial fixtures now cover provider-style differences; both device
ACLs/listeners/PTR remain unchanged. Real phone acceptance is still PENDING.
