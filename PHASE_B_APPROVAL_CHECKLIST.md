# Next Phase B approval checklist: no authorization granted

This handoff addresses [comment6098859695](https://github.com/vyncuslim/vynalth-public-dns/pull/1#issuecomment-6098859695).
Keep PR1 Draft and Issue2 open. No Oracle access/deployment is performed by this
documentation update. Phone failure/control evidence is user-reported, not a
new Codex measurement. Do not repeat private dig probes while the listener is
not enabled or change Android Private DNS/blanket tailnet DNS Override.

## Sequential gates (separate approvals, no implied continuation)

| Gate | Reviewable scope / exit evidence | Current state |
|---|---|---|
| A | Approve existing serial-console read-only impact/status audit; optionally extended baseline and Windows read-only recovery scope in ORACLE_READ_ONLY_AUDIT.md | PENDING approval; not executed |
| B | Review exact retained paths/units/dependencies and recovery exclusions; authorize itemized cleanup only if needed | UNKNOWN need; no cleanup approved |
| C | Approve exact environment and effects of current ARM/AppArmor/real180s timer readiness validation, preferring a separate lab; live host test files/scopes/transfers require explicit scope | NOT TESTED on current ARM; local evidence is insufficient |
| D | Review final full commit, config, complete bundle, exact diff, fresh pinned baseline and procedure; separately authorize staging and one-shot service-only Windows transaction | BLOCKED; no fresh baseline or deployment approval |
| E | After protected Windows confirmation, explicitly authorize phone DNS-only acceptance, strictly<45s; complete PASS required for mobile release | PENDING LIVE ACCEPTANCE |
| F | After both devices and every affected client are healthy/authorized, separately consider phone/system-wide or tailnet DNS settings with recorded restoration plan | BLOCKED; no DNS-admin approval |

Read-only approval never authorizes cleanup/tests/staging. A harness described as
isolated is still a live-host write/test if run on Oracle. Prior laboratory
deviation/residual impact remains unresolved in LIVE_VM_IMPACT.md. Gate C must
specify created files, units, CPU/RAM/FD caps, network traffic, cleanup ownership
and evidence handling; never cancel an existing production protection timer.
No production restart is implicit in readiness validation. If a reboot is needed,
create a separate maintenance/recovery approval; invalidate the old baseline.

## Exact candidate identity and fresh baseline gate

Code candidate reviewed before this docs update:
`2a2aa580a2f85684c7072c35b2fdf38c5422d71e`.
The final documentation commit will have a different SHA; resolve the actual
branch HEAD and review that full SHA before approval. No old approval carries over.

Unchanged Unbound configuration SHA256:
`d6db3048b2c8dce15bf3ebe50be89ce12680345f48ce72eb466b715d29317634`.
Unchanged21-file service manifest SHA256:
`d9e34e90e734fb0ca07ddf3a3e415bc2f35df28b10565d5a9af678b4068dd965`.

The existing baseline SHA256
`cbb29c44eebd8d3423dffffe99009c1f3cbaa2e5325439b81a7a73a3aa84820b`
is historical/review-only, **not a fresh approved baseline**. Gate A first
establishes state; an explicitly scoped later capture/staging step can collect
two equal fingerprints60s apart using the reviewed readiness procedure. Review
the raw bytes, sample times/boot, actual configs/drop-ins/policies and failures;
pin a new baseline hash and regenerate affected manifests/report as needed.
Any changed baseline bundle produces a new exact candidate for human review.
Never silently refresh it during deployment or substitute a PID to pass drift.

Check off all before requesting Gate D approval:

- [ ] Gate A findings reviewed; retained lab activity/dependencies resolved or
  explicitly assessed safe without cleanup. No unknown active transaction.
- [ ] Current Windows private SSH and independent console recovery verified;
  retain SSH session. Host keys/private keys remain protected.
- [ ] Fresh exact baseline approved; AppArmor enforcing, original listeners,
  trust-anchor/root-hints/config syntax and management policies verified.
- [ ] Maintenance idle, package locks clear, known schedule>15min away, NTP
  synchronized, reboot flag clear; no update-policy alteration.
- [ ] Actual current ARM/AppArmor and independent180s rollback readiness
  evidence reviewed; backup restores original configuration/systemd settings.
- [ ] Final clean GitHub/Windows/VM commits match; source staging separately
  authorized, all config/baseline/service/review checksums match Git bytes.
- [ ] Existing host/Tailscale/OCI ingress policy permits intended private DNS
  without modification. If not, STOP and propose separate networking review;
  service-only authorization cannot fix a blocked packet path.
- [ ] Exact reviewed active-config/systemd diff contains only private listener,
  both /32 DNS ACLs and reviewed service limits; no wildcard/public listener.
- [ ] Windows protected17-query/cold-warm/flags/cache/ACL procedure retained;
  Android and manual queries idle during first-use checks.
- [ ] Global controller starts T0 before all command/network/verification work;
  deploy, receipt transfers and confirmation share strictly<140s. Staging or
  a60s baseline capture outside it is separately approved preparation, never
  permission to reset T0 after the controller starts.

## Future Gate D approval text (template only, NOT ready to execute)

> Approve one service-only private trial tied to full commit `<REVIEWED_SHA>`,
> config SHA256 `d6db3048b2c8dce15bf3ebe50be89ce12680345f48ce72eb466b715d29317634`,
> service manifest `<FINAL_BUNDLE_SHA256>`, fresh baseline `<APPROVED_BASELINE_SHA256>`
> and reviewed evidence `<AUDIT/READINESS_REFERENCES>`. Permit only the reviewed
> Unbound config/systemd limits and one restart, with independent180s rollback
> armed and verified before writes. Retain existing SSH and unchanged management
> networking. Use the reviewed global controller and complete Windows acceptance.
> Confirm only with full PASS strictly before140s total, using the existing
> before120s submission/confirmation reserve. No late/forced/retried confirmation.

Any failure, timeout, missing evidence, hash/baseline drift, SSH interruption,
unexpected service/policy change or exhausted budget prevents confirmation and
requires service-only rollback under the approved transaction. Never stop the
timer early. Lost confirmation response is UNKNOWN: no automatic retry; obtain
scoped status review. Record restored state before claiming rollback success.
No `install.sh`, firewall/SSH/Tailscale/OCI/Spectrum/public DNS, OS upgrade/reboot,
Terraform apply/destroy, paid resource or PR merge authorization is included.

## Gate E and release

Use the existing mobile controller only after Gate E authorization and Windows
confirmation. It has ten one-shot queries and a32s summed query cap with a45s
controller ceiling; the approved gate must finish **strictly below45s**, including
command/receipt completion, or be recorded FAIL. Do not relax that ceiling, retry
or run a second deployment/confirmation. Check UDP/TCP A/AAAA, exact PTR,
valid NOERROR+AD and bogus SERVFAIL without AD; timeout is not DNSSEC rejection.
Cached results do not prove a cold-cache scenario or system-wide DNS use.
Mobile failure blocks release; after Windows confirmation, any service recovery
needs a separate decision. See ANDROID_DNS.md for preparation/restoration.

Current blockers: no fresh live audit/recovery/baseline, unknown lab residues,
current ARM/AppArmor/real timer validation, unstaged/unverified VM source and
private packet path, Windows/phone acceptance, CI account billing lock. Local
two-client simulation PASS does not clear these gates. No resources/cost changes;
RM0 target and existing invoice/free eligibility remain unverified.
