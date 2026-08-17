# P1 — code review, round 2

Diff under review: `git diff 51f66531a77ccba76d309c15123b94ef05430e37..HEAD` on `phase/015-P1` in
`/work/DockerImages` — one commit, `6f4c884`, three files touched (`webhook-relay/README.md`,
`src/internal/relay/relay.go`, `src/internal/relay/relay_test.go`), 64 insertions, 7 deletions. The
rest of the branch was reviewed in round 1 and is context here, not re-review scope.

## Readiness

**Sign-off. Round 1's one blocking finding (F4, the followed redirect) is fixed at the root, the fix
is pinned by a non-vacuous test that exercises the production construction path, and the fix commit
introduces no new problem I can find.** `relay.go:70` now builds the fan-out client as
`&http.Client{CheckRedirect: noRedirects}`, and `noRedirects` (`relay.go:83-85`) returns
`http.ErrUseLastResponse`, so the 3xx is handed back as that leg's own answer: `post`'s 2xx test at
`relay.go:204` sees the receiver's real status, the leg fails as `HTTP 301`…`HTTP 308`, and no hop is
taken — which closes all three of F4's traces at once (trace A's silently-green 303, trace B's
cross-host replay of the signed body on 307/308, trace C's misattributed 502 diagnostic, which now
names the status the receiver itself answered). The response-body contract that comes with
`ErrUseLastResponse` — the client returns the last response *unclosed*, so the caller owns it — is
honoured: `relay.go:201-202` drains and closes it, in that order, with the leg's `cancel` deferred
earlier so it runs after the close, so the connection is still returnable to the pool and the leg
timeout is not cancelled out from under the drain. The dispatch recorded the gate as unverified, so I
ran it against this commit myself: `cexec go go test ./...` green, `-count=1 -race` green over all
three packages, `go vet ./...` and `gofmt -l` clean, and `cexec iac ./scripts/arch-validate.py
*/architecture.yaml` green over all 23 files (`architecture.yaml` is untouched this round; it is
re-run only because the gate state was unverified). I did not re-run `kaniko --context webhook-relay
--no-push` — the `Dockerfile` and `go.mod` are untouched by this commit and the only source change
compiles under `go vet`/`go test`, so round 1's build proof stands.

I checked the new test is not vacuous rather than taking it on faith. `newHarness`
(`relay_test.go:109-122`) builds the relay through `relay.New(...)` — the same constructor
`cmd/webhook-relay/main.go:32` uses — so the test pins production's client, not a client the harness
made for itself. Mutation run: in a scratch copy of the module, reverting `relay.go:70` to
`&http.Client{}` and leaving everything else alone,
`cexec go go test -count=1 -run TestRedirect ./internal/relay/` fails on **all five** subtests
(`301/302/303/307/308`), each with `status 200, want 502 (body "ok\n")` and the relay logging "both
receivers accepted" — exactly round 1's trace A, caught. The stub receivers are real
`httptest.NewServer`s, so the outbound leg — the only side this fix touches — is exercised over real
sockets; the redirect target is a separate server and the test asserts it was contacted zero times,
which is what forecloses trace B's replay.

On the fix's cost, which I looked for as a possible new blocker and do not think is one: a receiver
URL that legitimately redirects (an `http://` URL toward an argocd-server that upgrades to `https://`
in non-insecure mode) now fails every delivery instead of quietly succeeding through the hop. That is
the intended trade — a loud `502` naming `argocd-server: HTTP 308` in *Recent Deliveries*, where a
redelivery button exists, versus a green delivery nothing processed — and the commit tells 009 so in
the one place 009 reads: `README.md:94-97`, immediately under the two URL variables in the
configuration table, naming that exact scenario. That was the half of F4 that made it blocking (the
URLs are written by a slice with "no further contact with this slice"), and it is now closed on the
documentation side as well as in code.

## Findings

None. Nothing in `6f4c884` is fix work for a further round, and nothing new was entered in
`close-out.md` this round.

Round 1's three advisory findings — F1 (the `HEAD /healthz` / non-canonical-path shapes outside the
stated refusal matrix), F2 (no test pins the constant-time comparison), F3 ("the estate's only
internet-facing service") — are unfixed by design and already recorded as `close-out.md` B2, B1 and
B3 respectively. They are the protocol working; they are not re-reported here and the fix commit does
not disturb them: it touches neither `signature.go`, nor `Routes()`, nor any of the three copies of
the internet-facing sentence.

## Checked and clear

Recorded so a later round does not re-derive them.

- **`ErrUseLastResponse` semantics.** Read out of this toolchain's `net/http` source, not from
  memory: `Client.do` returns the response immediately on that sentinel, *before* the
  drain-and-close it performs when a redirect is actually followed — hence the caller-owns-the-body
  rule that `relay.go:201-202` satisfies. No body leak, no held connection.
- **The doc comment's factual claims** (`relay.go:76-82`) are all true of Go's default policy it
  describes: 301/302/303 rewrite the method to `GET` and drop the body, 307/308 replay it (the
  `bytes.Reader` in `relay.go:184` gives `NewRequestWithContext` a `GetBody`, so the replay would
  have worked), and `X-Hub-Signature-256` is not among the four headers Go strips across hosts. It
  records why a non-obvious client option exists rather than restating the code or narrating the
  change, which is the shape the rest of this file's comments already have.
- **No second HTTP client escapes the fix.** `grep -rn "http.Client\|http.Get\|http.Post\|
  DefaultClient" webhook-relay/` matches only the field declaration and the one construction in
  `New`, so there is no other outbound path still carrying the default redirect policy.
- **The test additions do not destabilise the suite.** `receiver.location` is written and read under
  the same mutex as `status` (`relay_test.go:63`, `:85-89`), defaults empty so every pre-existing
  test is unaffected, and each subtest gets a fresh harness with `t.Cleanup`-closed servers; the
  package is green under `-race`.
- **The plan's done-record matches the code.** `plan.md:218-223` describes the fix as shipped —
  `CheckRedirect` returning `ErrUseLastResponse`, the leg failing as `HTTP 3xx`, the README telling
  009 that a redirecting URL is a `502` every time — with no claim the diff does not support.
