# Security policy

No public recursion in development. Renderer allows individual hosts only;
default Unbound ACL refuses all other clients. Host policy drops ingress except
loopback, established replies, ICMP and named SSH/DNS test clients. Existing
firewalls are never disabled or globally flushed. Packet rules and Unbound IP
limits bound development traffic; they are not proof of public abuse resistance.
UDP source IP is spoofable. Before public launch require validated edge abuse
controls, DNS cookies or an equivalent reviewed strategy, real client identity,
response association controls, sustained local abuse tests and operational response.

DNSSEC, QNAME minimisation, minimal replies, ANY denial, 1232-byte UDP cap,
TCP fallback, bounded caches/connections and rebinding filters are enforced in
configuration. SERVFAIL is retained for bogus DNSSEC, never converted to plaintext
or forwarded to a permissive upstream. RFC1918/link-local/ULA answers are filtered.
Root hints and anchors are from signed Ubuntu package distribution, not an
unverified arbitrary download. Preserve root.key state across deployments.

Administrative controls: key-only SSH, root/password/interactive login disabled,
Ubuntu user only, no X11/TCP forwarding and source-restricted ingress. The control
socket is local, protected by filesystem permissions. No web dashboard. Check
effective `sshd -T` because image drop-ins may override desired configuration.

Automatic security updates are configured without automatic reboots. Schedule
patch/reboot drills with rollback and availability checks. Logs default to error
only, without individual query/reply logs; journal retention seven days/64 MB.
Configure retention lower if required and verify actual journald drop-ins.

Terraform state and discovery artifacts can contain operational identifiers:
keep ignored and access-restricted. Never commit private keys, API tokens or
OCI configuration. Gitignore is not a secret scanner. Run repository secret
inspection before pushes and rotate exposed credentials rather than deleting logs.

Production gates: contract coverage, billing, identity preservation, security
review, approved abuse simulation, monitoring alerts, tested backup/recovery,
second origin/failover, IPv4/IPv6 acceptance and explicit public-access approval.
All remain unmet until evidence is recorded. Report vulnerabilities privately to
the repository owner; never post credentials or browsing histories in issues.
