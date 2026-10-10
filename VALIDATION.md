# Validation evidence â€” 2026-10-10

Local verification completed on Windows Python 3.12 and WSL Ubuntu 24.04.4:

| Check | Result |
|---|---|
| Python unit tests | 8 passed |
| Python compileall | passed |
| Cloud-init/workflow YAML parsing | passed; not a cloud-init boot test |
| Unbound Ubuntu package | 1.19.2-1ubuntu3.10, extracted locally without starting host service |
| unbound-checkconf | passed on runtime fixture configuration |
| DNS local runtime | UDP/TCP A/AAAA, signed DNSSEC AD, forged DNSSEC SERVFAIL, NXDOMAIN, ACL REFUSED, cache, RFC1918/ULA rebinding filtering, large-response TC/TCP, local authority outage/recovery, restart, bounded 40-packet loopback rate limit passed |
| nftables isolated namespaces | approved UDP/TCP 53 and TCP 22 connectivity; unapproved client denied; passed |
| SSH authentication | not tested; port-22 fixture is a TCP probe, not sshd |
| ShellCheck | scripts/*.sh and tests/*.sh passed |
| Terraform | 1.9.8 + oracle/oci 7.32.0: Linux init, fmt-check, validate passed |
| Windows Terraform provider | failed to return schema; Linux validation succeeded |
| Official OCI SDK model schema | capacity report models constructed locally; no cloud API request |
| GitHub Actions | job never started: account locked due to billing issue |
| Git diff whitespace | passed |

Linux distribution packages were extracted into local user cache; host Unbound,
SSH and firewall services were not installed or modified. Test interfaces and
firewall tables existed only inside disposable network/mount namespaces.

At the Phase A checkpoint, not executed: Terraform plan against real OCI identifiers, apply, OCI inventory/
capacity/pricing APIs, cloud-init boot, live systemd deployment/rollback drill,
real root/TLD/authoritative recursion acceptance, real SSH key authentication,
live egress outage, alert delivery, restore/failover and Spectrum IPv4/IPv6.
These remain deployment/production gates, not inferred passes.

GitHub billing issue must be resolved by the account owner; no billing settings,
subscription or spending limits were changed. Do not weaken CI or remove tests
to disguise the unavailable runner.

## Phase B: actual Oracle VM, 2026-10-10

Read-only SSH inspection and isolated repository tests were executed through the
Windows OpenSSH client. The key was only supplied as `ssh/scp -i`; its contents
were never read, displayed, copied or sent. The existing interactive SSH session
was kept open. No active DNS service, host firewall, SSH or Tailscale change.

| Observed check | Actual result |
|---|---|
| Identity/source | `vynalthai-dns`, Ubuntu 24.04.5, `aarch64`, user `ubuntu` UID 1001; SSH source `100.85.132.14`, destination `100.95.65.20:22` |
| Tailscale | active private connection/IP; fresh key-authenticated SSH succeeded |
| Unbound | 1.19.2; active, MainPID 8771, NRestarts 0 before and after isolated DNS/network tests |
| AppArmor | enabled; installed `unbound` profile enforcing; production `/proc/8771/attr/current` = `unbound (enforce)` |
| Current DNS listeners | UDP/TCP 127.0.0.1:53 and [::1]:53 only; no Tailscale/public DNS listener |
| Current host policy | Oracle iptables-nft input: established/ICMP/loopback, Tailscale chain, unrestricted new TCP 22, final IPv4 reject; no project table; IPv6 INPUT accept; UFW absent |
| Tailscale native rules | tailscale0 input accepted; UDP 41641 accepted; physical CGNAT spoof blocked; Oracle InstanceServices output rules retained |
| Other listeners | rpcbind 111, SSH 22 on wildcard addresses; Tailscale transport 41641 and peer API private ports; not changed |
| Effective sshd | password and keyboard-interactive disabled; public key enabled; root `without-password`, X11 and TCP forwarding enabled; no AllowUsers |
| Updates/disk | cached apt list 39 upgrade entries; MOTD separately reported 46 updates / 40 security; 45 GiB root, 3.1 GiB used, 41 GiB available; no apt refresh/update or reboot |
| Config syntax | active and staged private config both pass real `unbound-checkconf` |
| Trust/hints/time | managed `/var/lib/unbound/root.key` unbound-owned 0644; `/usr/share/dns/root.hints` packaged file exists; NTP synchronized; active service uses built-in hints, proposed config explicitly uses packaged hints |
| Current limits | MemoryMax infinity, TasksMax 6964, LimitNOFILE 524288; caches 4 MiB each; ip-ratelimit 0; EDNS 1232; proposed limits not installed |
| Unit tests | original 8 passed on ARM64; expanded suite 11 passed on ARM64 and Windows |
| AppArmor runtime | all fixture checks passed; latest fixture PIDs 10915/10917/10918 each `unbound (enforce)`; 0700 temporary directories cleaned |
| Isolated nftables lab | approved UDP/TCP 53 + TCP 22 port probe passed; unapproved rejected; production firewall unchanged |
| Simulated Tailscale lab | approved private DNS/SSH port passed; physical source spoof and unapproved tailnet DNS/SSH denied despite a later broad accept chain |
| Proposed firewall | `nft --check -f artifacts/private/firewall.nft` passed on actual VM; never applied |
| Service rollback lab | real transient timer `vynalth-rollback-test-11363` fired after 181 seconds; exact original main config and simulated prior unit drop-in restored, unrelated drop-in retained, originally absent private drop-in removed; strict service-command stubs, production PID 8771 unchanged |
| SHA256 checks | six reviewed service/baseline files and three active config files pass real VM `sha256sum --check` |
| Systemd staged unit | `systemd-analyze verify` with private artifact UNIT_PATH/drop-in passed; warned about pre-existing executable Oracle monitoring unit files, not changed |
| Windows/WSL checks | Python compileall, ShellCheck and diff whitespace passed; not production acceptance |

The AppArmor failure was caused by test config/state under `/tmp`, outside the
installed Unbound profile. The test now uses a disposable `/var/lib/unbound`
subdirectory already allowed by that profile. The installed binary remains
confined, the test control socket is disabled, fixture anchors/state are private
and children/directories are cleaned. Neither the profile nor production process
was relaxed, disabled or restarted.

### Live DNS evidence

Executed low-volume `dig` queries against localhost, not third-party load tests:

```sh
dig @127.0.0.1 cloudflare.com A +dnssec +time=3 +tries=1
dig @127.0.0.1 dnssec-failed.org A +dnssec +time=3 +tries=1
dig @127.0.0.1 dnssec-failed.org A +dnssec +tcp +time=3 +tries=1
dig @127.0.0.1 dnssec-failed.org A +cdflag +time=3 +tries=1
dig @127.0.0.1 example.com A +tcp +time=3 +tries=1
```

Results respectively: NOERROR + AD; SERVFAIL UDP; SERVFAIL TCP; NOERROR + CD
without AD (expected validation-disabled diagnostic); NOERROR + AD over TCP.
`unbound-control list_forwards` was empty; `list_stubs` showed only root priming;
module configuration contained `validator iterator`, with no configured upstream.

12-second `tcpdump -n -q` metadata-only egress observation (no stored query payload)
for controlled recursion saw root servers 192.5.5.241/202.12.27.33, .org TLD
199.249.112.1, .net TLD 192.5.6.30 and IANA authority
199.43.134.53/199.43.135.53/199.4.138.53. Random root/.iana.org names returned
NXDOMAIN + AD. Capture stopped intentionally by timeout (124); 38 packets,
zero kernel drops. Configuration plus destination evidence establishes actual
independent root/TLD/authority recursion for those queries.

Reproducible VM repository validation commands:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
sudo .venv/bin/python tests/local_runtime.py --require-apparmor
sudo bash tests/firewall_lab.sh
sudo bash tests/tailscale_firewall_lab.sh
sudo bash tests/service_rollback_lab.sh
sha256sum --check plans/phase-b-service.sha256
sha256sum --check plans/phase-b-active.sha256
sudo unbound-checkconf plans/phase-b-unbound.conf
sudo nft --check -f plans/phase-b-firewall.nft
```

The rollback lab exercised the actual rollback script in disposable bind mounts
using a real 180-second systemd timer, then a second manual restoration case.
`daemon-reload` and `restart unbound` were strict recorded stubs and nftables
execution was guarded against. Exact file restoration passed, but this does
not establish a successful restart of the production service. The temporary
timer/service and lab directory were cleaned. The new deployment/confirmation
transaction itself remains unexecuted pending final authorization.

Cache counters before/after two ordinary example.com lookups:
queries 18 -> 20, cache hits 6 -> 8, misses stayed 12.
One `www.nic.cz` lookup timed out with a 3-second limit during observation.
A single retry at 04:41:14 UTC returned cached NOERROR + AD in 0 ms. The earlier
timeout is retained; its cause was not established and this is not a latency SLA.

### OCI, recovery and pending checks

Read-only Chrome inspection of the default security list for vynalth-dns-vcn
showed stateful ICMP 3/4 from 0.0.0.0/0 and ICMP 3 from 10.0.0.0/16, with
all-protocol egress. No TCP 22/53 or UDP 41641 rule was shown in that list.
Full subnet security-list and VNIC/NSG attachments were not verified. OCI CLI/
authenticated SDK credentials were unavailable; do not infer effective OCI
policy or capacity from this one screen. No OCI settings were edited.
Public SSH connection to 134.185.94.152 timed out with strict host-key checking;
it is not verified recovery. Private SSH continues working.

Complete proposed config, real active-file diff, systemd limits and SHA256
manifest are committed under `plans/` and linked in PHASE_B.md. On the VM,
rendered config SHA256 was
`204aca36bc268e83e9878426605692b8c7f04b142fa0b0f8956c6d7e3486d2e7`.
The separate `deploy-private.sh` never calls install.sh, apt, nftables or network
configuration tools. The full installer remains outside this approval scope.

Not executed: production service deployment/restart/rollback, private Windows
DNS acceptance, a real second unapproved tailnet client test, host firewall
application/recovery drill, real egress outage, patching, alert delivery,
failover/restore, OCI billing/usage/shape APIs, Terraform apply/destroy or Spectrum.
The user explicitly deferred deployment pending code review and tests.
Existing A1 1 OCPU / 6 GiB shape and public IP are user-supplied inventory;
no new resources/charges were incurred by these actions, but the existing bill
and Always Free eligibility remain unverified. Monthly target is RM0.

## Authorized service attempt: FAILED, rolled back â€” 2026-10-10 13:47 MYT

The user explicitly approved only commit
`036575dfcf7ee1c9e5f0a15d8b7a4ab061b4ca97` and config SHA256
`204aca36bc268e83e9878426605692b8c7f04b142fa0b0f8956c6d7e3486d2e7`.
Before execution, Windows and VM HEAD/clean working tree, all six bundle hashes,
three active config baseline hashes, rendered/reviewed config byte equality,
Unbound syntax, Tailscale Running/online state and fresh SSH source
`100.85.132.14 -> 100.95.65.20` were verified. Existing SSH remained open.

Only the reviewed `scripts/deploy-private.sh` was executed, once, with the
approved hash. It armed the actual 180-second rollback timer, installed the
config and reviewed systemd drop-in, and restarted Unbound at 13:47:29 MYT
(05:47:29 UTC), new PID 13235. Its localhost readiness check passed.
No full installer, package upgrade, Terraform, OCI, SSH, Tailscale or firewall
configuration operation was executed.

| Windows private acceptance from 100.85.132.14 | Result |
|---|---|
| Fresh private key-authenticated SSH | passed; Unbound and tailscaled active |
| example.com A / UDP | NOERROR + AD |
| example.com AAAA / UDP | NOERROR + AD |
| example.com A / TCP | NOERROR + AD |
| cloudflare.com A / UDP | NOERROR + AD |
| dnssec-failed.org A / UDP | **FAIL: timeout at 5 seconds**, not observed SERVFAIL |
| Bogus TCP, CD diagnostic, NXDOMAIN, root DNSKEY | not executed; stopped at first failure |
| Post-deploy cache, negative ACL, effective limit/port assertions | not executed; stopped at first failure |

The client bound its real Windows Tailscale source IP. Each query was attempted
once; no automatic retry, relaxed timeout, alternate upstream or bypass.
Acceptance deliberately stopped on the first timeout and did not run confirm.sh.
The timeout's cause is unconfirmed. Reviewed logs show normal starts/stops and
the distro's unset DAEMON_OPTS warning; no matching Unbound AppArmor/OOM event
was found in the inspected kernel window. This evidence does not prove an
upstream fault or a configuration defect.

Immediate rollback ran the installed approved `/var/lib/vynalth-dns/rollback.sh`.
At 13:47:37 MYT (05:47:37 UTC) it restarted the original service with PID 13423.
The original main config and both include hashes passed; private.conf was
removed, DropInPaths empty, and effective settings restored to MemoryMax
infinity / TasksMax 6964 / LimitNOFILE 524288. Recovery snapshot retained at
`/var/lib/vynalth-dns/rolled-back-1791611257`.

Current verified state after rollback:

- Unbound active/running, PID 13423, NRestarts 0, `unbound (enforce)`.
- Unbound UDP/TCP listeners only `127.0.0.1:53` and `[::1]:53`.
- No Unbound Tailscale or public DNS listener. systemd-resolved retains its
  separate pre-existing 127.0.0.53/127.0.0.54 stub listeners.
- Unbound config syntax and all original baseline hashes restored; approved
  repository bundle hashes remain unchanged.
- Fresh Tailscale SSH still succeeds; Unbound, tailscaled and ssh active.
- No pending rollback snapshot/confirmation; the timer had not fired and was
  stopped only after verifying restoration. Final timer state inactive.
- No network-policy command was executed by the service-only transaction or
  its service-only rollback branch. The post-deployment before/after network
  hash comparison was not reached; do not report that comparison as passed.

The attempted private service is **not deployed successfully**. The prior eight/
eleven unit tests and isolated runtime/rollback evidence remain historical
passes, not substitutes for this failed live acceptance. No second attempt.
Structured sanitized transaction evidence is retained in
`plans/phase-b-deployment-result.json`. Existing cloud billing assumptions and
GitHub runner billing lock are unchanged. A new attempt requires root-cause
investigation, a complete acceptance plan and renewed human authorization.

## DNSSEC timeout investigation â€” 2026-10-10, no production redeployment

Starting HEAD was `ba6d457`. All work used the existing Windows OpenSSH client
with strict host-key checking and the key filename only. Fresh SSH again proved
`100.85.132.14 -> 100.95.65.20`; the original SSH session stayed open. Production
was not restarted, reconfigured or cache-flushed. No private deployment
acceptance was performed against its inactive Tailscale listener. No
firewall, SSH, Tailscale, OCI, Cloudflare, DNS record, package or OS change.

### Confirmed mechanism and diagnostic defect

The old `tests/acceptance.py` and the original operator transaction used a fixed
5s client timeout without a cold-cache latency rationale. This is the client's
reply wait, not the validator's deadline. It did not retain enough structured
information to distinguish missing UDP replies, TCP EOF, validation failure and
latency failure. The new function requires a timeout; the CLI emits exact
question/ID, DO/CD, transport/source, UTC timestamp, monotonic elapsed time,
RCODE, AD/CD/TC/EDE, typed exception, outcome and attempt count. An absent reply
has null response fields. Correct late replies stay failed. No automatic retry.

Installed Ubuntu package is **1.19.2-1ubuntu3.10**. Despite the upstream version
banner, its changelog includes the DNSBomb mitigation backport. Read-only
`unbound-control get_option discard-timeout` returns **1900 ms**. The previously
reviewed config inherited this default. `wait-limit=1000`, cookie limit=10000,
validator restart limit=5, bogus cache TTL=60s and serve-expired=no were observed.
The reply expiry mechanism is independently documented in
[NLnet Labs' release notes](https://nlnetlabs.nl/news/2024/May/08/unbound-1.20.0-released/);
[Ubuntu's CVE record](https://ubuntu.com/security/CVE-2024-33655) confirms the
Noble backport. These are not reasons to disable the mitigation with zero.
[dnspython query documentation](https://dnspython.readthedocs.io/en/stable/query.html)
defines the separate client timeout. Newer upstream TCP behavior must not be
assumed to match this installed backport; the TCP outcomes below were measured.

All listed experiments were separate predeclared fresh processes on loopback
15355, enforcing `unbound (enforce)`, with zero initial client queries, 1024
descriptors and a systemd scope capped at 384MiB/64 tasks. They used disposable
0700 files, copied public trust anchors and isolated Unix control sockets.
No AppArmor profile or permission broadening occurred. The deterministic
six-second local authority fixture uses only its pinned zone trust anchor and
never needs Internet DNS. Each cold failure suppresses its warm case.

| Experiment | Cold result | Warm result / conclusion |
|---|---|---|
| Real recursion, inherited 1900ms, valid cloudflare.com UDP/TCP | NOERROR + AD, 0.648s / 0.525s | <1ms, cache hit increment 1 each |
| Real recursion, inherited 1900ms, bogus dnssec-failed.org UDP | no response after 20.010s observation | skipped, not SERVFAIL |
| Same baseline, fresh process, bogus TCP | EOF at 5.792s, no DNS response | skipped; transport error preserved |
| Local 6s authority, explicit 1900ms, valid/bogus UDP | no response at ~20s | expected negative-control reproduction |
| Same local authority/control, valid/bogus TCP | EOF at ~6s | expected negative-control reproduction |
| Local 6s authority, finite 15000ms, declared 5s threshold | correct replies at ~6.01s, **latency_exceeded** | skipped; a longer observation does not turn FAIL into PASS |
| Same finite window, declared 15s threshold, valid/bogus UDP/TCP | NOERROR + AD / SERVFAIL without AD at ~6.01s | <1ms, hit increment 1 each |
| Real recursion, finite 15000ms, bogus UDP/TCP | SERVFAIL without AD at 6.070s / 2.584s | <1ms, hit increment 1 each |
| Final rendered config, no experimental override, valid UDP/TCP | NOERROR + AD at 0.484s / 0.690s | <1ms, hit increment 1 each |
| Final rendered config, no override, bogus UDP/TCP | SERVFAIL without AD at 2.664s / 2.404s | <1ms, hit increment 1 each |
| Final rendered config, local delayed fixture UDP/TCP | valid and bogus expected replies at 6.009â€“6.016s | <1ms, hit increment 1 each |

The controlled A/B changed the finite discard window with the same authority
delay and validation setup. Extending client observation alone did not fix the
missing replies; changing the server reply-age bound did. Isolated bogus logs
show DNSKEY/DS mismatch against authoritative servers and correct validation
failure. No alternate forwarder was introduced. Independent iterator, root
hints and empty `list_forwards` were verified in every recursive child; earlier
recorded root/TLD/authoritative packet evidence remains applicable to the design.
This investigation did not capture the historical failed packet.

**Confidence:** reply expiry plus the arbitrary 5s acceptance budget is a
confirmed reproducible defect and a high-confidence explanation of the original
failure. Original PID 13235 had verbosity zero and no packet capture, so the
exact historical packet path/delay cannot be proved retrospectively. Upstream
delay variance, packet loss and Tailscale-path latency in that one event remain
possible contributors. The observed 2.4â€“6.1s bogus validation variability is not
a service latency guarantee. Warm success does not erase a cold failure.

### Read-only production and resource evidence

Production remained PID **13423**, NRestarts 0, active and enforcing. Original
main/include baseline hashes passed, no systemd drop-in, and listeners remained
only 127.0.0.1/[::1] UDP/TCP 53. systemd-resolved's existing stub is separate.
The inspected production receipt contains 15 queries, 9 cache hits and 6 misses;
aggregate counters do not identify their source and do not attest cold state.
No individual production query logging was enabled. Main config,
PID/restart count, stateless nftables and effective SSH hashes match across all
isolated before/after receipts. The root anchor refreshed normally at 06:15 UTC
between experiments (last_success/query_failed=0); no operator anchor edit.
NTP is synchronized, both root KSKs remain valid, root hints readable. No
matching Unbound AppArmor denial or OOM event was found in the inspected kernel
window. These are bounded observations, not proof that no packet was lost.

Current available memory was ~5340MiB and production MemoryCurrent 8937472 bytes.
Original systemd settings remain MemoryMax=infinity/TasksMax=6964/NOFILE=524288;
the daemon's own descriptor limit is 4152. Successful isolated children instead
ran with 1024 descriptors and the proposed cgroup caps. This argues against
those proposed resource caps causing this reproduced failure; no sustained load
or public abuse capacity claim is made. Current SSH/firewall risks and incomplete
OCI ingress inventory/recovery are unchanged from the preceding audit.

Committed receipts under `plans/investigation/`:

- `dnssec-recursive.json`: inherited-default real-recursion failures retained.
- `dnssec-fixture-control.json`: four explicit 1900ms negative controls; missing
  replies are expected experiment outcomes, not DNS acceptance passes.
- `dnssec-fixture-fixed.json`: eight separate 5s/15s finite-window experiments;
  four deliberate 5s latency failures preserved.
- `dnssec-recursive-fixed.json`: first finite-window real-recursion comparison.
- `dnssec-reviewed-recursion.json`: final config's four cold/warm pairs.
- `dnssec-reviewed-fixture.json`: final config, including measured cgroup caps.
- `dnssec-production-readonly.json` and `dnssec-system-readonly.json`: effective
  service, ports, hashes, anchor metadata, package, resources and service logs.

### Validation and revised procedure

All **23 unit tests passed** on Windows Python 3.12 and the real ARM64 VM,
including the original eight. Full `local_runtime.py --require-apparmor` passed
UDP/TCP A/AAAA, signed/bogus DNSSEC, NXDOMAIN, ACL, truncation/TCP fallback, cache,
rebinding, isolated authority outage/recovery, child restart and bounded rate
limiting; all three children reported enforcing confinement. Rendered Unbound
syntax passed. Python compilation, YAML parsing, Git whitespace and shell syntax
checks passed. Shellcheck is absent on the VM; it was not installed, and a fresh
Shellcheck pass is not claimed. Transaction shell code is unchanged from its
earlier validation. Terraform/network/rollback labs are unchanged; their earlier
results remain historical. The successful real rollback remains retained.

Proposed config SHA256:
`d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`.
The complete config/diff and expanded bundle checksum manifest are committed.
The revised [PHASE_B.md](PHASE_B.md) procedure requires fresh review/approval at
the new exact commit, rechecks baseline/source/hash, and uses the existing 180s
automatic rollback. Acceptance is capped at 100s, cold 15s/warm 2s, standard/CD
5s and negative ACL 2s. Confirmation additionally requires transaction elapsed
<140s. Diagnostic labs may observe for 20s but still fail beyond 15s; production
acceptance uses no extended observation. Controller tests prove first-failure
stop, missing cache evidence failure, source/listener rejection and deadline
failure without sending a next query. It has no deployment/confirmation calls.

**Decision:** the correction is supported for a newly authorized, rollback-
protected private trial. It is not deployed or production-ready. The Windows
Tailscale path under the new config, complete live acceptance and a real second
unapproved tailnet client's rejection remain unverified. Public service remains
blocked. The longer finite reply window needs a separate abuse/capacity review
before broader exposure. RM0 remains a target, existing billing unverified;
no resources or paid services were created. GitHub Actions remain subject to
the account billing lock; no CI execution success is claimed.

## Second approved private trial â€” ABORTED BEFORE DEPLOYMENT, 2026-10-10

The user approved only `61a9ad8c342717d10974b6de1e274a0e180d09e6` and config
SHA256 `d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`.
No approved service file or executable was changed by this reporting commit.
The orchestration aborted during preflight; **deployment attempts = 0** for
this authorization. No `deploy-private.sh`, Unbound restart, rollback timer,
acceptance controller or `confirm.sh` execution by the agent. No automatic retry.

| Preflight / acceptance item | Actual result |
|---|---|
| GitHub Draft PR head, remote branch, Windows and VM HEAD | exact approved commit, clean worktrees |
| Windows / VM 13-file service manifest | all hashes passed |
| Active main config / both include hashes, rendered byte equality, syntax | passed |
| Existing systemd drop-ins and include set | no drop-ins, original two include files |
| Private SSH / Tailscale | real source 100.85.132.14 -> 100.95.65.20, both online; retained session still open |
| AppArmor | unbound (enforce) before and after abort |
| Recovery | old real rollback snapshot retained; no pending snapshot or active timer |
| Stable service baseline | **FAIL: initial MainPID13423 no longer matched; journal shows 24650, subsequent inspection 34123** |
| Cold / warm DNSSEC UDP/TCP, A/AAAA, NXDOMAIN, CD, cache and ACL | **NOT RUN**; no live latency or PASS receipt |
| 180s transaction and <140s confirmation gate | NOT STARTED; no confirmation |

The raw orchestration log retains its assertion failure and attempt count zero.
Subsequent diagnostics identify the differing field as MainPID; the exact failed
inspection's JSON was not saved by the wrapper, so its intermediate PID is
correlated from the service journal rather than claimed as a captured receipt.
No threshold or
baseline was relaxed to continue. The failure was not a DNSSEC timeout. Original
active config, effective systemd limits and management hashes still matched.

Service journal timeline (UTC; MYT = UTC+8):

- 06:52:21: existing `apt-daily-upgrade.service` / unattended-upgrade started.
- 06:52:47: initial inspection still observed PID13423 and original baseline.
- 06:53:53: Unbound stopped/started with PID24650.
- 06:55:20: final transaction preflight bundle/config checks passed; the following
  active-service equality check failed before the transaction timer was started.
- 06:56:04: Unbound stopped/started again with PID34123.
- 06:56:18: unattended-upgrades log reports all upgrades installed.
- 06:57 onward: read-only verification found PID34123 active, NRestarts0.

The automatic-maintenance dpkg log explicitly contains a `needrestart` command
restarting `unbound.service`, `ssh.service`, `systemd-networkd.service`,
`systemd-resolved.service` and other services after package updates. This links
the observed baseline drift to concurrent host maintenance, independently of the
agent's zero-attempt transaction. The agent neither started those upgrades nor
changed/restarted those services, and did not disable the maintenance mechanism.
Unbound package remains 1.19.2-1ubuntu3.10; library/kernel packages changed under
existing automatic maintenance. `reboot-required` lists the new Oracle kernel
and linux-base. **No reboot was performed.** NRestarts0 does not mean no restarts:
explicit service starts are visible in the journal and may reset that counter.

Final inspected state: Unbound active PID34123, enforcing; listeners only
127.0.0.1/[::1] UDP/TCP53, no Tailscale/public Unbound DNS listener. Effective
MemoryMax=infinity, TasksMax=6964, LimitNOFILE=524288; DropInPaths empty. Default
discard timeout remains 1900ms. The final receipt reports zero client queries,
zero cache hits/misses/recursive replies; these are counters after the external
restart, not a successful cache/DNSSEC test. SSH and tailscaled active, retained
private SSH session usable. Stateless nftables and effective sshd hashes match
the initial preflight. The agent made no management-network/cloud/DNS changes.

`vynalth-rollback.timer`: LoadState=not-found, inactive/dead; no new snapshot.
No rollback command was needed because the deployment never started and active
files were not written. Previous recovery snapshot remains retained. Do not run
a recovery operation that would undo unrelated maintenance changes.

Sanitized initial/final service receipts, the abort log, PID diagnosis, Tailscale
preflight and host-maintenance logs are committed in `plans/second-attempt/`.
Stop further deployments as instructed. Before any fresh trial, review the new
service/package baseline and pending-reboot disposition in a stable maintenance
window, obtain fresh authorization, and reverify all existing gates. Do not
automatically disable updates, reboot, retry, confirm or promote public service.
No cloud resources were created; existing cost assumptions remain unverified.

## 2026-10-10 post-maintenance review (no production change)

Read-only inspection after unattended-upgrades/needrestart found production
PID34123 active/enforcing, invocation2cad7a7d4117419398f15349dcf710f5, original
127.0.0.1/[::1] UDP/TCP53 listeners, no private drop-in or forwarders. Main config,
two includes, complete original service manifest and management fingerprints
still match. The reviewed proposed config SHA256 remains
`d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`.
Fresh private SSH source100.85.132.14 ->100.95.65.20 and the retained session both
worked. tailscaled/unbound enabled; ssh.socket enabled/active. No new independent
OCI console or public SSH recovery verification is claimed.

Two samples60s apart at07:17/07:18 UTC matched exact kernel/boot/service/binary/
configuration/management fingerprints. apt services inactive/dead, no installer
or needrestart processes, four package locks unoccupied. Existing waiting
unattended-upgrade-shutdown helper was explicitly distinguished from installation.
Schedules were >15min away at sampling, not a guarantee of future inactivity.
Frozen review baseline and raw capture are committed under plans/. Its pinned
comparison matched the exact fingerprint at both samples; its only failures
were pending reboot (exit1, deployment_ready=false). Capture does not authorize
deployment or auto-refresh.

Pending reboot remains: running6.17.0-1020-oracle, installed7.0.0-1013-oracle and
linux-base; new /boot links and old fallback image/initramfs verified. No scheduled
shutdown was present. Separate console-backed maintenance approval is recommended
before another DNS trial; the actual post-boot fingerprint requires new review.
No reboot, policy change, upgrade or production restart occurred in this review.

Historical timer journal proves missing-fragment warnings began after the timer
was explicitly stopped05:49:15, before its deadline; current timer not-found and
no pending snapshot. Transient GC/stale references are a plausible explanation,
not a proven exact systemd bug. The same exact warning was not reproduced.
Harmless isolated cancellation/same-name2s rearming succeeded independently.

Existing180s isolated rollback lab passed: journal07:12:11 armed,07:15:11 fired;
outer monotonic181.385918s, shell observation182s including polling/rounding.
Config/prior settings restored byte-for-byte, unrelated drop-in retained and
initially absent private.conf removed in a separate isolated case. Production
PID/invocation/config/nft/sshd fingerprints unchanged. Production daemon-reload/
restart calls were stubbed in disposable mounts; this is not a new live rollback
or proof of future recovery. Lab transient units/temp data cleaned.

Proposed read-only timer gate tested against real independent lab units:
180s active/waiting PASS (179.928543s remaining);60s FAIL;stopped/missing FAIL.
During lab development busctl scalar decoding and cancellation cleanup assumptions
were corrected; only disposable lab units were involved. The production script
remains unchanged and the patch is not applied. Adoption requires a separately
reviewed updated script/bundle manifest/commit and fresh approval.

30 unit tests passed on Windows Python3.12 and real Ubuntu ARM64 (original eight
included); seven additional tests cover maintenance/process/lock/schedule gates
and busctl property decoding. Python compilation, JSON and patch dry-run checks
passed. No new live private DNS acceptance was run; previous DNSSEC/runtime
evidence above remains historical. No fresh full DNS runtime or Shellcheck pass
is claimed. GitHub Actions remain billing-blocked; local success is not CI success.

See POST_MAINTENANCE.md for reproduction commands, exact proposed gates, separate
maintenance/recovery plan and blocked future approval terms. Evidence collectors
and receipts are in plans/post-maintenance/. No deploy-private/install/confirm/
production rollback, firewall/SSH/Tailscale/OCI/Spectrum/public-DNS mutation,
Terraform operation or paid-resource creation occurred. Further deployment is
stopped awaiting fresh explicit authorization after prerequisites are satisfied.

## 2026-10-10 integrated private identity and post-boot candidate (development only)

Actual remote starting HEAD9bc27af72a1a2229d440f025caf2aefa777a784e was inspected
and safely fast-forwarded, preserving the newer PTR proposal and Issue2 scope.
No force push or merge. PTR is now generated from the private JSON policy at the
single owner20.65.95.100.in-addr.arpa., returning exactly dns.vynalthai.com.
New actual config SHA256:
`e20308ba789cd7aebeb0a4e009c5df120a0523ebf9a8891176a8b67ddd6c5b1b`.
UTF-8/LF writes prevent Windows newline drift; rendered bytes equal reviewed
config. The old hash above remains historical. Source guards, reviewed candidate
baseline and all runtime imports are covered by the updated18-file manifest.

Original post-boot evidence was present on Oracle; actual retrieval matched
5e1b72073fa74dbd975601a513fa1b5c9e34ac773b45ebdc88863239d82bc4b3.
Both samples match, no operational failures/reboot flag, kernel7.0.0-1013,
PID984, boot ID06c41b28-e22e-4540-8bd7-61b91fcaf465 and enforcing AppArmor.
Candidate baseline SHA256cbb29c44eebd8d3423dffffe99009c1f3cbaa2e5325439b81a7a73a3aa84820b
is review-only and requires human approval. Fresh10:50:09UTC read-only sample
matched, NTP=yes, no maintenance failure/pending reboot. An initial read-only
invocation emitted a generic failure without field evidence; its precise cause
is unproven. Preserve it as failure, not PASS. Checker now fixes repository cwd
and emits failure fields; a direct updated invocation passed. No auto-approval.

Testing used a separate0700 temporary checkout and high loopback ports. Oracle
working HEAD remained24aa2d0; its repository was not staged. Production
PID984/invocation/config/nft/sshd stayed unchanged. No production restart/reload,
/etc/unbound write, reboot, OS/update-policy change, SSH/firewall/Tailscale/OCI/
Spectrum/public DNS mutation, install.sh or Terraform operation occurred.

Real enforcing runtime passed exact PTR UDP/TCP, unrelated reverse with/without
identity, A/AAAA, valid/bogus/CD DNSSEC, NXDOMAIN, approved-loopback/unapproved
A+PTR REFUSED, cache, rebinding, truncation/TCP fallback, local outage/recovery,
child restart and bounded40-packet loopback rate limiting. Local6s signed/bogus
UDP/TCP cold cases passed at6.008725â€“6.016141s with finite15000ms; distinct warm
cases passed with one measured hit each. Fixture and low-volume recursive
children used384MiB/64-task scopes,1024 descriptors, enforcing profiles and no
forwarders. Valid cloudflare.com NOERROR+AD UDP/TCP1.111152/0.521043s; bogus
dnssec-failed.org SERVFAIL without AD UDP/TCP2.468710/2.941162s. Timeout never
counts as successful DNSSEC rejection. Original live timeout cause remains
uncertain; earlier1900ms mechanism evidence is retained, not reinterpreted.

Actual timer readiness180s PASS;60s and missing/stopped timers correctly rejected.
Actual180s isolated restoration passed after181s observation: config/prior limits
restored, unrelated drop-in retained and originally absent private.conf removed;
production unchanged. Current actual shell scripts passed private-mount/strict
shim tests with synthetic receipts: success, bad timer before writes, missing
receipt and>=140s deadline. These are contract tests, not live DNS PASS records.
A test import, initial-budget assertion and fixture rendered-path error were
fixed during development; no security threshold or live deployment was retried.

Confirmation validates complete inventory/PTR/flags/cache/ACL evidence, current
config/process/AppArmor/listeners/limits/management state and boot-bound
monotonic<140s transaction. It retains the independent timer through atomic
snapshot confirmation; the timer then no-ops at180s if confirmed. Errors/signals
invoke rollback. Changed design and<120s Windows submission reserve are explicit
in POST_BOOT_REVIEW.md and require new exact approval.

Raw outputs/original capture/baseline comparison/DNSSEC latency/cache/resource/
timer/rollback receipts are under plans/integration/. Final counts/checks are in
the candidate report. Windows PTR/nslookup display, actual Tailscale DNS and a
second unapproved tailnet client remain NOT TESTED / PENDING LIVE ACCEPTANCE.
Final Windows Python3.12 and real Ubuntu ARM64 each passed38unit tests. Exact
rendered bytes,18-file bundle,syntax,Python compilation,YAML and Bash syntax
passed. Shellcheck was absent and is NOT TESTED. Root unit/script manifests and
the original capture hashes were verified on actual bytes. CI remains blocked.
CI is billing-blocked, not passed. Shellcheck availability/pass is not assumed.
RM0 remains an unverified target; no paid resources were created. Stop before
live changes until exact new commit/config/baseline/bundle authorization.

## User STOP revision: boundary deviation, local-only follow-up

The earlier "isolated" development environment was on the LIVE Oracle VM.
Creating/transferring test files, launching processes/scopes/transient units and
removing the first checkout deviated from the development-only boundary. Private
mounts/shims do not make this compliant. The user stopped further VM writes/tests/
cleanup/timer operations. No new Oracle command was sent after that instruction;
only buffered output from pre-existing SSH session8534 was read. It reported0,
unchanged production fingerprints and an updated180s restoration PASS (181.403s
monotonic,182s integer observation). Its embedded automatic cleanup may have
already executed; exact ordering/current residual status is NOT REINSPECTED.

LIVE_VM_IMPACT.md inventories paths/processes/units, prior deletion and retained
second checkout /var/lib/unbound/vynalth-dev.PMaPSc. Current active status/full
resource impact are unknown. Do not infer no impact from PID/hash equality, or
delete artifacts/stop timers. Separate approval is required for scoped read-only
audit and then itemized cleanup if requested. Original config remains last
observed8808b474..., PID984; no production deploy/restart was observed.

After the stop all changes/tests were Windows/local WSL only. The old server-local
140s origin was insufficient for end-to-end timing. New client coordinator T0
precedes ALL commands/network/verification and shares one140s budget. Its
conservative monotonic/boot probe maps remaining global time to the server;
server confirmation also requires this deadline and never resets140s after
preflight. Missing context/NaN/delay/exhausted budget fail closed. Lost confirmation
reply is UNKNOWN and not retried. Independent180s protection is never stopped by
confirmation. Source staging/deployment is not authorized by this implementation.

Private rollback calls now force --service-only even if the marker disappears,
and installed rollback is root-owned0700. Local WSL real-file restore initially
failed on a same-second archive collision; PID-suffixed atomic archive naming
fixed it. Four present/absent drop-in/marker cases then passed with strict service
shims and nft prohibited; no-snapshot callback passed without service calls.
This is file/contract validation, not AppArmor or production restart evidence.

Latest local Windows suite:48unit tests PASS, including global command/network
budget, long verification, acceptance/transfer delays, missing server deadline,
complete mocked flow and lost confirmation response/no retry. Python compile,
local WSL Bash syntax, YAML, exact rendered bytes and current20-file bundle
checks are recorded in final local evidence. Latest source was NOT retested on
Oracle; historical38ARM/38Windows/18-file results above are not current candidate
validation. Original configuration content/hash e20308ba...d6c5b1b is unchanged.
Local WSL has no Unbound; latest full timing/service ARM runtime is NOT TESTED.
Windows live acceptance and second tailnet client remain PENDING. CI billing
lock and absent Shellcheck are NOT PASS. No new live status/recovery guarantee.

## Android integration: local-only validation

Starting branch HEAD df070d3466c64c7dde68f69304532dfffd1ba51f was verified
against origin before editing. No Oracle connection or experiment was made.
The earlier live laboratory boundary deviation remains documented in
LIVE_VM_IMPACT.md; current residues and production impact remain unknown.

- PASS: 53 unit tests on Windows and 53 on local WSL Linux.
- PASS: actual local Unbound 1.19.2, namespace without a default route, exact
  synthetic Windows and Android source IPs: UDP/TCP A/AAAA, exact PTR, unrelated
  reverse NXDOMAIN, valid DNSSEC NOERROR+AD, bogus SERVFAIL, CD diagnostic.
  Timeout is never counted as rejection. Both sources measured two warm cache
  hits. Eight unknown-tailnet/public-source probes returned REFUSED.
- PASS: actual rollback file restoration in four prior-file/marker variants
  plus no-snapshot no-op, using strict service shims and no firewall calls.
- PASS: Shellcheck of deploy/confirm/rollback and local rollback harness.
- NOT TESTED: enforcing AppArmor locally (kernel unavailable), new ARM runtime,
  fresh real 180-second timer, real Tailscale path and system-wide phone DNS.
  Historical live tests do not validate this new candidate.
- PENDING LIVE ACCEPTANCE: Windows and OPPO hardware, production private
  listeners, fresh baseline/recovery/firewall review. CI requires AppArmor;
  local success does not imply CI passed.

Raw current evidence: plans/integration/android-local-runtime.json,
android-linux-unit.txt, android-rollback.txt and android-shellcheck.txt.
The Windows transaction is unchanged at strictly <140s total and 180s rollback.
The ten-query mobile release gate is separate, <=45s, fail-fast and DNS-only.
No deployment or Tailscale DNS Override is authorized by these results.

- PASS: full local_runtime.py in a local network namespace, including large
  answer truncation/TCP fallback, rebinding, authority outage/recovery, isolated
  restart and bounded rate limits. Raw android-full-runtime.txt is normalized
  to remove the proc attribute NUL terminator; original remains local.
- NOT TESTED: Tailscale firewall simulation this update; local nft/iptables
  binaries are absent. CI retains the expanded two-client simulation.

## Review6098859695: phone failure evidence and audit preparation

Owner-reported2026-10-10 OPPO/Termux dig9.20.24 explicit Vynalth A queries got
connection refused or5s timeouts. Same-phone1.1.1.1 control returned NOERROR,
two dynamic A answers and76ms. Default DNS was unchanged. Evidence source is
the linked owner review in ANDROID_DNS.md, not a new Codex live measurement.
Transport failure is not REFUSED RCODE; no exact current root cause is confirmed.
Earlier localhost-only listeners and overlay ping are historical. No repeated
phone probes, Oracle SSH/SCP/commands, cleanup, service/timer or DNS changes
were made. No new runtime PASS or baseline approval is claimed.

Prepared ORACLE_READ_ONLY_AUDIT.md for separately authorized, existing mobile
serial-console use, with minimal service/listener/syntax/localhost query and
focused retained lab inventory. PHASE_B_APPROVAL_CHECKLIST.md separates audit,
cleanup, readiness validation, exact approved service trial, mobile gate and
settings gates. Config/21-file service manifest bytes remain unchanged; review
checksums cover this documentation update. Live acceptance stays PENDING.
