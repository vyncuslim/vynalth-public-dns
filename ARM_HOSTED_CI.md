# Independent hosted ARM Gate C — execution not assumed

Owner authorizes the standard `ubuntu-24.04-arm` GitHub-hosted runner for this
PUBLIC repository. No physical ARM machine, OCI instance, paid/larger/self-hosted
runner, VPN or production access is used. Repo API confirms private=false and
visibility=public; Actions enabled=true. The ARM job also refuses private events.
[GitHub standard runner documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job)
lists this native ARM label and free standard runner use for public repositories.
No billing setting, purchase, resource provisioning or account change occurred.

## Independent job and fail-closed checks

`gate-c-arm64` is separate from the existing `validate` job; no existing tests
were removed. Read-only contents permission,20min timeout and explicit Bash
pipefail mean failed commands cannot be hidden by tee. No continue-on-error.
Source/config/service/Gate C manifest hashes are checked before tests.

The job records actual uname/aarch64, Ubuntu VERSION_ID24.04, PID1/systemd,
Unbound/package versions and aa-status. Preflight checks architecture and kernel
enforcement; each actual Unbound fixture additionally requires `/proc/PID/attr/current`
to be `unbound (enforce)`. Missing/complain/unconfined profiles fail the job;
AppArmor is never disabled or relaxed. Runner packages are installed only inside
the disposable hosted runner, not Oracle. There is no fallback to x86/emulation.

Tests: unit/syntax, enforcing local and two-source DNSSEC/ACL/PTR/negative response
fixtures, actual unique Unbound service/cgroup restoration, shell guard/file
recovery contracts and real180s uniquely named disposable timer tests. All DNS
fixtures use isolated network namespaces with no default route; no live Windows,
OPPO, Tailscale or external/Oracle DNS probes. Real timer tests continue to label
their service shims and do not claim real daemon or production recovery PASS.

## Actual-service/cgroup test scope

`tests/arm_service_recovery.py` refuses non-GitHub/non-ARM/known-production hosts
and requires enforcing AppArmor. It creates only a unique vynalth-arm-ci UUID
unit/drop-in under /run and owned lab files under /var/lib/unbound. The actual
Unbound PID/profile, systemd MemoryMax/TasksMax/LimitNOFILE, kernel memory.max/
pids.max and proc open-file limits must agree. Original lab limits256MiB/32/512
are changed to candidate384MiB/64/1024 then restored; UDP/TCP fixture results from
both synthetic /32 sources and different actual PIDs are verified.

Actual rollback.sh runs in private mounts. Its unit-name adapter delegates only
daemon-reload and restart to the real systemd manager/unique test service. This
is an actual isolated daemon restart, unlike a no-op service shim, but does not
prove production Unbound recovery, SSH/Tailscale continuity or Oracle networking.
The service fixture uses local data without a public root anchor; DNSSEC proof
is supplied by the separate enforcing signed-authority tests, not that A record.
No default unbound.service restart/config change or firewall operation is used.
If cleanup cannot stop the owned unit, fail and retain owned files/evidence.

## Evidence and unresolved scheduling blocker

Each step writes logs/JSON. Always-run hashing/upload steps retain artifacts for
14 days even after a started job fails. A job rejected before runner allocation
cannot execute these steps and produces no runtime artifact: absence is NOT
EXECUTED, never PASS. Partial logs cannot certify skipped later tests.

Before this update, both bcd873c check runs failed with the exact annotation:
`The job was not started because your account is locked due to a billing issue.`
Repository Actions is enabled; this is not a demonstrated runner architecture,
DNS, AppArmor or code failure. No executed runner log or exact underlying billing
cause is available. No settings were changed or purchases made. The account owner
can request GitHub clarification of the lock and public-runner eligibility;
there is no automatic retry, billing workaround or paid runner substitution.

Native ARM architecture/runtime/profile/isolated service/cgroup/timer/ACL/PTR/
DNSSEC tests are now **PASS**, with exact receipts in ARM_CI_RESULTS.md. See the
PR's latest checks for later commits. Earlier local development unit/static checks
are recorded separately in VALIDATION.md and are not ARM Gate C evidence.
No physical ARM machine is required if the standard job starts and proves these
properties. If profile or real recovery cannot be proven, their gates stay PENDING.

Existing180s rollback, strict<140s global confirmation, separately approved
post-confirmation Android<45s, fresh baseline and all production approval gates
are unchanged. This job cannot authorize deployment or claim live device success.

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
