# Test matrix and boundaries

CI/unit checks are not production acceptance. No public load/attack tests.
`local_runtime.py` starts a high-port loopback process and terminates it, without
editing the host service or firewall. `acceptance.py` sends at most seven ordinary
queries to an explicitly authorized resolver; root/authoritative queries are the
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
