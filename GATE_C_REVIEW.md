# Gate C independent validation package — no Oracle execution

Completed on the authorized standard **ubuntu-24.04-arm hosted runner**.
No additional physical ARM lab is requested; commands below are reproduction references.
No OCI provisioning, cloud charges, package/OS updates or production access are
performed by this package. Native ubuntu-24.04-arm hosted CI is now verified PASS for aarch64/Ubuntu24.04,
Unbound1.19.2-1ubuntu3.10, actual unbound(enforce), isolated cgroup/service
restoration and real180s timers. See ARM_CI_RESULTS.md. Earlier WSL results were
x86-only and are retained as history, not substituted for these native receipts.

## Reproducible ARM/enforcement gate

Require reviewed full commit, matching config/service/Gate C manifests, clean
checkout, existing test Python dependencies and installed Unbound/root data,
iproute2/systemd/AppArmor/Shellcheck. Inspect package version, kernel, architecture
and profile state first. Do not install software or create a lab as implicit
authorization. The preflight refuses the known production hostname and fails on
x86/missing enforcement; actual runtime tests separately verify the loaded label.

On that approved independent lab only:

```sh
python scripts/gate-c-preflight.py --authorized-independent-lab --out artifacts/gate-c-capabilities.json
sha256sum --check plans/phase-b-service.sha256
sha256sum --check plans/gate-c-review.sha256
python -m unittest discover -s tests -p 'test_*.py' -v
sudo /path/to/test-python tests/two_client_runtime.py --require-apparmor --out artifacts/gate-c-two-client.json
sudo /path/to/test-python tests/negative_runtime.py --require-apparmor --out artifacts/gate-c-negative.json
sudo /path/to/test-python tests/local_runtime.py --require-apparmor
sudo /path/to/test-python tests/gate_c_deploy_lab.py --authorized-independent-lab
sudo bash tests/local_rollback_files.sh
sudo /usr/bin/python3 tests/gate_c_rollback_lab.py --authorized-independent-lab --out artifacts/gate-c-real-timer.json
shellcheck scripts/*.sh tests/*.sh
```

Record actual installed package/version and all failures/skips. Capability PASS
is only a prerequisite: it is not a hardware/profile/runtime acceptance result
or permission to access Oracle. The lab must contain no production checkout,
active protection or recovery data. New files stay in lab temp directories and
its artifacts; real timer units have unique vynalth-local-gate-c names. Scoped
cleanup covers only those created lab units/files, not Oracle residue/backups.

Systemd MemoryMax384M/TasksMax64/LimitNOFILE1024 has been verified with the actual
isolated Unbound service/cgroup, reading unit/cgroup/proc limits and enforcing
label; actual original limits were restored. See ARM_CI_RESULTS.md. Earlier
rlimit/shim-only evidence was insufficient on its own. Tailscale SSH
recovery/continuity and complete networking remain separate live/private gates.
No actual Tailscale administration or Android DNS settings are part of this lab.

## Safety changes now implemented

- Deploy acquires the shared transaction lock nonblocking, refuses existing
  protection/pending snapshot, and verifies the pinned baseline under that lock.
  This prevents concurrent deployment writes from racing confirmation/recovery.
- Timer readiness is verified before service writes; the original mapped global
  deadline/boot is rechecked after arming. No fresh140s window is introduced.
- ERR/TERM/INT recovery releases the deploy lock before invoking service-only
  rollback, avoiding a self-deadlock. SIGKILL still relies on independent timer.
- Snapshot checksums detect missing/corrupt/extra restore files before restoration;
  confirmation verifies the snapshot. Failed restart leaves pending recovery
  evidence, never claims success. Historical backups remain excluded from cleanup.
- Confirmation uses an atomic `mv -T` with PID-suffixed destination, avoiding
  nesting/merging into an existing same-second archive. Protection stays armed.
- Review-only baseline capture now reports `capture_complete` independently from
  `deployment_ready=false`; a successful capture can exit0 without authorizing
  deployment. Drift/failure still fails closed.

New snapshot format is not retroactively applied to historical Oracle backups.
Missing integrity information blocks automatic recovery with this new script;
review historical recovery procedure separately, never upgrade/delete its files.
Restore consists of normal file copies and service operations, not a power-loss
durability guarantee. Crash/fsync/storage failure and failed real-daemon recovery
remain risks to review; no new deployment method bypasses existing protections.

## Local evidence and coverage limits

Real independent180s systemd tests use actual rollback.sh and private mounts:
controller SIGKILL simulation still restored files; completion184.181692s.
Atomic-confirmation-state simulation caused no-op after183.456660s. Readiness
records show configured180s interval and AccuracySec1s. Completion includes
dispatch/namespace/recovery time, not a guarantee of exactly180s callback finish.
Both tests use strict service shims; neither proves real Unbound restart/SSH or
ARM/AppArmor. The confirmation simulation is not a full production PASS receipt.

Actual shell guard/recovery scenarios in disposable private mounts cover success,
concurrent lock, active timer, existing pending snapshot, config hash mismatch,
bad timer, readiness-query failure, restart/recovery failure and TERM interruption.
OS baseline, DNS readiness and timer APIs there are explicit shims. Unit tests
cover partial/missing/failed receipts, PID/boot/hash drift, global deadline and
ambiguous confirmation/no retry. File tests cover4 restore variants, no-snapshot
no-op, missing checksum, corruption, unrecorded limits and failed restart.

Not fully exercised: real SSH disconnect/network latency with real service,
controller SIGKILL holding inherited lock descriptors, missing original recovery
files during a real outage, actual AppArmor denial, ARM cgroup limits, delayed/
failed real service recovery and power loss. Do not label them PASS based on mocks.
See VALIDATION.md and plans/gate-c/ for actual receipts and precise statuses.

Windows protected transaction remains strictly<140s including every command,
network/verification/confirmation operation. No retries on ambiguous confirmation.
Android DNS-only gate remains separately approved, after Windows confirmation,
strictly<45s. Both /32 ACLs/private listeners/PTR/DNSSEC/default refuse remain.
No system-wide override, public listener or paid infrastructure is authorized.

## Authorized standard public ARM hosted CI

See ARM_HOSTED_CI.md. Owner now authorizes the independent ubuntu-24.04-arm
standard public-repository job; no separate physical machine is required. Existing
tests remain. Architecture/profile/isolated service/cgroup/timer/Unbound results are now PASS
with native hosted receipts. Earlier billing-lock observations were historical,
not code/runtime failures; why scheduling resumed remains unknown. No paid/OCI/self-hosted fallback or billing/VPN change.
Production recovery and fresh baseline/Windows/Android approvals remain separate.

## Actual hosted native ARM evidence supersedes preparation status

See ARM_CI_RESULTS.md and plans/arm-ci/38080431432/ plus38080434109/. Both
81c8cf8 native ARM jobs completed SUCCESS; downloaded evidence hashes verified.
aarch64/Ubuntu24.04/Unbound1.19.2-1ubuntu3.10 and actual unbound(enforce),
DNSSEC/dual ACL/PTR, actual isolated service/cgroup restoration and real180s
unique timers are now PASS for that code/scope, not merely prepared or mocked.
Production recovery/live devices remain PENDING. Earlier billing-block statements
are historical: scheduling resumed without any Codex billing modification. The
retained x86 job's missing /run/sshd runtime dependency is fixed in f4a6f15; its
results are separate from native ARM success. Do not claim all CI or production
readiness solely from these ARM receipts.

## Current Gate D review

See GATE_D_REVIEW.md and the superseding FRESH_BASELINE_APPROVAL.md for explicit
R read-only inspection, S staging, C one-file two-sample capture and D deployment
permissions. Native Gate C evidence is complete in its CI scope; no separate
physical ARM lab is requested. Production recovery/UID/paths, residual dependencies,
same-method policies/OCI/private path, anchor health, original DNSSEC timeout and
fresh approved baseline/real Windows/Android acceptance remain blockers. No Oracle
access occurred; next requested permission is R only, not staging or capture.
