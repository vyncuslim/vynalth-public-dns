# Fresh Oracle baseline: separate permissions, no execution yet

Native ARM64/AppArmor/cgroup/180s CI passed; no new physical ARM lab is needed.
See GATE_D_REVIEW.md. This is preparation only: Oracle was not accessed. The old
cbb29c44 baseline is historical/review-only, never silently reused or refreshed.

| Permission | Precisely allowed effects | Not included |
|---|---|---|
| R inspection | Existing pinned Windows private SSH and listed remote reads; stdout/local recording | Remote writes, staging, collector, probes/tests or deployment |
| S source staging | Exact reviewed commit in existing /home/ubuntu/vynalth-public-dns after clean-state review and explicit git-operation approval | Active service/config, packages/venv, collector, cleanup |
| C evidence capture | Reviewed code, two samples60s apart, exactly one new file in an existing approved artifacts directory, one local retrieval/hash check | Baseline approval/overwrite, DNS probes/cache/anchor changes, restart/timers/network |
| D private trial | Future exact commit/config/service/fresh baseline protected Windows transaction | Granted by none of R/S/C; Android and DNS settings separate |

## Next request: approve R only

One retained Windows OpenSSH session to ubuntu@100.95.65.20 using the existing
local key filename and strict existing host-key pin. No key/password/token
contents requested. Precisely these stdout-only commands, once, no script upload:

```sh
date -u
hostname
id -un
uname -m
uname -r
printf '%s\n' "$SSH_CONNECTION"
cat /proc/sys/kernel/random/boot_id
GIT_OPTIONAL_LOCKS=0 git -C /home/ubuntu/vynalth-public-dns rev-parse HEAD
GIT_OPTIONAL_LOCKS=0 git -C /home/ubuntu/vynalth-public-dns status --porcelain
readlink -f /home/ubuntu/vynalth-public-dns/artifacts
stat -c '%F %U:%G %a %n' /home/ubuntu/vynalth-public-dns/artifacts
test -d /home/ubuntu/vynalth-public-dns/artifacts; printf 'artifacts-directory-exists=%s\n' "$?"
/usr/bin/python3 --version
systemctl show unbound -p MainPID -p InvocationID -p ExecMainStartTimestampMonotonic -p ActiveState -p SubState -p NRestarts -p DropInPaths
sudo -n ss -lntup '( sport = :53 )'
sudo -n sha256sum /etc/unbound/unbound.conf
sudo -n find /etc/unbound/unbound.conf.d -maxdepth 1 -name '*.conf' -type f -exec sha256sum {} \;
tailscale ip -4
systemctl is-active ssh tailscaled
systemctl show vynalth-rollback.timer vynalth-rollback.service -p LoadState -p ActiveState -p SubState
sudo -n test ! -e /var/lib/vynalth-dns/rollback; printf 'pending-snapshot-absent=%s\n' "$?"
```

Test exit0 means condition true; errors/inaccessible fields are not PASS. Verify
source100.85.132.14, destination100.95.65.20 and expected host/user. Wrong host,
dirty checkout, unexpected listeners or active protection: STOP before writes.
GIT_OPTIONAL_LOCKS=0 avoids optional index refresh writes. Routine SSH/sudo audit
records may occur; read-only is not zero incidental logging. Retain existing
session/console recovery; no new console connection or management test disruption.

R approval text: "Approve only scope R of FRESH_BASELINE_APPROVAL.md at the full
reviewed PR commit: one existing Windows private SSH session and listed stdout
reads/local recording; no remote files, staging, collector, DNS probe/test, timer,
cleanup, restart, network change or deployment."

## S: separately approve staging after actual R results

Review actual VM HEAD/clean state and permissions. Approve exact fetch/checkout
operations to a named path/commit; do not reset, clean, overwrite dirty work or
assume a branch. Verify resulting HEAD and21-file service/review/Gate C checksums.
Do not run an old checkout's collector. Collector uses Python stdlib and existing
OS commands; no package/OS/venv setup is required for C. Missing prerequisites
require a new itemized scope, not automatic bootstrap. S is not C or D.

## C: exact minimal two-sample capture after S review

Approve the literal proposed filename below (or a newly reviewed unique name) and one local
retrieval. Parent directory must already exist, resolve within the approved checkout, and have reviewed ownership/mode; unexpected symlinks STOP. Exclusive creation rejects an
existing file/symlink or absent parent before any sample, with no automatic retry.
One new evidence file is updated through this run; failures retain partial data.
No other remote files/directories are created.60s plus bounded command time is
preparation, outside the future<140s trial, never resetting its T0.

```sh
cd /home/ubuntu/vynalth-public-dns
test "$(GIT_OPTIONAL_LOCKS=0 git rev-parse HEAD)" = '<APPROVED_FULL_COMMIT>'
test -z "$(GIT_OPTIONAL_LOCKS=0 git status --porcelain)"
sha256sum --check plans/phase-b-service.sha256
sha256sum --check plans/identity-review.sha256
sha256sum --check plans/gate-c-review.sha256
systemctl show vynalth-rollback.timer vynalth-rollback.service -p LoadState -p ActiveState -p SubState
sudo -n /usr/bin/python3 scripts/post-maintenance-readiness.py --capture --interval 60 --ssh-connection "$SSH_CONNECTION" --out artifacts/fresh-baseline-gate-d-20261011-01.json
systemctl show vynalth-rollback.timer vynalth-rollback.service -p LoadState -p ActiveState -p SubState
sudo -n sha256sum artifacts/fresh-baseline-gate-d-20261011-01.json
```

Execute each once and STOP on a nonzero result, not an unconditional command
chain. Verify source/commit/hashes again immediately before C. Capture success
means capture_complete=true and deployment_ready=false, never human approval.
Do not overwrite original baseline/capture or retry a partial failed capture.

## Evidence PASS / mandatory STOP

PASS means two complete samples>=60s apart with equal static fingerprints and no
operational failure: boot/kernel/unit PID/invocation/start, includes/drop-ins,
packages, enforcing profile, original loopback listeners, hints, anchor/status,
same-method policies, Tailscale/source, no maintenance/locks/active protection,
known schedule>15min, NTP=yes, reboot=no and reviewed RAM/disk/recovery evidence.

Anchor metadata is mutable and outside the static fingerprint: compare trusted
keys/VALID status/refresh manually. Hash/equal samples alone do not prove DNSSEC
health. Owner firewall589768... pipeline remains unknown; do not compare unlike
digests as incidents. Full host/OCI/private policy/path still needs separate
review. Collector does not resolve the original production bogus15s timeout.

STOP for missing fields, inaccessible commands, source/hash/drift, unexpected
boot/PID/config/policy needing review, invalid/uncertain anchor, non-enforcing
profile, clock/reboot/maintenance/schedule, pending rollback or unresolved active
residue/recovery. Never substitute PID/hash, waive checks, disable updates,
flush caches, rewrite evidence or broaden permission to obtain PASS.

Only after explicit human review, make a new LOCAL review-only baseline from
the first accepted fingerprint, raw capture SHA/UTC and review_only=true plus
human_approval_required=true. Preserve both full samples. Recompute service/
baseline/review hashes and commit for another exact approval. New baseline/source
goes back to Oracle only with another S approval. D still requires exact then-
current commit/config/bundle/fresh baseline, unchanged preflight,180s protection
and strictly<140s complete Windows acceptance/confirmation. No D approval here.

The separate pre/post service-property reads in C are recorded on local stdout;
both timer and recovery service must be inactive (or not-found/inactive). Active,
activating, failed or unknown states STOP. Collector JSON alone does not capture
the recovery service state, so do not infer this PASS from its timer field alone.
