# Approved private trial: preflight abort

The approved bundle was `61a9ad8c342717d10974b6de1e274a0e180d09e6`, configuration
SHA256 `d2e4c258f750db0e3b42a32b12bc690ecf43743500d90e099ee2628a022c57c7`.
No deployment started. The service PID changed during existing automatic host
maintenance; the required equality gate stopped the operation. See VALIDATION.md.

The transaction JSON preserves the original failure and has additional labelled
status/reason fields derived from the separate read-only diagnosis. Initial and
final receipts intentionally have different PIDs; they must not be overwritten
or treated as a passing stable baseline. No DNS acceptance receipt exists because
the acceptance controller was never executed. No query/latency results should be
inferred from the final zero-query cache counters. A fresh trial needs review and
authorization; these files do not authorize restarting, rebooting or retrying.
