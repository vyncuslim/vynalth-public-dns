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

Not executed: Terraform plan against real OCI identifiers, apply, OCI inventory/
capacity/pricing APIs, cloud-init boot, live systemd deployment/rollback drill,
real root/TLD/authoritative recursion acceptance, real SSH key authentication,
live egress outage, alert delivery, restore/failover and Spectrum IPv4/IPv6.
These remain deployment/production gates, not inferred passes.

GitHub billing issue must be resolved by the account owner; no billing settings,
subscription or spending limits were changed. Do not weaken CI or remove tests
to disguise the unavailable runner.
