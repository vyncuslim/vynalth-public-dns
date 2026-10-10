# Existing Oracle VM: private service approval plan

> **DNS display-name proposal (not applied):** [Phase B private PTR identity review](proposals/PHASE_B_DNS_IDENTITY.md) and [candidate Unbound fragment](proposals/phase-b-dns-identity.conf) propose the Windows `Server: dns.vynalthai.com` label for `100.95.65.20` only. These review files are **not** included in the existing pinned config/bundle hashes or production deployment. Integrate, recalculate hashes, test, review a new post-boot baseline, and request new exact authorization before deploying. No Oracle setting or public DNS is changed by this proposal.

**Latest review: [POST_MAINTENANCE.md](POST_MAINTENANCE.md). No next deployment is
authorized or ready.** The fresh PID34123 baseline is stable and exact, but a
kernel reboot is pending and independent console recovery is unverified. Review
the separate maintenance proposal first, then commit/review a new post-boot
baseline and exact service authorization. The historical transaction commands
below are gated references, not permission to execute. Read-only readiness and
the additional timer-check patch are separately reviewable; the latter has not
been applied to the service bundle.

Status on 2026-10-10: the `036575d` attempt **failed and rolled back**; production
remains localhost-only. The subsequent investigation reproduced reply expiry at
the packaged 1900ms discard timeout and tested a finite 15000ms correction in
isolated enforcing processes. The user approved exact `61a9ad8`/the revised hash,
but the second trial was **aborted during preflight before deployment** because
automatic package maintenance restarted Unbound and changed its PID baseline.
No reviewed deployment, agent service restart, timer start or confirmation ran.
Further deployment is stopped; do not automatically retry under that approval.
See VALIDATION.md, `plans/second-attempt/` and the investigation receipts. A new
trial needs a stable maintenance window, refreshed baseline review and fresh
human authorization. The service bundle/config hash below remain unchanged.
No firewall, SSH, Tailscale, OCI, DNS record or package changes are authorized by
this plan. Public recursive service remains blocked.

Verified SSH source is Windows `100.85.132.14` connecting to `ubuntu@100.95.65.20`.
Host `vynalthai-dns`, Ubuntu 24.04.5 ARM64, enforcing Unbound AppArmor profile.
Keep the existing SSH session open; a fresh private SSH login succeeds. Public
SSH to `134.185.94.152` timed out and is **not verified recovery access**.

## Exact service change for approval

Review [the actual VM config diff](plans/phase-b-unbound.diff) and
[the complete config](plans/phase-b-unbound.conf),
[the new systemd drop-in](scripts/unbound-private-limits.conf), plus
[deployment](scripts/deploy-private.sh), [rollback](scripts/rollback.sh) and
[confirmation](scripts/confirm.sh) code at the reviewed branch commit.

The new main config replaces the distro include directive; the existing include
files are retained on disk. Their current trust anchor and Unix control socket
settings are explicitly preserved in the proposed config. The main changes are:

- IPv4 listeners `127.0.0.1:53` and `100.95.65.20:53`; no public or IPv6 listener.
- Default REFUSED ACLs; only localhost and `100.85.132.14/32` may recurse.
- DNSSEC, explicit packaged root hints, independent iterator, QNAME minimisation,
  rebinding protection, 1232-byte UDP responses and 20 queries/sec/client.
- 16/32 MiB caches; process memory 384 MiB, 64 tasks and 1024 descriptors.
- Finite `discard-timeout: 15000` ms, preserving a response-age bound. It retains
  pending replies longer than the DNSBomb mitigation's 1900ms default, increasing
  resource/abuse exposure; the one approved private client, 20 qps/client,
  128 query slots and process limits are essential. Never set this to zero or
  carry it into public service without a separate abuse/capacity review.
- No individual query/reply logging; local Unix control socket `/run/unbound.ctl`.
- One Unbound restart; brief private/local DNS interruption is possible.

Rendered configuration SHA256:
`d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`.
Approval covers this config and the reviewed service-only scripts/drop-in, not
arbitrary future branch changes. Re-render and compare the hash before use.
The [checksum manifest](plans/phase-b-service.sha256) covers the complete config,
drop-in and deployment/rollback/confirmation scripts. Deployment checks it and
compares rendered bytes to the reviewed config before touching active files.
The [active baseline checksums](plans/phase-b-active.sha256), current two-file
include set and absence of existing systemd drop-ins are also checked. Drift
fails closed and requires a new review; this plan is for the inspected VM state.

After explicit approval, on the existing VM at `/home/ubuntu/vynalth-public-dns`:

```sh
.venv/bin/python scripts/prepare-private.py
sha256sum --check plans/phase-b-service.sha256
sudo unbound-checkconf artifacts/private/unbound.conf
# HUMAN APPROVAL REQUIRED before this command:
sudo bash scripts/deploy-private.sh artifacts/private \
  d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7
```

Before editing active files, the script backs up the main config and previous
private drop-in and arms an independent 180-second systemd rollback timer.
Failure also invokes rollback. Rollback restores only service files, reloads
systemd and restarts Unbound; it does not modify host firewall or remote access.
Confirmation and rollback serialize with `flock` to avoid snapshot races.
The initially isolated rollback lab
uses a real 180-second transient systemd timer, disposable mount namespace and
stub service commands. It checks exact file restoration and drop-in removal
without reloading/restarting the production service. A later authorized service
attempt restored the real production config/drop-in state after test failure;
successful private-service acceptance remains incomplete. See VALIDATION.md.

## Revised acceptance and rollback gates (further execution stopped)

Keep the existing SSH session open. Before any future deployment, require clean
Windows/VM worktrees at the exact newly reviewed full commit, bundle SHA256
verification, active baseline verification, byte-equal rendering, config syntax,
unchanged service/drop-in baseline, Tailscale Running/online status, and a fresh
SSH connection proving source `100.85.132.14` and destination `100.95.65.20`.
Do not proceed on drift or unverified connectivity. Verify that no pending
snapshot exists and the retained rollback backup is available. No package or
management-network mutation belongs in this procedure.

The transaction arms its 180s timer before changes; restart is limited to 40s.
Start a Windows stopwatch **before** launching it. After successful readiness,
run the committed read-only controller once, with a 100s total acceptance deadline.
Only a complete PASS receipt and elapsed transaction time below 140s allow
confirmation. Otherwise immediately run the installed service-only rollback;
never cancel its timer for incomplete tests. The >=40s reserve allows recovery.
Transport errors, timeouts, excessive latency, missing AD, incorrect RCODE,
lost SSH, restart, cache-hit or ACL failure, hash drift and an absent/expired
timer are all rollback conditions. No retries, larger ad-hoc timeout or CD bypass.

| Scenario, in order | Per-query limit | Required result |
|---|---:|---|
| First-use valid + bogus DNSSEC, UDP | 15s | NOERROR + AD; SERVFAIL without AD |
| Warm valid + bogus, UDP and TCP | 2s | same codes/flags, >=4 measured cache hits |
| Standard A/AAAA UDP, A TCP, signed/bogus, NXDOMAIN, root DNSKEY TCP | 5s | full standard scenario |
| Bogus checking-disabled, UDP/TCP | 5s | NOERROR, CD, no AD; diagnostic only |
| Unapproved 127.0.0.2 source, UDP/TCP | 2s | REFUSED both transports |

Initial client query count must be exactly one (deployment's localhost readiness
query) at a new process. These are first-use **name** cold cases; the shared
root/TLD cache may warm between names. Fully empty-process cold UDP and TCP
are proven separately by the isolated harness, not by flushing the active service.
Warm cases are distinct declared tests after successful cold cases, not retries.
The controller verifies the real private SSH source, enforcing profile, exact
listeners, config hash, 384MiB/64/1024 limits, finite discard window, absence of
forwarders, unchanged PID/restart count and SSH/firewall fingerprints.

After fresh explicit approval only, in Windows PowerShell from this repository
with Python test dependencies installed, run the following transaction. Set
`$reviewedCommit` to the exact full commit approved by the user and verify both
worktrees manually before using this block; the placeholder must never be used.

```powershell
$reviewedCommit = '<REVIEWED_FULL_COMMIT>'
$configHash = 'd2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7'
$keyPath = 'C:\Users\lynne\Downloads\ssh-key-2026-10-09 (1).key'
$sshArgs = @('-i', $keyPath, '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes',
             '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=4', 'ubuntu@100.95.65.20')
if ((git rev-parse HEAD) -ne $reviewedCommit -or (git status --porcelain)) { throw 'Local review drift' }
$preflight = 'cd /home/ubuntu/vynalth-public-dns && test "$(git rev-parse HEAD)" = ' + $reviewedCommit +
  ' && test -z "$(git status --porcelain)" && .venv/bin/python scripts/prepare-private.py' +
  ' && sha256sum --check plans/phase-b-service.sha256 && sha256sum --check plans/phase-b-active.sha256' +
  ' && sudo -n unbound-checkconf artifacts/private/unbound.conf'
& ssh @sshArgs $preflight
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; do not deploy' }
# Also inspect Tailscale status/source, effective baseline and retained recovery as above.
$elapsed = [Diagnostics.Stopwatch]::StartNew()
try {
  & ssh @sshArgs ('cd /home/ubuntu/vynalth-public-dns && sudo -n bash scripts/deploy-private.sh artifacts/private ' + $configHash)
  if ($LASTEXITCODE -ne 0) { throw 'Deployment failed' }
  & python scripts/private-acceptance.py --ssh-key $keyPath --config-sha256 $configHash `
    --authorized-target --deadline-seconds 100 --out artifacts/private-acceptance.json
  if ($LASTEXITCODE -ne 0 -or $elapsed.Elapsed.TotalSeconds -ge 140) { throw 'Acceptance failed or transaction budget exhausted' }
  & ssh @sshArgs 'cd /home/ubuntu/vynalth-public-dns && sudo -n bash scripts/confirm.sh'
  if ($LASTEXITCODE -ne 0) { throw 'Confirmation failed; inspect rollback state' }
} catch {
  & ssh @sshArgs 'sudo -n bash /var/lib/vynalth-dns/rollback.sh'
  throw
}
```

The controller never deploys, confirms, stops a timer or rolls back. A missing
receipt or killed controller is failure; independent timer recovery remains
armed if SSH is unavailable. Verify restored baseline hashes, original drop-in
state, localhost-only listeners and SSH after rollback. Retain all snapshots.

Manual recovery command (only within an approved active transaction):

```sh
sudo bash /var/lib/vynalth-dns/rollback.sh
```

Do not cancel the timer for incomplete testing. Retain snapshots. The service
plan leaves the existing host firewall unchanged, including current SSH access.
An actual unapproved second tailnet client is unavailable; its live test remains
pending. The loopback negative test and prior isolated ACL tests prove resolver
ACL logic only. This scoped private trial cannot establish public readiness.

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
