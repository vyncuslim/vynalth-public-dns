# Existing Oracle VM: private service approval plan

Status on 2026-10-10: the approved `036575d` service bundle was attempted once
at 13:47 MYT and **rolled back after a DNSSEC test timeout**. Private DNS is not
active. See VALIDATION.md for the latest result. No confirmation or automatic
retry occurred; another attempt requires renewed explicit authorization.
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
- No individual query/reply logging; local Unix control socket `/run/unbound.ctl`.
- One Unbound restart; brief private/local DNS interruption is possible.

Rendered configuration SHA256:
`204aca36bc268e83e9878426605692b8c7f04b142fa0b0f8956c6d7e3486d2e7`.
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
  204aca36bc268e83e9878426605692b8c7f04b142fa0b0f8956c6d7e3486d2e7
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

Within 180 seconds, verify fresh Windows SSH, low-volume UDP/TCP DNSSEC and cache
checks to `100.95.65.20`. Confirm only after success:

```sh
sudo bash scripts/confirm.sh
# Immediate recovery instead of confirmation:
sudo bash /var/lib/vynalth-dns/rollback.sh
```

Do not cancel the timer for incomplete testing. Retain snapshots. The service
plan leaves the existing host firewall unchanged, including current SSH access.
An actual unapproved second tailnet client is unavailable; its live test remains
pending. Isolated tests establish ACL behavior but cannot replace that evidence.

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
