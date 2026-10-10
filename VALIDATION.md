# Validation evidence — 2026-10-10

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

## Authorized service attempt: FAILED, rolled back — 2026-10-10 13:47 MYT

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
