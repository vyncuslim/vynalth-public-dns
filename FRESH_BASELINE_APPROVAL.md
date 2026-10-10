# Fresh two-sample baseline: future separately approved collection only

Owner Gate A findings are reconciled in GATE_A_RECONCILIATION.md. Existing pinned
baseline is historical/review-only; no PID/hash substitution or automatic approval.
No command here has been executed on Oracle by Codex. Gate C and unresolved
production DNSSEC timeout are not cleared by collecting a baseline.

## Exact proposed authorization scope

Approve a Windows authenticated read-only SSH collection using its existing key
and strict host pin, retaining the existing session and console recovery. First
review/stage the exact full commit and complete source/config/manifest bundle to
`/home/ubuntu/vynalth-public-dns` under **separate staging approval**. Staging and
new evidence-file writes/transfers are writes and must be explicitly authorized;
this request is not implicit permission for them. Never run install/deploy/confirm,
start timers/tests, change active services, delete residue or modify networking.

After those prerequisites are approved and available, the capture-only command
reads host state twice60s apart and writes one **new unique evidence file only**:

```sh
cd /home/ubuntu/vynalth-public-dns
git rev-parse HEAD
git status --porcelain
sha256sum --check plans/phase-b-service.sha256
sudo -n .venv/bin/python scripts/post-maintenance-readiness.py --capture --interval 60 --ssh-connection "$SSH_CONNECTION" --out artifacts/fresh-baseline-<APPROVED_UNIQUE_ID>.json
sha256sum artifacts/fresh-baseline-<APPROVED_UNIQUE_ID>.json
```

Approve the exact output path, staged commit, key filename-only use, read commands
and one local retrieval/hash verification. No private key contents are requested.
Do not overwrite the original capture or baseline. Capture success has
`capture_complete=true` and **deployment_ready=false**; it is never authorization.
All read failures are retained; no automatic repeat or silent baseline refresh.

## Human review and pinning, on the local review checkout

Check both UTC timestamps and actual separation>=60s, equality of fingerprints,
boot/kernel/PID/invocation/start time, configs/includes/drop-ins/package versions,
AppArmor enforcing label, root hints and captured root-anchor SHA/status metadata,
effective SSH/firewall normalization, Tailscale address and source connection.
Compare full root-anchor/status records manually: mutable anchor metadata is not
part of the static fingerprint, so equal fingerprints alone do not prove anchor
health. Verify trusted keys/status and reject uncertain root validation.

Review maintenance services/processes/package locks, known timer schedule>15min,
NTP, reboot flag, disk/RAM, SSH/Tailscale boot activation, pending snapshot and
active rollback unit/service. Keep owner firewall589768... labeled method-unknown;
do not treat it as interchangeable with the script's normalized digest. OCI
ingress/private53 reachability and worst-case management recovery are separate.

STOP for missing samples/fields, mismatched source/hash, new PID/boot/file/policy
drift, non-enforcing profile, invalid anchor, clock/reboot/maintenance/schedule
uncertainty, unknown active residue/transaction or failed recovery. Do not disable
updates, clear cache, rewrite the sample, broaden ACLs or substitute old values.

Only after explicit review approval, create a **new local review-only baseline**
from the accepted first fingerprint, with source capture SHA256, UTC time and
`review_only=true`, `human_approval_required=true`. Preserve the full raw capture.
Recalculate the baseline, service and review manifests; commit/push for another
exact review. No baseline material is written back to Oracle until separately
approved staging. Changed bundles invalidate older approvals. Final trial needs
a fresh exact commit/config/bundle/baseline authorization and unchanged preflight;
the collector never starts or confirms the trial.
