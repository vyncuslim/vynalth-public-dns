# Observability and alerts

`sudo python3 scripts/metrics.py` emits JSON with Unbound counters, cache hit
ratio, DNS rcodes, recursion timeouts (where provided by installed version),
memory, load and service restarts. Never emits query names/client histories.
Run locally every 60 seconds using an approved collector; do not expose the
control socket or metrics dashboard publicly. No paid collector is provisioned.

Compute counter deltas between samples; detect reset on restart. Alert on:
- failed low-volume localhost UDP/TCP health probe for 2 samples;
- any service restart count increase or systemd failed state;
- SERVFAIL delta >5% with at least 20 queries over five minutes;
- increasing requestlist timeout/exceeded counters;
- RAM available <15%, load >CPU count for ten minutes;
- security update failures, SSH authentication failures and unexpected ACL changes;
- missing metric heartbeat >3 minutes and any actual charge above RM0 policy.

Collect service journal errors and `journalctl -u ssh`, without enabling DNS
query logs. Configure verified alert destination and transport manually; this
release does not send emails or provision paid OCI alarms. Test delivery and
loss-of-collector alerts before Phase D. Cost analysis/alerts must cover the
whole tenancy and Cloudflare bill, not just the VM compartment.

Health probes must use known public DNSSEC domains only at low frequency, plus
local deterministic fixtures. SERVFAIL rates can be genuine upstream DNSSEC
failure; diagnose before changing validation. No guaranteed uptime is claimed.
