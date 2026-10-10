# Verified native ARM Gate C receipts — 2026-10-11 Malaysia time

Both standard ubuntu-24.04-arm jobs for code commit
`81c8cf8bc9ec42f7c730b7b3d53cf9bb5cbac4b3` completed SUCCESS:
[push run38080431432](https://github.com/vyncuslim/vynalth-public-dns/actions/runs/38080431432),
[PR run38080434109](https://github.com/vyncuslim/vynalth-public-dns/actions/runs/38080434109).
Raw artifacts are preserved under plans/arm-ci/<run-id>; each downloaded evidence
SHA256 was checked against its included manifest. Retrieval JSON records archive
hash, tested commit, event, job steps and public run URL. PR commit.txt may be a
GitHub synthetic merge SHA; run head SHA and source integrity checks are retained.

| Requirement | Actual push-run evidence | Status |
|---|---|---|
| Architecture/OS | aarch64; Ubuntu24.04; systemd PID1 | PASS native, no emulation |
| Packages | Unbound1.19.2-1ubuntu3.10; systemd255.4-1ubuntu8.17; AppArmor4.0.1really4.0.1-0ubuntu0.24.04.8 | PASS exact versions recorded |
| Kernel/profile | AppArmor enabled; each fixture and actual daemon unbound(enforce) | PASS; no disabling/relaxation |
| DNS | UDP/TCP A/AAAA, valid/bogus/CD DNSSEC, PTR, default-deny and both synthetic /32 clients | PASS isolated namespaces |
| Negative DNS |54 signed/unsigned/compact/wildcard/CNAME/empty-node cases; bogus negative proof and cache checks | PASS |
| Actual service/cgroup | PID3162 original256MiB/32tasks/512FD → PID3253 candidate384MiB/64/1024 → PID3360 restored256MiB/32/512 | PASS actual kernel/unit/proc values and queries |
| Real timer | configured180s; killed-controller restore completed180.774371s; confirmed-state no-op180.663318s | PASS real unique timers; timer service actions still shims |
| Guard/file recovery |9 actual shell guard cases; snapshot restoration/failure retention | PASS stated shim/private-file scope |
| Unit/syntax/hash |68 tests; compilation/Shellcheck/source and artifact checksums | PASS native job |

Actual service restore uses a strict unit-name adapter to the real manager and
actual Unbound. It proves isolated configuration/limit recovery, not production
Oracle, Tailscale/SSH continuity, real device acceptance or the full live global
transaction. Local-data cgroup recovery is not itself DNSSEC proof; separate
signed-authority enforcing fixtures supply that evidence. No VPN/public DNS/
Oracle/resource/billing modifications occurred. Private listeners are synthetic
inside namespaces, not a new live Vynalth service.

## Billing and retained x86 job

The earlier bcd873c runs never started due to the reported account billing lock.
The new81c8cf8 runs were allocated and executed. Codex did not change billing,
purchase anything or determine why scheduling resumed. Public standard-runner
eligibility remains documented in ARM_HOSTED_CI.md; account status is not inferred
from a paid transaction.

Existing x86 validate tests were retained. Their first real run failed at
isolated_dnssec.py because sshd -T needed /run/sshd. Commit
`f4a6f15f47ed4baf2169b831f118606a26e7ce26` adds only a root0755 runtime directory
on the disposable runner, no SSH policy/service change or test removal. Its runs
must be assessed separately; native success is not a claim that all CI passed.
No retries after uncertain production confirmation are introduced.

## Remaining production gates

Native ARM/enforcing/isolated actual cgroup/service and disposable timer evidence
now exists. Production recovery, owner residue disposition, fresh approved
two-sample baseline, exact staging/commit/bundle approval, private packet path,
unresolved historical production DNSSEC timeout, protected Windows acceptance
and separate post-confirmation Android<45s acceptance remain PENDING. No deployment
or PR merge is authorized by a green ARM job.180s rollback/<140s global safeguards
and unchanged configuration/service hashes remain intact.
