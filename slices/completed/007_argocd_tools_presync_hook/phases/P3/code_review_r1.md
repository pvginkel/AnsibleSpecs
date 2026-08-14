# P3 — The PV reattach — code review r1

## Readiness

The phase meets its outcome and I found nothing that should block the merge. The bound P3 exists to
be reviewed on holds exactly as written: `claimed_by` matches on `status.phase == "Released"` **and**
`spec.claimRef.namespace` equal to the argument (`presync/reattach.py:38-43`), the argument is
`args.namespace` handed straight through with nothing derived from it (`presync/cli.py:48`), and the
patch nulls `uid`/`resourceVersion` while keeping the claim's name and namespace
(`presync/reattach.py:30`) — so the volume stays reserved for the same PVC rather than being offered
to the cluster at large. The negatives that matter are all asserted rather than assumed: a
prefix-sharing sibling namespace, another app's `Released` volume, an unclaimed volume and the run's
own `Bound` volume are each present in the fixture and each unmatched
(`tests/test_reattach.py:19-27`), the wire test proves exactly one PATCH with exactly that body
(`tests/test_reattach.py:79-91`), and a failed apply is shown to reach the apiserver not at all
(`tests/test_cli.py:147-156`). Reaching the API over stdlib `urllib`+`ssl` rather than kubectl
satisfies D31, TLS is verified against the ServiceAccount's own CA with an unknown CA refused before
a byte is sent (`tests/test_reattach.py:110-118`), the token is re-read per request against kubelet's
in-place rotation (`presync/kube.py:56`, asserted at `tests/test_reattach.py:93-101`), and a 403 —
what a run without slice 009's PV RBAC gets — fails the run rather than letting the sync proceed onto
empty volumes.

I probed the two places this could have been theatre. The `VERIFY_X509_STRICT` relaxation
(`presync/kube.py:38`) is load-bearing and genuinely covered: the gate's interpreter is Python 3.13.7
with the flag on by default, the test double's CA is generated without a `keyUsage` extension exactly
as the estate's is (confirmed by inspecting a CA minted the same way), and deleting that one line
makes 8 of the 52 tests fail — including the end-to-end `python -m presync` exit-code test. The
relaxation's scope is described accurately: chain, expiry, hostname and unknown-CA rejection all
still bite. I also checked the apply→reattach ordering against what the estate's Terraform actually
declares, since a deadlock there would have been fatal: `terraform-modules/static-zfs-pv` and
`static-rbd-pv` manage the `Retain` PV itself with a `claim_ref` carrying only name and namespace
(`/work/HelmCharts/terraform-modules/static-zfs-pv/main.tf:94-132`) and no PVC, so the apply neither
waits on a binding nor diffs against the nulled fields — the ordering is safe for the real workloads.
Per the dispatch I took the green gate as given and did not re-run the suite except for the mutation
above. The live prd half of V06 is the done-record's claim and the test phase's to re-check; I could
not independently confirm the fixture's cleanup because the read-only kubeconfig cannot list PVs at
cluster scope, which incidentally corroborates the executor's own card about the mounted kubeconfigs.
The three findings below are all advisory — one coverage gap that costs nothing today, and two
places where words are wrong.

## Findings

### F1 — No test exercises more than one matching volume, and the estate's normal case has three

**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

`reattach()` loops over every name `claimed_by` returns (`presync/reattach.py:46-50`), but no fixture
in the suite ever produces more than one match: `tests/test_reattach.py:19-27` has exactly one
`Released` volume in `NAMESPACE`, and `tests/test_cli.py:65-72` exactly one in `app-prd`. An
implementation that patched only the first match — `names[:1]`, an early `return`, a `next()` —
passes all 52 tests, and the live prd proof also had a single matching volume, so nothing in the
phase's evidence distinguishes "patches every match" from "patches one match".

The case that makes this concrete rather than theoretical is the estate's most storage-heavy app:
`/work/HelmCharts/configs/prd/postgres-pas/_shared/infrastructure.tf:18-60` declares three
`static-zfs-pv` modules, all in `module.namespace.name`, pre-bound to `postgres-1`/`-2`/`-3`. A
teardown leaves three `Released` PVs in one namespace and a re-deploy needs all three reattached; if
only the first were, the other two CNPG instances' PVCs would sit `Pending` forever — no dynamic
provisioner can serve them, since the PVs carry `storage_class_name = ""`.

The code as written is correct, which is why this is advisory: the gap is regression protection, not
a defect to fix.

### F2 — `cli.py`'s stated reason for reattaching after the apply cannot happen

**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

`presync/cli.py:46-47` justifies the ordering as "After the apply, so the volumes Terraform just
declared are reattachable too". A volume Terraform declares in this apply is never `Released` — the
phase is reached only after a bound PVC is deleted, and the estate's PV modules set `claim_ref` with
no uid (`/work/HelmCharts/terraform-modules/static-zfs-pv/main.tf:109-112`), which the PV controller
treats as pre-bound and marks `Available`. So a just-declared volume can never satisfy
`claimed_by`'s `status.phase == "Released"` bound, and the comment names a benefit the ordering
cannot deliver. The ordering's real load — a failed apply must reattach nothing — is what the code
does and what `tests/test_cli.py:147-156` asserts.

### F3 — A ServiceAccount CA that is present but unparseable fails the run with a traceback, not a named cause

**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

`Api.__init__` builds its TLS context at `presync/kube.py:35` from `who.ca_file`, but
`kubeconfig.identity()` only checks that the file exists (`presync/kubeconfig.py:53-55`), never that
it parses. An empty or truncated `ca.crt` — a partially-projected volume, a misassembled ESO literal
— makes `ssl.create_default_context` raise `ssl.SSLError` (`[X509: NO_CERTIFICATE_OR_CRL_FOUND] no
certificate or crl found`, confirmed on the gate's interpreter), which is not a `PresyncError` and so
escapes `__main__.py:15`'s handler. D30 still holds — an uncaught exception exits 1 — so the sync is
correctly gated; what is lost is the "fails the run by name" property every other input in this
entrypoint has (`environment.require`, `kubeconfig.identity`, `backend._wait_until_listening`,
`git.clone_at_revision`), and the Job log shows a Python traceback where the rest of the flow shows
`presync: <cause>`. The window is also later than it needs to be: the context is only built after the
clone, the init and the apply have already run.
