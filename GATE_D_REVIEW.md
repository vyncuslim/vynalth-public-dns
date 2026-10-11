# Gate D pre-deployment review — no production authorization

Starting actual local/origin HEAD:6f7a15ad51878dc3b0e061df4f042aed2634a390.
Native ARM and retained x86 CI passed at that SHA. Evidence is reconciled with
ARM_CI_RESULTS.md and archived artifacts. No separate physical ARM lab request,
Oracle access or operation is part of this work.

| Requirement | Completed evidence | Scope limit |
|---|---|---|
| Native architecture/OS | PASS aarch64/Ubuntu24.04/systemd hosted runner | Not Oracle present state |
| Unbound/AppArmor | PASS1.19.2-1ubuntu3.10; actual unbound(enforce) | Production UID/path permissions not proven |
| Real cgroup/service restore | PASS256MiB/32tasks/512FD→384MiB/64/1024→original, distinct real PIDs/queries | Isolated root fixture, not Oracle/SSH recovery |
| DNSSEC/ACL/PTR | PASS signed/bogus/CD/negative responses, both synthetic /32 sources and refusals/PTR | Real devices/VPN and incident cause unverified |
| Independent180s timers | PASS unique disposable timers; killed-controller restore/confirmed-state no-op | Timer service operations remain labeled shims |
| Global<140s/receipt guards | PASS unit/contracts, no late/missing/partial PASS or uncertain retry | Real Windows/network timing still pending |
| Retained x86/ARM CI | PASS push/PR at6f7a15a; earlier receipts archived | Does not authorize later commits or deployment |

Earlier billing lock no longer prevented these runs; cause unknown, no billing
change.68 tests passed on tested source. Existing config/listeners/ACL/PTR/security
settings are unchanged. New capture-output safety fix is tested separately.

## STOP/PASS pre-trial review

| Topic | Existing evidence | Required before authorization |
|---|---|---|
| Residue | Owner PMaPSc~976KB,3 /tmp files; matching scopes/timers inactive;1791611257 backup preserved | Dependencies/impact assessed safe to retain, or separately approved disposition; absence of names alone insufficient; no cleanup now |
| SSH recovery | Owner Windows private authentication/strict pin; console workflow available | Fresh source/host/session proof and reviewed independent recovery; no universal failure recovery guarantee or public SSH removal |
| Firewall | Partial ts-input accept, complete host/OCI policy unverified | Same-method policy/SSH review and OCI/private path evidence under separate read scope;589768... normalization unknown, not automatically an incident |
| Root trust | Historical validation; current anchor state unknown | Captured hints/anchor/status/trusted keys/refresh reviewed; equal hashes alone are not health; no anchor/cache mutation |
| Production timeout | Owner bogus UDP15s TIMEOUT, not SERVFAIL | Unresolved pre-trial blocker; separately approved effective discard/validator/path/cache/limit diagnostics and explicit assessment, not silently waived |
| Source/baseline | VM checkout unverified; oldcbb29c44 baseline historical | R inspection→S exact staging→C new capture60s apart→human pinning/new hashes; no PID/hash substitution |
| UID/paths/private listener | Root lab identity/synthetic aliases | Production user/control/AppArmor paths reviewed; actual private path acceptance belongs to a separately approved bounded trial |

STOP for missing evidence, uncertainty, changed boot/PID/config/policy needing
review, inactive recovery, invalid anchor, active maintenance/rollback or unknown
residue dependencies. No fingerprint/document automatically approves readiness.
The original timeout is not fixed by CI proof. Inherently post-listener checks
may run only after prerequisite blockers are reviewed and explicitly accepted
under the exact protected-trial authorization; no extra unbudgeted transaction.

## Minimal next permission: R only

See FRESH_BASELINE_APPROVAL.md: one retained existing pinned Windows private SSH
session, listed identity/source/repo/service/listener/hash/pending-protection
reads, stdout recorded locally. No remote write/staging/collector/DNS probe/test,
cleanup/timer/restart/network action. Read-only SSH/sudo can leave routine audit
records; no keys/passwords are read or disclosed.

After R, request S with actual checkout state and exact commit; after S, request
C with one exact new evidence filename and two samples60s apart. Capture rejects
overwrite/missing parent, uses existing Python stdlib and keeps deployment_ready
false. Broader root/policy/timeout diagnostics are separate, not silently in R.

Future D binds full commit/config/service/fresh baseline/diff, preserves management,
arms180s rollback before writes and confirms only complete Windows PASS strictly
before140s globally including all commands/network/transfer time. Android<45s
after confirmation requires its own approval. No production access/deploy/merge now.

Unchanged configuration SHA256: `d6db3048b2c8dce15bf3ebe50be89ce12680345f48ce72eb466b715d29317634`.
New21-file service manifest SHA256: `29b84c8d37486b8882d5c1400cd91d47d6a35e25e3eef45851194774d4794e1f`.
It changed only because capture-output safety code changed; no baseline approved.
