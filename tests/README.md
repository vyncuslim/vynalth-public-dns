# Test matrix and boundaries

CI/unit checks are not production acceptance. No public load/attack tests.
`local_runtime.py` starts a high-port loopback process and terminates it, without
editing the host service or firewall. `acceptance.py` sends at most seven ordinary
queries to an explicitly authorized resolver; root/authoritative queries are the
resolver's normal DNS operation, not attacks or benchmark load.

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
