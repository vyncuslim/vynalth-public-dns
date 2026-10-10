# Negative DNS and DNSSEC investigation — 2026-10-11, Malaysia time

Development/isolated local testing only. No Oracle SSH/serial/files/processes,
cleanup, service/timer/network/DNS changes or Phase B deployment. PR1 stays Draft.
Starting local/origin HEAD matched c289395c4457f6fe1ebb710fd682f81a73006324.
[Owner investigation](https://github.com/vyncuslim/vynalth-public-dns/pull/1#issuecomment-6099493372)
is historical user-provided evidence, not a Codex live observation.

## User-observed production results

Baseline main configuration SHA256:
`8808b474175ff8eeebecbf407f9091fd73f65c4a43a6ee212e8ae2d9f80778f8`.
User reports PID984, localhost127.0.0.1/[::1] listeners, no private candidate
deployment; Gate A reported ts-input accepts tailscale0, not proven DNS reachability.

| Exact A query | User-reported RCODE / ANSWER | Authority / flags |
|---|---|---|
| test-nx-20261010.example.com. | NOERROR /0 | example.com SOA; AD=true |
| test-nx-20261010.cloudflare.com. | NOERROR /0 | cloudflare.com SOA; AD=true |
| test-nx-20261010.github.com. | NOERROR /0 | github.com AWS SOA; AD=false |
| test-nx-20261010.invalid. | NXDOMAIN /0 | invalid SOA; AA=true, AD=false |
| dnssec-failed.org., UDP,15s one try | TIMEOUT /no response | **FAIL**, not SERVFAIL or validation PASS |

NOERROR with no requested RRset and SOA is NODATA-style. It is not proof that the
name exists, that it does not exist, or that Unbound changed a valid RCODE. CNAME
can remain in the ANSWER while its terminal target has no requested type. SOA
supports negative caching; AD describes validation, AA authority, CD diagnostic
checking bypass. Missing AD alone is not an invalid signature diagnosis.
[RFC2308](https://www.rfc-editor.org/rfc/rfc2308.html),
[RFC4592](https://www.rfc-editor.org/rfc/rfc4592.html).

## Actual external comparisons: limited, not Oracle

The local Windows host sent24 ordinary one-shot requests per bounded probe run,
two runs, no load testing or retries. The second run sampled one NS1 and one AWS
server for github as well as two Cloudflare authorities per other zone. Raw
UTC times, IPs, NS discovery, DO/CD, codes, flags and proof RRsets are retained in
plans/investigation/external-negative-providers.json (first sampling also retained).
1.1.1.1 is a comparison/discovery target only; no Unbound forwarding was added.
NS discovery through that recursor is not an independent root-to-delegation audit.

Both sampled Cloudflare authorities returned NOERROR/NODATA+SOA for each exact
example.com/cloudflare.com name, with signed NSEC including **NXNAME** and RRSIG.
The public recursor returned the same shape with AD. This is consistent with
[RFC9824 Compact Denial](https://www.rfc-editor.org/rfc/rfc9824.html): a provider
can send authenticated NOERROR denial for a nonexistent name. It is not evidence
of a wildcard-positive answer or an Unbound RCODE defect. Preserve the actual
code; never synthesize NXDOMAIN from an empty ANSWER.

For github, the sampled NS1 and AWS authorities also returned NOERROR, no A,
and their own SOAs. SOA/provider differences are recorded, not normalized away.
The comparison recursor returned NODATA without AD. This does not prove the
entire github delegation's DNSSEC status; authoritative AD assertions are not
equivalent to a trusted recursive validation result. No zone transfer or full
wildcard/empty-node enumeration of third-party zones was performed. Their exact
internal name-existence mechanism remains UNKNOWN. The observed wire shape is
supported by the sampled authorities, not a confirmed resolver defect.

External dnssec-failed.org: comparison UDP/TCP returned SERVFAIL without AD;
CD returned NOERROR without AD. It shows availability from this local path at
that time, not Oracle's root/authority reachability or exact timeout cause.

## Deterministic real Unbound regression

Local WSL x86_64 cached Unbound1.19.2, network namespace with loopback only and
no default route. Fresh ephemeral authorities and pinned local ECDSA trust
anchors; no public traffic. Original candidate directives remain except explicit
test adaptations: high loopback port/runtime files, test identity, local anchors
instead of root auto-anchor, and stub zones pointing only to fixtures. Unsigned
fixture alone is declared insecure to model an unsigned delegation; signed zones
still require actual cryptographic validation. This does not test real parent DS
absence. No val-permissive mode or unlimited discard timeout is enabled.

**PASS:54 cases**, UDP/TCP across traditional signed NSEC, unsigned data, and
signed Compact Denial fixtures: NXDOMAIN, existing AAAA-only name queried for A,
A-only name queried for AAAA, TYPE65280 NODATA, empty nonterminal, positive
wildcard, wildcard NODATA, wildcard CNAME/address resolution, CNAME to absent
target. Codes, terminal RRsets, SOA/TTL, AD/CD/AA and NSEC/RRSIG are checked.
Signed negative replies have AD; unsigned negatives do not. The fixture supplies
complete NSEC proofs, not a reproduction of a provider's internal implementation.

**PASS:6 measured negative-cache reuses** with no new authority request. Signed
traditional cases can increment aggressive-NSEC synthesis counters rather than
total.num.cachehits; both are explicitly measured. SOA negative TTL is bounded
by MINIMUM30. Expiry after30s is NOT TESTED. Authoritative UDP truncation triggered
actual upstream TCP fallback (18 TCP authority requests in this run).
Tests are paced below the preserved20qps client limit; an early unpaced harness
hit that protection, and an initial cache assertion omitted aggressive counters.
Those test-harness errors were corrected without changing resolver security.

Built-in `.invalid` returns NXDOMAIN, AA=true, AD=false with invalid SOA. That is
local special-use behavior, not a validated root denial;
[RFC6761](https://www.rfc-editor.org/rfc/rfc6761.html) calls for local negative
responses. This confirms an **acceptance defect**: the old case required AD for
that local response. The same query/count/5s budget now expects NXDOMAIN without
requiring AD; real valid signed-domain and root-DNSKEY AD checks remain mandatory.

Second confirmed **acceptance defect**: an A/AAAA positive check accepted a
nonempty ANSWER containing only CNAME and no requested address RRset. It now
requires the requested type. Explicit `expected_nodata=True` supports negative
diagnostics with NOERROR+SOA, preserving CNAME and never rewriting RCODE. Default
positive checks remain strict. Added diagnostics include AA/RA, full authority,
SOA negative TTL and descriptive wire shape. No production resolver defect was
invented or configuration modified to make tests pass.

## DNSSEC reply-age A/B

Original main-config bytes reconstructed from the captured diff match8808b474...
exactly. They only include `/etc/unbound/unbound.conf.d/*.conf`; they do not
contain all effective directives/trust-anchor/cache state. The complete current
production environment is **NOT RECONSTRUCTED**. The local package's minimal
default `unbound-checkconf -o discard-timeout` is1900; actual version/default
evidence is retained. This matrix changes only the candidate's reply-age value
between1900 and15000 with a controlled six-second first authority delay. Each
cell starts a fresh Unbound/authority; no client warm retry after cold failure.
Unbound's upstream requests (9–17 including keys/retries) are counted separately
from the exactly-one client transmission; counts do not identify every retry cause.

| Reply age | Cold UDP valid / bogus | Cold TCP valid / bogus |
|---|---|---|
|1900ms|TIMEOUT8.005110s /8.008865s; no response|EOF transport error6.029546s /6.050976s; no response|
|15000ms|NOERROR+AD6.087737s / SERVFAIL without AD6.036818s|NOERROR+AD6.021844s / SERVFAIL without AD6.042221s|

PASS: tampered signed-negative SOA/RRSIG UDP/TCP returns SERVFAIL without AD;
this uses a separate cold trust domain so previously valid NSEC cache cannot
answer instead of the faulty authority. Candidate warm valid/bogus queries PASS below2s; bogus CD diagnostics PASS
NOERROR+CD without AD. Legacy failed-cold warm validation is not attempted;
separately labeled CD diagnostics can answer but cannot turn failure into PASS.
A5s client deadline would reject these6s candidate replies. Client timeout,
server EOF, late response, SERVFAIL and NOERROR remain different outcomes.
The harness PASS means the expected A/B failure mechanism was reproduced;
the1900 client validation queries themselves remain **FAIL**.

**Confirmed:** finite reply-age expiration can discard a delayed validated result
in this package; the existing finite15000 proposal avoids it for this controlled
delay. **Probable contributor, not proven production cause:** inherited1900
reply-age interacting with cold validation/upstream retries. **Unresolved:**
the exact Oracle15s failure. No contemporaneous validation log/packet evidence
or complete current effective config was collected here. Connectivity, cache,
trust-anchor health, EDNS/fragmentation/TCP paths, authoritative loss and queue
pressure remain hypotheses. No public15000ms promotion or live fix is claimed.
[NLnet Labs DNSBomb release explanation](https://nlnetlabs.nl/news/2024/May/08/unbound-1.20.0-released/).

## Reproduction and next safe evidence

On an independent Linux lab with Unbound, dns-root-data, iproute2 and test Python
dependencies installed (never Oracle):

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
sudo /path/to/test-python tests/negative_runtime.py --require-apparmor --out artifacts/negative-runtime.json
sudo /path/to/test-python tests/two_client_runtime.py --require-apparmor --out artifacts/two-client-runtime.json
```

Strict AppArmor mode fails if enforcement is unavailable; don't disable it. The
local WSL kernel did not enforce AppArmor, so that item is **NOT TESTED**, not PASS.
External optional commands are documented in tests/external_negative_probe.py;
never run third-party probes in CI by default. Their success is not acceptance.

Before a new live test, separately approve read-only effective include/config
hashes, root hints/anchor status, `unbound-checkconf -o discard-timeout`, service
limits, current stats, maintenance/clock/recovery and bounded relevant journal
window. Do not clear caches, expose browsing logs or mutate the baseline. If cold
state is required, explicitly authorize a separate isolated ARM environment;
ordinary production queries cannot prove a fresh cache. A later approved low-
volume baseline comparison must specify UDP/TCP, CD, deadlines, exact query count,
stats/flags/authority and no retries; capturing packets/log changes needs its own
scope. Current production testing is **PENDING SEPARATE APPROVAL**.

Existing [audit](ORACLE_READ_ONLY_AUDIT.md) and
[sequential gates](PHASE_B_APPROVAL_CHECKLIST.md) remain mandatory. No new queries
are added to the protected Windows17-query/<140s transaction;180s rollback and
post-confirmation separately authorized Android<45s gate remain intact. Both
/32 ACLs, private listeners and PTR are unchanged and real isolated two-client
tests pass; neither Windows nor OPPO live acceptance is claimed. ARM/enforcing
AppArmor/current real180s timer, fresh approved baseline/recovery/residue impact,
VM staging/packet path and CI billing remain approval blockers.

Current unchanged configuration SHA256: `d6db3048b2c8dce15bf3ebe50be89ce12680345f48ce72eb466b715d29317634`.
Current21-file service manifest SHA256: `39d1d897e63bb87ff52195ce07ef77c219dff2def100e44249ae72071182ffc2`.
The service manifest changed because acceptance/confirmation code changed; configuration
bytes did not. Current61 Windows and61 local Linux unit tests PASS. Local
rollback4 variants plus no-snapshot no-op, full runtime, both-client runtime,
Shellcheck all scripts/tests and Python compilation PASS. CI has not been
executed locally; account billing status is reported separately on the PR.
