# Controlled DNSSEC investigation receipts

Recorded on the existing authorized Oracle ARM64 VM on 2026-10-10. These JSON
files preserve complete per-query diagnostics and intentional failures. They are
time-bound observations, not a benchmark or availability guarantee. Only named
test domains/local signed fixtures were queried; no user browsing history.

`production_before`/`production_after` compare each isolated experiment group.
Normal RFC5011 anchor maintenance can change its hash between groups; no operator
anchor modification occurred. `execution_limits` in the final fixture receipt
records actual cgroup settings; earlier scopes used the same declared caps but
did not record those fields. Earlier experiments predate the final rendered
config hash and explicitly varied only its discard window. The final reviewed
config tests used no window override. See ../../VALIDATION.md for interpretation
and ../../tests/README.md for reproducible commands. Never call a negative control
or intentional latency failure a DNS acceptance pass.
