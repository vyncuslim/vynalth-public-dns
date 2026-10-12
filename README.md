# Vynalth AI DNS

**Vynalth AI Secure Recursive DNS Resolver** â€” `dns.vynalthai.com`.
The private candidate includes single-owner PTR identity, DNSSEC and checked
rollback/confirmation gates. See [post-boot candidate review](POST_BOOT_REVIEW.md).
It has not been deployed; every live trial requires separate exact authorization.

Independent Unbound recursion on Ubuntu 24.04, targeting OCI Singapore.
**Development policy only. Public service and Spectrum integration remain blocked.**
No cloud resources, live DNS records, or Spectrum applications are created by CI.

## Quick start (no cloud resources)

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python scripts/render.py config.example.json
# Ubuntu 24.04 with Unbound and dns-root-data installed:
sudo .venv/bin/python tests/local_runtime.py --require-apparmor
```

The example listens on localhost, allows no external DNS clients and uses a
documentation-only SSH address. Replace it with your approved administrator host
before deploying. Renderer accepts only individual /32 or /128 clients and
rejects wildcard listeners. IPv6 needs an explicit opt-in and verified routing.

See [architecture](ARCHITECTURE.md), [security](SECURITY.md), [cost controls](COSTS.md),
[deployment commands](DEPLOYMENT.md), [rollback](ROLLBACK.md),
[test matrix](tests/README.md), [observability](OBSERVABILITY.md) and
[current discovery evidence](DISCOVERY.md).
See [validation evidence and unexecuted checks](VALIDATION.md).
The existing Oracle VM has a separately reviewed [Phase B private service plan](PHASE_B.md).
Its authorized private-service attempt was rolled back after a test timeout.
The DNSSEC reply-expiry correction and cold/warm diagnostics passed isolated
tests; the new private trial and all firewall changes need explicit approval. Use the
service-only procedure rather than the full installer on this Tailscale-managed VM.

This is not yet a replacement for 1.1.1.1: no verified static edge IP entitlement,
SLA, failover, DDoS guarantee or production acceptance. Conventional OS DNS clients
need stable IP addresses; `dns.vynalthai.com` alone is insufficient.

## Android private candidate

See [Android setup and recovery](ANDROID_DNS.md). Both client ACLs are
covered by `tests/two_client_runtime.py` in a local network namespace using
synthetic exact source addresses and a signed local authority. Run as root
on an isolated Linux test host; CI requires `--require-apparmor`. No live
phone, Tailscale tunnel or public recursion is certified by this test.
