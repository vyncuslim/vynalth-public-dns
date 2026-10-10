# Test matrix and boundaries

CI/unit checks are not production acceptance. No public load/attack tests.
`local_runtime.py` starts a high-port loopback process and terminates it, without
editing the host service or firewall. Each `acceptance.py` scenario sends at most
seven one-shot queries to an explicitly authorized resolver; root/authoritative queries are the
resolver's normal DNS operation, not attacks or benchmark load.

On Ubuntu with an enforcing packaged AppArmor profile, use:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
sudo .venv/bin/python tests/local_runtime.py --require-apparmor
sudo bash tests/firewall_lab.sh
sudo bash tests/tailscale_firewall_lab.sh
sudo bash tests/service_rollback_lab.sh  # actual 180s timer; isolated files/stub service calls
```

The runtime uses a 0700 disposable directory inside `/var/lib/unbound`, which
the existing Ubuntu profile already permits. It checks each child process's
`/proc/PID/attr/current` for `unbound (enforce)`. Config, fixture trust anchor,
PID and logs are isolated; remote control is disabled so the production socket
is never used. Children are terminated and the directory removed. No profile
edit, permissions broadening, production restart or firewall modification.
`--work-dir` is for explicitly permitted lab paths; it is not an AppArmor bypass.

The Tailscale firewall lab uses veth devices to simulate `tailscale0` and a
physical interface, plus a later broad accept chain. It verifies approved
UDP/TCP DNS and SSH port access, physical-interface source spoof rejection and
unapproved tailnet rejection. It is not a real Tailscale/WireGuard recovery test.
The rollback lab restores a copy of the actual main config and simulated prior
systemd drop-in, including originally absent drop-in removal. Service calls are
strictly stubbed; it cannot establish production restart success.

| Property | Executable / procedure | Required evidence |
|---|---|---|
| A/AAAA UDP/TCP, NXDOMAIN | local_runtime.py + acceptance.py | valid answer/rcode |
| DNSSEC valid/bogus | local_runtime.py ephemeral signed fixture + acceptance.py | AD on valid, SERVFAIL on forged answer |
| Large response/TCP fallback | local_runtime.py | TC with 512 byte EDNS, TCP complete |
| Restart | local_runtime.py; VM `systemctl restart unbound` then acceptance | recovery + alert |
| ACL renderer | test_policy.py | host-only networks, wildcard/injection rejection |
| Unauthorized resolver client | local_runtime.py source 127.0.0.2 | REFUSED UDP/TCP |
| Origin/SSH firewall | firewall_lab.sh isolated namespaces; live external checks still required | approved DNS/22 reachable; unauthorized blocked |
| Cache | local_runtime.py local authority, query twice | no upstream second request |
| Recursion | acceptance.py, reviewed config and low-volume origin capture | root/TLD/authority destinations; no forwarders |
| Rate limits | local_runtime.py, bounded 40 loopback packets | excess replies dropped |
| Network outage | local_runtime.py stops/starts private authority; VM egress drill still required | timeout/SERVFAIL, recover after restore |
| Rebinding | local_runtime.py authority returns RFC1918 A/ULA AAAA | filtered answer |
| Service limits, patches, SSH | VM systemctl/sshd -T/package checks | exact effective configuration |
| Spectrum identity IPv4/IPv6 | blocked until decoder and contract review | client identity, return framing, spoof rejection |
| Failover/alerts/restore | separately approved secondary lab/VM | failure + notification + recovery |

No missing test should be treated as PASS. Phase D requires runtime evidence for
every row, effective OCI rules and live edge acceptance. Never report an
unexecuted drill as successful. Static checks cannot establish network behavior.

## DNSSEC timeout investigation

`acceptance.py` requires an explicit observation timeout. It preserves transport,
question, elapsed time, RCODE, AD/CD/TC, EDE and exception type. Null response
means no reply was observed, not SERVFAIL. A correct reply exceeding the declared
latency limit remains failed. There are no retries or automatic UDP/TCP fallback.
Cold and warm scenarios must be identified explicitly; CLI cache evidence is an
operator attestation. The isolated harness proves cold process query count zero
and warm cache-hit increments through its own control socket.

Run the deterministic six-second signed authority A/B tests on the authorized VM:

```sh
sudo systemd-run --scope --unit=dnssec-default-control -p MemoryMax=384M -p TasksMax=64 \
  .venv/bin/python tests/isolated_dnssec.py --mode fixture --discard-timeout 1900 \
  --require-apparmor --out artifacts/dnssec-control.json
sudo systemd-run --scope --unit=dnssec-finite-window -p MemoryMax=384M -p TasksMax=64 \
  .venv/bin/python tests/isolated_dnssec.py --mode fixture --discard-timeout 15000 \
  --legacy-comparison --require-apparmor --out artifacts/dnssec-fixed.json
# Low-volume independent recursion: explicit authorized lab only, never CI load.
sudo systemd-run --scope --unit=dnssec-recursion -p MemoryMax=384M -p TasksMax=64 \
  .venv/bin/python tests/isolated_dnssec.py --mode recursive --authorized-recursion \
  --require-apparmor --out artifacts/dnssec-recursion.json
```

Each experiment creates a fresh enforcing Unbound process on 127.0.0.1:15355,
1024 descriptors, an isolated trust anchor/control socket and disposable files.
The fixture uses only a local test trust anchor and authority; no Internet DNS
queries are needed. Recursive mode copies the production public root anchor;
its normal resolver traffic is limited to four declared cold/warm cases. It never
flushes production caches or uses the production control socket for mutation.
Production service, config, trust anchor, SSH and firewall fingerprints must stay
unchanged. Diagnostic observation is 20s, acceptance threshold 15s, warm 2s.
The declared 5s comparison must FAIL late replies; no warm retry follows failure.
Negative-control PASS means the expected missing reply was reproduced, not that
DNS service passed. See [the private acceptance procedure](../PHASE_B.md).
# Private identity candidate

`test_identity.py` checks exact rendered bytes, narrow reverse owner, input
rejection and missing/wrong PTR failure. `local_runtime.py` tests real UDP/TCP
identity, unrelated reverse with/without the mapping, approved loopback and
unauthorized A/PTR refusal under enforced AppArmor. Actual Windows/Tailscale
identity/display remains NOT TESTED / PENDING LIVE ACCEPTANCE.

`test_confirmation.py` rejects incomplete/failed/late receipts, wrong PTR,
missing cache/ACL evidence and boot/config/process drift. The actual shell
transaction is tested by `private_transaction_lab.py` using private mounts,
strict OS/service shims and synthetic receipts; it never restarts production.
`timer_guard_lab.py` tests harmless independent timer readiness; the existing
`service_rollback_lab.sh` separately tests real180s file restoration.
See [POST_BOOT_REVIEW.md](../POST_BOOT_REVIEW.md) for commands and limitations.

## Android private candidate

See [Android setup and recovery](../ANDROID_DNS.md). Both client ACLs are
covered by `tests/two_client_runtime.py` in a local network namespace using
synthetic exact source addresses and a signed local authority. Run as root
on an isolated Linux test host; CI requires `--require-apparmor`. No live
phone, Tailscale tunnel or public recursion is certified by this test.
