# Gate A review reconciled — user-provided live evidence

The owner has completed the stated read-only Oracle checks. This review accepts
them as **USER-PROVIDED LIVE EVIDENCE**, not Codex-executed observations. Exact
observation timestamps/raw command transcripts were not supplied here. The
findings are time-specific; no new Oracle access occurred in this task.

| Subject | Owner observation | Review conclusion / limit |
|---|---|---|
| Host | vynalthai-dns; aarch64; kernel7.0.0-1013-oracle; boot06c41b28-e22e-4540-8bd7-61b91fcaf465 | Matches historical identity, not a fresh approved baseline |
| Service | Unbound/tailscaled active; PID984; NRestarts0; Unbound enforcing | Positive owner evidence; new ARM/AppArmor candidate test still required |
| DNS | UDP/TCP127.0.0.1/[::1]:53; no100.95.65.20 listener; no observed public Unbound listener | Private service remains undeployed; listener absence explains service unavailability at that observation, not every timeout's packet cause |
| Local query | vyncuslim.com A NOERROR;104.18.16.55/104.18.17.55;174ms | Successful owner probe; addresses are observed, not test constants |
| Syntax/main hash | checkconf no errors;8808b474175ff8eeebecbf407f9091fd73f65c4a43a6ee212e8ae2d9f80778f8 | Main file matches; complete effective includes/anchor/runtime must still be reviewed |
| Network | ts-input accepts tailscale0; SSH22 listens | Not proof of end-to-end UDP/TCP53, complete host/OCI ingress or every failure path |
| Windows SSH | Authenticated ubuntu from100.85.132.14 to100.95.65.20:22, hostname correct, strict host-key checking | Authorized authentication path demonstrated by owner; future recovery under failures not guaranteed |
| Serial recovery | Existing console workflow available | No new console/resource/account operation needed or authorized here |
| Maintenance | apt-daily/upgrade inactive; timers scheduled; NTP=yes; reboot=no;~41GB free | Favorable historical sample, not idle-lock/schedule readiness at a future window |
| Units/recovery | No loaded vynalth-* units/active timers; scopes not-found/inactive; production timer/service not-found/inactive; pending recovery directory absent | No matching active protection observed; not an exhaustive dependency/process audit |

Owner firewall fingerprint:
`589768c435cd62bf0328818932c6a879371fed739fdd1ddbef0064ef7398fae4`.
The exact pipeline/normalization was not supplied. It must not be compared as
equivalent to historical `ab2fe6d9...` or labeled an incident merely because the
digests differ. A later approved capture uses the exact current script method:
`nft --stateless list ruleset`, LC_ALL=C, stripped output, UTF-8 SHA256. Preserve
raw policies and review differences using the same method, never overwrite a
baseline to hide drift. No OCI Security List/NSG proof is inferred.

## Retained artifacts: no cleanup authorized

- `/var/lib/unbound/vynalth-dev.PMaPSc`, approximately976KB.
- `/tmp/vynalth-final-rollback-82fcb9.py`.
- `/tmp/vynalth-cleanup-82fcb9.py`.
- `/tmp/vynalth-identity-dev-82fcb9.tar.gz`.
- `/var/lib/vynalth-dns/rolled-back-1791611257`: historical recovery backup,
  **must be preserved**, excluded from any lab cleanup.

Absence of matching unit/process names does not prove every open file/mount,
descendant or dependency is gone. Previous boundary deviation remains acknowledged
in LIVE_VM_IMPACT.md. Disposition requires an itemized separately authorized
review/cleanup decision; no files or units were changed on Oracle here.

## Gate status

Gate A evidence reconciliation is **COMPLETE with stated limitations**; it is
not deployment approval. Remaining production properties include exact effective
configuration/anchor state, comparable full management policies, residual
dependencies, complete OCI/private DNS path, current maintenance/locks and fresh
two-sample baseline. Original15s bogus-DNSSEC timeout exact cause remains unresolved.
Current repository state and local test receipts are independently verified in
VALIDATION.md. Next: GATE_C_REVIEW.md and FRESH_BASELINE_APPROVAL.md; no automatic
transition to production testing, staging or deployment.
