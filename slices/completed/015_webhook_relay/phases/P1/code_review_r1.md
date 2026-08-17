# P1 — code review, round 1

Diff under review: `git diff 1f06dbaf0429c35c95d30ff6ad50b11eb0a557e6..HEAD` on `phase/015-P1` in
`/work/DockerImages` — one commit, `51f6653`, 12 new files under `webhook-relay/`, 1266 insertions,
nothing else in the repo touched.

## Readiness

**One blocking finding: the relay follows HTTP redirects, so a leg can be recorded as delivered
when nothing was delivered.** Everything else about the phase is in good shape — the functional
contract is met clause by clause, the gate is green, and the remaining three findings are advisory
— but F4 puts a witnessed hole in R2's central property, the one the plan says "this whole design
exists to protect", and the receiver URLs that decide whether it fires are written by a different
slice against a README that does not mention the behaviour. The rest of this paragraph stands: the
plan's five pinned rulings (Go + `backup-server` layout into `iac-provisioner`'s runtime stage, the
`/api/webhook` path, the two served routes, the signature wire format, tests out of CI) are all
honoured. The dispatch recorded the gate as unverified, so I ran it myself against `51f6653`:
`cexec go go test ./...` and `-race -count=1` are green on Go 1.26.5, `go vet ./...` and `gofmt -l`
are clean, `cexec iac ./scripts/arch-validate.py */architecture.yaml` passes over the whole set
including the new file, and `kaniko --context webhook-relay --no-push` builds end to end (exit 0),
which also proves `golang:1.26-bookworm` resolves and `go.mod`'s `go 1.26.0` agrees with it. I went
past the suite to the production HTTP path the suite never exercises — the whole suite drives
`ServeHTTP` directly via `httptest.NewRequest`, so the `411` case is only reached by hand-setting
`r.ContentLength = -1` — and confirmed over a real socket that a genuinely chunked `POST` yields
`411`, a signed delivery yields `200` with both stubs hit, and a 1 MiB body against a 16-byte cap
yields `413`. The two timing-shaped tests do not flake: `-count=8 -race` on the `relay` package is
green. I also confirmed the refusal happens before the body is read: a `POST` with no
`X-Hub-Signature-256` whose body reader panics the test if touched returns `401` untouched
(`relay.go:88-92`). F1–F3 below are advisory; only F4 is fix work.

Two things I checked specifically because they would have been blockers and are not. First, R2's
"no retries": `rl.client` is a bare `http.Client` on `DefaultTransport`, whose only replay is
`shouldRetryRequest`'s `nothingWrittenError` case on an already-reused idle connection — the
receiver never saw the first attempt, so no delivery is duplicated, and `POST` with a body is not
`isReplayable()` (both read out of this toolchain's `net/http` source, not from memory). Second, the
fan-out's concurrency: `errs[i]` is written from per-iteration goroutines under Go 1.22+
loop-variable semantics with `go 1.26.0` in `go.mod`, `r.Header` is only read, and `wg.Wait()`
establishes the happens-before — `-race` agrees.

## Findings

Ranked by severity. Ids are assignment order, not rank.

### F4 — the relay follows HTTP redirects, so a leg is recorded as delivered when nothing was delivered

*Severity: Major · Impact: blocking · Anchor: repro-trace · Category: functional · Confidence:
high*

`relay.go:70` builds the fan-out client as a bare `&http.Client{}`, which carries Go's default
redirect policy: up to ten hops, followed automatically. The success test at `relay.go:193`
therefore reads the status of the *last* response in the chain, not the receiver's own answer. Three
traces, each witnessed against stub receivers in the phase's own harness on this commit:

**Trace A — GitHub is told 200 for a delivery no receiver processed.** A receiver answering `303 See
Other` with a `Location`: Go's redirect policy downgrades `POST` to `GET` and drops the body for
301/302/303, the redirect target answers `200`, and the leg is scored a success.

```
relay answered 200 body="ok\n"                 (log: "both receivers accepted")
redirect target hit=true method="GET" body="" sig="sha256=bc41f13e…"
```

The payload reached nothing. R2 says the relay answers GitHub 2xx "only when both legs returned
2xx", and the plan states the reason twice — "preserving its fidelity for **both** legs is the
property this whole design exists to protect", `README.md:52-60` restating it as the argument for
having no queue. A delivery scored green is a delivery whose manual redelivery button — available
for three days, per the same paragraph — is never pressed, and there is no other ledger. This is the
one failure mode the slice exists to prevent, reachable without any refusal being bypassed.

**Trace B — the signed payload is replayed to an arbitrary host, and still scored a success.** A
receiver answering `307` with a cross-host `Location`: Go replays the full body, and
`X-Hub-Signature-256` is not among the headers Go strips on a cross-domain redirect (it strips only
`Authorization`, `Www-Authenticate`, `Cookie`, `Cookie2`).

```
relay answered 200
cross-host target hit=true method="POST" event="push"
  sig="sha256=bc41f13e…" body="{\"ref\":\"refs/heads/main\",\"secret-ish\":\"payload\"}"
```

Anything able to answer as a receiver — a Service or DNS takeover inside `argocd-prd`, something
placed in front of one — turns the estate's internet-facing service into an outbound POST primitive
carrying GitHub's payload and its valid signature to any URL it names, while GitHub still sees
green. The consult's §2 blast-radius statement is that "the relay holds nothing else; that is the
whole point"; this is a capability outside that statement.

**Trace C — the 502 diagnostic misattributes.** A receiver answering `302` toward something that
404s produces `webhook-relay: 1 of 2 receivers failed / argocd-server: HTTP 404`. argocd-server
answered `302`; the `404` came from elsewhere. The 502 body is the operator's only view of a failed
leg (`relay.go:120-129` puts the URL in the log and the reason in the body), so it names a status no
receiver returned.

Why this is blocking rather than advisory, given the two real receivers do not redirect on
`/api/webhook` today: the receiver URLs are not this slice's to choose. Per the cut-line ruling 009
writes them, "with no further contact with this slice", against the README's contract at
`README.md:85-110` — which documents the two variables as plain URLs and says nothing about
redirects or about what the relay trusts at the other end. The README's own examples are `http://`
URLs, and argocd-server's TLS posture is 009's to set and not settled in the `argo-cd/` document set
(`grep -n 'insecure\|redirect' /work/AnsibleSpecs/argo-cd/*.md` matches nothing), so whether this
fires at all is decided in a slice that has no way to know the question exists. `relay_test.go`
has no redirect case, so nothing in the suite pins the intended behaviour either way.

### F1 — the served refusal matrix is narrower than the acceptance criterion's literal wording

*Severity: Minor · Impact: advisory · Anchor: contradiction · Category: functional · Confidence:
high*

`relay.go:76-81` registers exactly two patterns on Go's method-aware `ServeMux`: `POST /api/webhook`
and `GET /healthz`. Go's `ServeMux` documents that a `GET` pattern also matches `HEAD`, and that a
request whose path is not already canonical gets a redirect rather than a miss. Probed against this
commit, both through `ServeHTTP` and over a real socket:

```
HEAD     /healthz         -> 200
HEAD     /api/webhook     -> 405
OPTIONS  /healthz         -> 405
POST     /api//webhook    -> 307
POST     /api/./webhook   -> 307
GET      /healthz/        -> 404
```

`verification.json` V04 and `plan.md`'s health-path ruling both say "every other path, and every
other method on those two, is refused", and `README.md:75-76` restates that as a table — `Any other
method on either path` → `405`, `Any other path` → `404`. `HEAD /healthz` → `200` and
`POST /api//webhook` → `307` are neither. `relay_test.go:354-381` pins eleven refusal cases and
covers none of these two shapes.

Why it matters, and why only advisorily: there is no product consequence — `HEAD` is `GET` without a
body per RFC 9110, and the `307` sends the client to the canonical path where the signature still
has to verify — but the ruling that fixed the two-route matrix exists precisely so "a test agent
probing the refusal matrix … does not have to guess which way to rule", and these two shapes are
exactly that guess, now in the phase's own README as a claim the binary does not make.

### F2 — nothing in the suite pins the constant-time comparison; the `==` mutation survives

*Severity: Major · Impact: advisory · Anchor: coverage-gap · Category: functional · Confidence:
high*

V14 names five properties of GitHub's wire format that R6's suite must pin. Four are pinned:
the `sha256=` prefix and lowercase-hex digest (`signature_test.go:21-53`, including the
prefix-stripped and uppercase-hex rejections), the digest over the exact raw bytes
(`signature_test.go:58-70`), a missing header refused exactly like an invalid one
(`relay_test.go:385-404`), and SHA-1 forwarded but never trusted (`relay_test.go:408-417` plus the
header assertion at `relay_test.go:174-185`). The fifth — "the comparison is **constant-time**
(`hmac.Equal`), never `==`" — has no test behind it.

I ran the mutation. In a scratch copy of the module, replacing `signature.go:36`'s
`return hmac.Equal([]byte(got), []byte(want))` with `return got == want` leaves
`cexec go go test -count=1 ./...` fully green across all three packages. So the one property of the
five that is a security property is the one the suite would not notice being removed, on the
service whose entire design rationale is what an unauthenticated internet caller can reach.

Advisory, not blocking, for one reason: the shipped code *is* constant-time (`signature.go:32-37`,
with the reasoning in its doc comment), and constant-timeness is not behaviourally testable in Go
without a timing harness whose flakiness would cost more than it buys. The gap is real; I do not
think it funds a fix round.

### F3 — "the estate's only internet-facing service" is false as written

*Severity: Minor · Impact: advisory · Anchor: none · Category: comment-prose · Confidence: high*

`architecture.yaml:4`, `README.md:9-10` and `Dockerfile:12-13` each state flatly that the relay is
the estate's only internet-facing service. Around twenty services face the internet today —
`HelmCharts/configs/prd/jenkins/prd/values.yaml:4`, `.../keycloak/prd/values.yaml:4`,
`.../guacamole/prd/values.yaml:4`, `.../webathome-org/prd/values.yaml:4` and more all set
`isPublic: yes` — and the slice's own estate facts say so: `slice.md`, "Jenkins rides it today at
`jenkins.webathome.org`". The authoritative design says the narrower, true thing — the consult's §1
calls the relay "the only public thing in `argocd-prd`". The claim reached a hand-authored
`architecture.yaml`, which is source of truth for the federated model rather than a throwaway
comment, which is why it is worth the one sentence.

## Checked and clear

Recorded so a later round does not re-derive them.

- **R1** — `relay.go:104-133`: body read under the cap, verified, then the *same* `body` slice
  forwarded; `forwardedHeaders` (`relay.go:42-48`) is exactly R1's list, and
  `relay_test.go:155-187` asserts all five arrive on both legs with the body byte-identical.
  `TestForwardsNoCredentialOfItsOwn` (`relay_test.go:191-204`) covers R5's code half from the wire
  side; `config_test.go` covers it from the config side.
- **R2** — `fanOut`/`post` (`relay.go:138-200`): per-leg `context.WithTimeout` at 4 s
  (`relay.go:37`), `502` naming each failed leg with its reason and the URL kept to the log
  (`relay.go:120-129`, `relay.go:155-157`). Each leg failing alone is covered as a table
  (`relay_test.go:243-282`), both failing (`:284-296`), and the timeout path (`:298-311`). The
  2xx-only test at `relay.go:193` is correct on the response it is handed; what it is handed is F4.
- **R3** — no payload parse anywhere in the diff; `ping` (`relay_test.go:321-335`) and a
  non-JSON body with NUL and `0xff` (`:339-350`) both relay verbatim.
- **R4** — signature presence and declared length are both checked before the body is read
  (`relay.go:88-102`), which I verified directly; the lying-`Content-Length` belt-and-braces path
  (`relay.go:104-113`) is covered at `relay_test.go:441-451` and the cap boundary at `:453-459`.
- **R6 / V09 / V12** — `webhook-relay/` is a top-level directory with a `Dockerfile`, which is the
  whole of the pipeline wiring (`tools/dockerfile_deps.py:21-28`, `Jenkinsfile:46`,
  `Jenkinsfile:100-101`); the root `Jenkinsfile` is untouched. The builder stage is
  `backup-server/Dockerfile:1-9`'s shape and the runtime stage is `iac-provisioner/Dockerfile:9-13`'s
  — `debian:bookworm-slim`, `ca-certificates` only, no apt cache, static binary — with
  `backup-server`'s apt-plus-`rclone` runtime correctly not copied. No `go.sum` is correct: the
  module has no requires.
- **V11** — `webhook-relay/architecture.yaml` follows `backup-server/architecture.yaml`'s shape
  (one `SoftwareProduct`, one `ApplicationService` realized by it, one `ApplicationInterface`
  assigned to it, `sourceRepository: git:pvginkel/DockerImages`, `environment`/`cluster` unset) and
  validates in the whole set. The absent consumption edge is argued in the file's own header comment
  and recorded as close-out S2; no `cap:` in the repo's existing vocabulary
  (`cap:continuous-integration`, `cap:source-control`, …) fits Argo CD's receivers, so minting a
  dangling reference would have been worse.
- **V13** — `README.md:85-110` carries everything 009 needs with no further contact with this
  slice: port `8080`, `GET /healthz`, `WEBHOOK_SECRET` / `ARGOCD_WEBHOOK_URL` /
  `APPLICATIONSET_WEBHOOK_URL` plus optional `LISTEN_ADDR`, statelessness and `RollingUpdate`, no
  volumes, no service account beyond the default. The README's `openssl dgst -sha256 -hmac` recipe
  and its note that `python3 -m http.server` answers `POST` with `501` are both accurate.
- **Not findings, deliberately.** Recorded so a later round does not re-raise them. No SIGTERM
  handling in `main.go` and no `USER` in the Dockerfile are the repo's universal convention
  (`backup-server` and `iac-provisioner` have neither; only `code-server` sets `USER`), not this
  phase's deviation. The README's two-replica claim is the consult's own §1 sentence, not drift.
  Using `r.Context()` as the fan-out's parent, so a client hang-up cancels both legs, is an approach
  choice the plan does not rule on and is consistent with "GitHub's *Recent Deliveries* is the
  ledger". `io.ReadAll` at `relay.go:104` grows by doubling rather than sizing from the already
  validated `ContentLength`, so a refused 4 MiB body churns roughly 2.4× its size pre-HMAC — but an
  attacker must upload those 4 MiB to cause it, which is exactly the volumetric case the consult's
  §2 answers ("the volumetric threat saturates the PPPoE link before any app-level limiter
  matters"). `hdr.Get` at `relay.go:178` forwards only the first value of a repeated header, and the
  Transport adds its own `User-Agent` and `Accept-Encoding`; GitHub sends no repeated headers and
  neither receiver keys on either, so "verbatim" holds for every header R1 names.
