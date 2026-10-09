# Vynalth AI Public DNS

Independent Unbound recursion on Ubuntu 24.04, targeting OCI Singapore.
**Development policy only. Public service and Spectrum integration remain blocked.**
No cloud resources, live DNS records, or Spectrum applications are created by CI.

## Quick start (no cloud resources)

```sh
python3 -m pip install -r requirements-test.txt
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/render.py config.example.json
# Ubuntu 24.04 with Unbound and dns-root-data installed:
python3 tests/local_runtime.py
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

This is not yet a replacement for 1.1.1.1: no verified static edge IP entitlement,
SLA, failover, DDoS guarantee or production acceptance. Conventional OS DNS clients
need stable IP addresses; `dns.vynalthai.com` alone is insufficient.
