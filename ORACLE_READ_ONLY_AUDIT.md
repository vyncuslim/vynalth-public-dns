# Oracle safety audit: prepared, NOT executed

Scope reference: [review comment6098859695](https://github.com/vyncuslim/vynalth-public-dns/pull/1#issuecomment-6098859695),
[Issue2](https://github.com/vyncuslim/vynalth-public-dns/issues/2).
This document does not authorize host access. Current work is documentation/local
verification only: no Oracle SSH/SCP, commands, tests, cleanup or deployment.

## Gate A: separately approve the minimal serial-console audit

Use the existing OCI Serial Console access path on the phone only after explicit
approval of this scope. Do not create a new console connection, change credentials
or networking as an assumed prerequisite. If the existing console cannot be used,
stop and request a separate recovery decision. Do not disclose passwords, keys,
tokens, raw Tailscale state files or private key contents. Paste commands only,
without Termux prompts (`~ $`) or dig output (`;;`). Run one line at a time; record
each command's exit status/time in the approved evidence destination. No `tee`,
redirect-to-file, script upload or directory creation on Oracle is included.

Minimal first pass (the localhost query is explicitly part of the proposed audit,
not Android acceptance; it can update in-memory cache/counters and ordinary logs):

```sh
date -u
hostname
uname -m
id -un
cat /proc/sys/kernel/random/boot_id
systemctl is-active unbound tailscaled
sudo ss -lntup '( sport = :53 )'
sudo unbound-checkconf
dig @127.0.0.1 vyncuslim.com A +time=5 +tries=1
ip -br addr show tailscale0
```

Interpret each service result individually; `is-active` can exit nonzero when
either is inactive. Syntax PASS is not evidence that the running daemon loaded
those bytes. If only127.0.0.1/[::1] binds53, the private listener is absent at the
sample time. If100.95.65.20 binds53, identify its PID/service before attributing
it to production. Wildcard/public listeners, failing syntax/local query or an
unexpected process are STOP findings; do not repair or restart. Even a healthy
private listener does not prove the OPPO Tailscale/firewall path works.

### Focused retained-laboratory inventory, still read-only

The known paths/units are in [LIVE_VM_IMPACT.md](LIVE_VM_IMPACT.md). Do not remove
anything, kill a process, stop a unit, cancel a timer or launch a fixture. The
historical numeric PIDs may be reused; use current PID, executable, start time,
cgroup and unit together rather than treating an old PID as a cleanup target.

```sh
systemctl list-units --all --no-pager 'vynalth-*'
systemctl list-unit-files --no-pager 'vynalth-*'
systemctl list-timers --all --no-pager 'vynalth-*'
systemctl show vynalth-rollback.timer vynalth-rollback.service -p LoadState -p ActiveState -p SubState -p MainPID -p NextElapseUSecMonotonic
systemctl show vynalth-dev-fixture-82fcb9.scope vynalth-dev-recursion-82fcb9.scope -p LoadState -p ActiveState -p SubState -p ControlGroup
systemctl show vynalth-candidate-timer-2634.timer vynalth-candidate-timer-2634.service vynalth-rollback-test-2658.timer vynalth-rollback-test-2658.service vynalth-rollback-test-6463.timer vynalth-rollback-test-6463.service -p LoadState -p ActiveState -p SubState -p MainPID -p ControlGroup
ps -eo pid,ppid,lstart,comm,cgroup --sort=pid
sudo find /var/lib/unbound -maxdepth 1 -name 'vynalth-*' -printf '%y %u:%g %m %s %p\n'
sudo find /tmp -maxdepth 1 -name 'vynalth-*82fcb9*' -printf '%y %u:%g %m %s %p\n'
sudo ls -ld /var/lib/vynalth-dns /var/lib/vynalth-dns/pending /var/lib/vynalth-dns/rolled-back-1791611257
```

Missing paths/units are evidence, not a reason to recreate them. The first removed
checkout cannot be reconstructed as original evidence. For an unexpected Unbound
PID, after identifying it from `ss`/`ps`, substitute its decimal PID below:

```sh
sudo readlink /proc/<CURRENT_PID>/exe
sudo cat /proc/<CURRENT_PID>/cgroup
sudo cat /proc/<CURRENT_PID>/attr/current
```

Ownership and top-level directory size do not establish total disk usage. If
needed, separately approve bounded recursive metadata/size inspection of the
exact retained checkout `/var/lib/unbound/vynalth-dev.PMaPSc`. Do not source its
scripts or inspect arbitrary secrets. Pending transaction or active protection
blocks the next trial; leave it untouched and escalate status review.

## Extended baseline/recovery audit: separately include in Gate A scope

No command below installs a package, changes policy or starts tests. Collect
timestamps and failures; unavailable commands mean UNKNOWN, not PASS. `sudo` may
create ordinary authentication/audit records; read-only is not zero side effect.

```sh
systemctl show unbound -p MainPID -p InvocationID -p ActiveState -p SubState -p NRestarts -p DropInPaths -p FragmentPath -p MemoryMax -p TasksMax -p LimitNOFILE
sudo aa-status
sudo sha256sum /etc/unbound/unbound.conf /usr/share/dns/root.hints /var/lib/unbound/root.key
sudo find /etc/unbound/unbound.conf.d /etc/systemd/system/unbound.service.d -maxdepth 1 -type f -exec sha256sum {} \;
sudo nft --stateless list ruleset
sudo ufw status verbose
sudo /usr/sbin/sshd -T
tailscale ip -4
systemctl is-active ssh tailscaled
sudo ss -tnp '( sport = :22 )'
systemctl is-active apt-daily.service apt-daily-upgrade.service
systemctl list-timers --all --no-pager apt-daily.timer apt-daily-upgrade.timer
sudo lslocks --output COMMAND,PID,PATH
test ! -e /var/run/reboot-required; printf 'reboot-clear exit=%s\n' "$?"
timedatectl show -p NTPSynchronized
df -h / /var/lib/unbound
```

Missing root-anchor/drop-in paths must be assessed against the actual configured
paths, not created. Capture firewall/SSH effective output in the approved local
evidence destination, hash there using the existing readiness script's exact
normalization, and compare full policy, not counters or an old digest alone.
Full firewall output can contain sensitive topology; redact before public upload
and retain original digest under the approved private evidence procedure.
This host audit does not inspect OCI security lists/NSGs or change them.

Serial access does not verify Windows Tailscale SSH recovery. That requires a
separately approved read-only Windows connection with the existing host-key pin
and local private key, retaining the session. Verify hostname/user, `$SSH_CONNECTION`
source100.85.132.14 and server100.95.65.20. Keep the private key on Windows. No
reauthentication, SSH policy change or extra phone SSH permission is authorized.

Bounded service journals (no individual DNS query history) and process executable
details may be needed for an unexpected unit. Approve a specific UTC window and
units before collecting them; absence of journal evidence is not proof of no
impact. Assess CPU/RAM/disk and active dependencies before any cleanup proposal.

## Audit handoff and stop conditions

Return UTC sample time/boot ID, each result including failures, actual listener
owners, enforcing label, file/policy hashes, maintenance/reboot/clock state,
retained artifact/unit/process inventory and separately verified recovery path.
Current status is **NOT AUDITED**. No fresh baseline is approved by these commands.
Reboot required, maintenance activity/schedule uncertainty, drift, public binding,
unknown residue impact, failed recovery or pending protection blocks deployment.
Do not disable upgrades, relax checks, cancel timers or automatically retry.
Next gates are in [PHASE_B_APPROVAL_CHECKLIST.md](PHASE_B_APPROVAL_CHECKLIST.md).
