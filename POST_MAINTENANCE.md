# Post-maintenance review: deployment remains blocked

This review does **not** deploy, restart production services or grant permission.
The second trial stopped at preflight. The new read-only baseline is stable, but
the VM has a pending kernel reboot and independent console recovery is unverified.
Recommend a separately approved maintenance reboot first, followed by a new
baseline review and a new exact private-service authorization. Do not substitute
a new PID into the previously approved transaction or reuse its approval.

## Verified state on 2026-10-10

Receipts are in [plans/post-maintenance/](plans/post-maintenance/).
Two capture samples at 07:17/07:18 UTC matched exactly over 60 seconds. A separate
two-sample pinned comparison matched the frozen fingerprint exactly; its only
failures were the pending-reboot gate in each sample (exit1, not authorization).

| Item | Evidence / outcome |
|---|---|
| Host / current kernel | vynalthai-dns, Ubuntu 24.04.5 aarch64; 6.17.0-1020-oracle |
| Unbound | active/running, PID34123, invocation 2cad7a7d4117419398f15349dcf710f5; started 06:56:04 UTC; NRestarts0 |
| DNS listeners | original 127.0.0.1/[::1] UDP/TCP53 only; no Tailscale or public Unbound listener |
| AppArmor | unbound (enforce); profile unchanged |
| Limits / drop-ins | MemoryMax=infinity, TasksMax6964, NOFILE524288; no drop-ins |
| Recursion / anchors | no configured forwarders; packaged root hints and original RFC5011 anchor include; syntax valid; public anchor metadata captured |
| SSH recovery via Tailscale | fresh Windows 100.85.132.14 -> VM100.95.65.20 SSH succeeded; retained session remained open |
| Boot activation | tailscaled and unbound enabled; ssh.socket enabled/active (ssh.service disabled is socket activation, not absence of SSH) |
| Management policies | nftables/sshd fingerprints equal to previous receipts; no mutations |
| Package maintenance | apt-daily and apt-daily-upgrade inactive/dead, no upgrade/dpkg/needrestart process, all four package locks unoccupied |
| Shutdown helper | existing unattended-upgrade-shutdown --wait-for-signal is a waiting helper, not an active installation |
| Next sampled apt schedules | 12:39:38 UTC Oct10 / 06:53:56 UTC Oct11; time-bound observations, not a future window guarantee |
| Recovery transaction | no pending snapshot; production rollback timer not-found/inactive; previous rolled-back-1791611257 backup retained |
| Reboot | required: new Oracle kernel and linux-base; no scheduled shutdown observed |

Active main config SHA256:
`8808b474175ff8eeebecbf407f9091fd73f65c4a43a6ee212e8ae2d9f80778f8`.
Stateless nftables SHA256:
`ab2fe6d9f0cd70d6bdd543f40e84589f6a72df3c0db5511d043e5ab7701f10e9`.
Effective sshd SHA256:
`6a343a5d48e53f841c95fd70c02411548d4c4e5097892d048a16b05b554c1344`.

Proposed config remains byte-identical to the reviewed configuration, SHA256:
`d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`.
The original 13-file service manifest and active-config manifest still pass.
No production deployment script or manifest was changed in this review.

## Fresh reproducible baseline and preflight

[The frozen baseline](plans/post-maintenance-baseline.json) is **pre-reboot,
review-only**. SHA256:
`b134e1cc99c56e065f0657b205561c08bc55f24fabd7efcbe9e0f48647c86a17`.
It pins kernel/boot ID, PID/invocation/start time, package versions, binaries,
unit/config/AppArmor/root-hints hashes, limits, listeners, boot activation,
Tailscale identity and management fingerprints. It does not pin RFC5011 refresh
timestamps or DNS counters; these are diagnostic observations, not immutable
configuration. Existing configuration/management checks remain exact.

From an authenticated Windows SSH connection, run on the VM repository:

```sh
cd /home/ubuntu/vynalth-public-dns
sudo -n .venv/bin/python scripts/post-maintenance-readiness.py \
  --baseline plans/post-maintenance-baseline.json \
  --ssh-connection "$SSH_CONNECTION" --interval 60 \
  --out artifacts/post-maintenance-pinned-check.json
```

This performs only reads and writes its evidence JSON. Current expected exit is
**1**, with a pending-reboot failure; it must not authorize deployment. Errors,
hash drift, maintenance activity, occupied locks, unknown schedules or the next
apt timer within 15 minutes fail closed. Require two equal samples at least 60s
apart. Capture mode is explicitly review-only, always non-authorizing:

```sh
sudo -n .venv/bin/python scripts/post-maintenance-readiness.py --capture \
  --ssh-connection "$SSH_CONNECTION" --interval 60 \
  --out artifacts/post-maintenance-new-capture.json
```

After a reboot/package/service change, compare the full new evidence, commit a
new baseline as a separately reviewed artifact and obtain fresh authorization.
Do not edit the baseline automatically, ignore exit1 or strip the drift fields.
For a proposed window, inspect again immediately before the transaction; the
current quiet state does not prevent later automatic maintenance. Leave update
policy and timers enabled. Any later baseline drift aborts the trial.

## Separate maintenance proposal: no reboot authorized

The installed `7.0.0-1013-oracle` image/initramfs and /boot links differ from the
running kernel. GRUB_DEFAULT=0; both new and prior kernels remain available.
The reboot-required flag is evidence that maintenance is incomplete; kernel
updates generally need a reboot to finish loading the new kernel.
[Ubuntu automatic updates documentation](https://ubuntu.com/server/docs/how-to/software/automatic-updates/).
This remains Ubuntu24.04; do not perform a release upgrade. No explicit
Automatic-Reboot setting appeared in apt-config; absence is not a guarantee
against another reboot mechanism. No policy change was made.

Before seeking **separate reboot approval**:

1. Independently verify an existing OCI console/recovery path and authorization
   to use it, including pricing if anything needs creating. Private SSH alone
   cannot recover a failed boot. Public SSH was previously unverified; unchanged
   ssh.socket binding does not establish OCI ingress reachability. Do not open
   SSH or alter security lists/NSGs. Console recovery is still unverified.
2. Recheck quiet maintenance/locks/timers, NTP, disk, boot files, enabled
   tailscaled/unbound/ssh.socket and known-host private SSH. Save evidence and
   copies of service settings to existing local storage; no paid backup service.
3. Review an exact one-reboot command and downtime/recovery window with the
   human. A reboot intentionally ends SSH sessions and is a different approval
   from a protected DNS trial. Do not reboot under a service-only authorization.
4. After that approval only, execute one reboot with console recovery available.
   Reconnect using the unchanged Windows SSH key/client and strict known-host
   checking. Verify kernel/boot ID, Tailscale/private SSH, AppArmor, original
   DNS listeners/configuration, management hashes, maintenance state and cleared
   reboot flag. Do not deploy DNS during this maintenance transaction.
5. If boot/access fails, use the independently verified console and retained old
   kernel under the agreed recovery plan. Do not improvise firewall relaxation,
   package removal or paid replacement resources. After recovery, stop for review.
6. Commit/review a fresh post-boot fingerprint, rerun preflight/isolated checks
   appropriate to any change, and present a new full commit and baseline hash.

## Transient timer warning: evidence and limits

Old journal: production rollback timer armed 05:47:29, explicitly stopped
05:49:15, before its 05:50:29 deadline. The first missing-fragment warning occurs
**after that stop**, then repeats during later inspections. Current unit is
not-found/inactive with no fragment or pending transaction. The evidence does
not show an armed timer failing to fire.

Transient units are runtime-created and can be unloaded/garbage-collected.
[systemd-run documentation](https://manpages.ubuntu.com/manpages/noble/man1/systemd-run.1.html).
The timeline is consistent with a removed transient fragment and a stale unit
reference/reload after cancellation. **The precise cause of the historical
warning is unproven**: isolated cancellation/same-name rearming worked, but did
not reproduce the exact warning. No production reset-failed, daemon reload,
timer replacement or cleanup was used to conceal it.

Independent 180s test used the existing mount-namespace lab, a distinct transient
unit, disposable config/systemd mounts and strict stub service commands. Journal
armed at07:12:11 and fired at07:15:11 UTC. Outer monotonic runtime181.386s; shell
integer wall-clock observation182s includes setup/polling/rounding. Exact original
config/prior limits were restored, unrelated drop-in retained, initially absent
private.conf removed in the second isolated case. Production PID/invocation,
config and management fingerprints remained unchanged. Test units/temp data were
cleaned. This proves the isolated timer/file-restore mechanics, **not** a future
production restart or post-reboot access.

Reproduce only on the authorized VM, from repository root (lab units only):

```sh
sudo -n .venv/bin/python plans/post-maintenance/collect-rollback-evidence.py
sudo -n .venv/bin/python plans/post-maintenance/collect-timer-guard-evidence.py
```

Systemd monotonic timers allow scheduling accuracy; do not turn sampled elapsed
182s into a longer configured rollback timeout.
[systemd.timer documentation](https://manpages.ubuntu.com/manpages/noble/man5/systemd.timer.5.html).

## Separately reviewable timer gate proposal: not applied

[Read-only checker](proposals/check-rollback-timer.py) requires the real timer
active/waiting, a present transient fragment, AccuracySec1s, approximately180s
monotonic interval and at least170s remaining before active config writes.
Isolated actual-systemd tests: fresh180s PASS; incorrectly armed60s FAIL;
stopped/missing timer FAIL. Exact historical warning is still not reproduced.

[One-line patch](proposals/deploy-private-timer-gate.patch) proposes invoking it
after installing the ERR trap and before config writes. It passes dry-run patch
validation but is **not integrated**. To adopt it, first integrate it in a new
review commit, update the service bundle manifest to cover both changed script
and checker, validate with the isolated rollback lab, then obtain approval for
that exact new commit. Never patch the approved deployment during execution.
This review's manifest covers diagnostic/proposal/evidence files separately.
Verify it from repository root with
`sha256sum --check plans/post-maintenance-review.sha256` on the VM. Do not change
the original service manifest to make an unreviewed patch pass.

## Exact next private-service approval terms (request blocked for now)

Do not request executable deployment authorization until the maintenance/recovery
gates above are satisfied and a post-boot baseline and any adopted timer changes
have been committed and reviewed. This pre-reboot documentation commit cannot
stand in for that future immutable commit. The final request must name the
**actual full GitHub/Windows/VM commit**, **actual post-boot baseline SHA256**,
service-bundle manifest and the unchanged config hash `d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`.
No fabricated future commit/PID/hash or wildcard authorization is acceptable.

Approval wording to complete with those verified identities:

> Approve one private Unbound trial at the specified full commit, baseline and
> configuration SHA256 only. Install the reviewed private configuration and
> systemd limits, restart Unbound once, and arm an independent180s rollback before
> active writes. Retain the existing SSH session. No firewall/SSH/Tailscale/OCI/
> Spectrum/DNS-record/package/reboot changes. Do not run install.sh or Terraform.
> Require all preflight and one-shot acceptance gates below. Only a complete PASS
> receipt and total transaction time strictly below140s permit confirm.sh. Any
> failure, timeout, missing receipt, drift, maintenance, SSH loss or exhausted
> budget requires immediate service-only rollback; if disconnected, leave the
> independent timer armed. No retry, bypass, forced confirmation or public DNS.

Preflight: clean/equal GitHub/Windows/VM HEAD; all review/service/active manifests;
byte-equal rendering and syntax; exact reviewed service/boot baseline at two
samples; no reboot flag, maintenance processes/locks or close/unknown apt
schedule; AppArmor enforcing; approved source/destination and both Tailscale
peers online; retained SSH and fresh login; unchanged management policies;
original listeners/limits/drop-ins; no pending transaction; retained recovery.
Require working rollback timer immediately after arming and before writes.

Acceptance remains [PHASE_B.md](PHASE_B.md)'s existing one-shot Windows procedure:
first-use valid/bogus UDP15s, distinct warm UDP/TCP2s and >=4 measured cache hits;
standard A/AAAA/UDP/TCP/DNSSEC/NXDOMAIN/root DNSKEY and CD diagnostic5s;
unapproved127.0.0.2 UDP/TCP REFUSED2s. Verify no forwarders, approved private
listeners, config/limits/identity, stable deployed PID and management hashes.
Acceptance total100s; restart cap40s; transaction <140s for confirm, rollback180s.
Record exact query/transport/elapsed/RCODE/AD/CD/error/outcome, never silent retries.
An actual second unapproved tailnet client remains unavailable and unverified;
loopback rejection does not prove the whole tailnet path. Public readiness stays
blocked, and 15000ms must not be promoted to public production.

RM0 remains the budget target, not confirmed billing eligibility. No cloud/paid
resources were created or changed; invoice/free allocation/OCI ingress/recovery
and Spectrum contractual coverage remain unverified.
