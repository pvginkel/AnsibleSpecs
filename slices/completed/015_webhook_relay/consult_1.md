# Consult 1 — slice 015 webhook_relay

Outcome: **complete**. No phase appended.

## What the plan owes, and where each piece landed

P1 is the slice's only coding phase, and the plan says so in *Ordering constraints*. Walking the
requirements and rulings against the merged tree (`DockerImages` @ `6f4c884`, 12 files, 1323 lines
under `webhook-relay/`):

| Owed | Delivered by |
| --- | --- |
| R1 — one POST endpoint, size cap, constant-time HMAC, verbatim fan-out with the five headers, concurrent, plus health | `relay.go:87-145` (`Routes`, `handleWebhook`), `relay.go:40-48` (`forwardedHeaders`), `relay.go:149-171` (`fanOut`, `sync.WaitGroup`) |
| R2 — both-or-502, ~4 s per leg, no state | `relay.go:31-38` (`defaultLegTimeout`), `relay.go:131-144`, `relay.go:180-211` |
| R3 — duplicate everything, never parse | `relay.go` has no unmarshal; body is `[]byte` end to end |
| R4 — structural refusals | `relay.go:98-124`; signature presence and declared length checked before the body is read |
| R5 (code half) — no credential, config is the secret plus two URLs | `config.go:13-42`; the 4 MiB cap and 4 s timeout are source constants, not env |
| R6 — lands in DockerImages, published by the existing glob; suite covers HMAC accept/reject, fan-out, both-or-502 each leg alone, every R4 refusal | root `Jenkinsfile` untouched (diff stat is `webhook-relay/` only); `relay_test.go` (508 lines), `signature_test.go`, `config_test.go` |
| Ruling — Go, `backup-server` layout into `iac-provisioner` runtime | `src/{go.mod,cmd/webhook-relay,internal/*}`; `Dockerfile` = `golang:1.26-bookworm` builder → `debian:bookworm-slim` + `ca-certificates` and the binary, nothing else |
| Ruling — endpoint path `/api/webhook` | `relay.go:24` |
| Ruling — ships an `architecture.yaml` | `webhook-relay/architecture.yaml`, green in `arch-validate` over all 23 files |
| Ruling — tests out of CI | root `Jenkinsfile` untouched; `README.md:117-126` documents `go test ./...` by hand |
| Ruling — exactly two routes | `relay.go:87-92`, method-aware `ServeMux` |
| Ruling — signature wire format | `signature.go`: `sha256=` prefix part of the value, lowercase hex, HMAC over the exact wire bytes, `hmac.Equal`, missing header refused like invalid, SHA-1 forwarded never verified |
| V13 — 009 can pin and deploy from what shipped | `README.md:85-115`: port 8080, `GET /healthz`, the three env vars plus `LISTEN_ADDR`, statelessness and `RollingUpdate`, no volumes, no service account |

The toolchain check the plan asks for holds: `go.mod` is `go 1.26.0` against a `golang:1.26-bookworm`
builder, and this environment's `cexec go go version` is `go1.26.5`.

## The three things the plan does not deliver — all assigned elsewhere by the plan itself

1. **R7 / V08 — the `argo-cd/` document set.** *Ordering constraints*: "R7 is in scope and
   `verification.json` checks it, but its `argo-cd/` document-set edits are the run loop's own doc
   phase … not a phase here." The doc phase has not run (`run_phase: consult`, `test_rounds: 0`),
   and `docs/slice-doc-plan.md:21` puts `/work/AnsibleSpecs/argo-cd/` squarely in the doc-writer's
   scope. Its inputs are real and untouched: O3 open at `argo-cd/decisions.md:542`, the O3 pointer
   at `argo-cd/design.md:290-291`, and A.4's "homelab TLS" bullet at `argo-cd/phases.md:88-89`.
   Owed, not outstanding.
2. **R5's leaf half and the chart manifests.** The R5-split and cut-line rulings put both in 009;
   *Not in scope* denies them here.
3. **The architecture consumption edge toward the two receivers.** Filed as close-out S2, blocked on
   UUIDs only 009's `ArgoCDDeploy` producer can mint.

## Leftovers judged against the bar, not appended

- **B1 — V14's constant-time clause has no test behind it.** The plan says "R6's suite pins each of
  those five" and four are pinned; the fifth is not. The *implementing* work is there
  (`signature.go:36` is `hmac.Equal`, with a doc comment saying why) — what is missing is a test,
  and no non-flaky Go test distinguishes `hmac.Equal` from `==` without a timing harness. The
  realistic fix is a source-level guard, which is a judgement call, not work the plan specified.
  One word from the operator; not three rounds.
- **B2 — `HEAD /healthz` → 200 and `POST /api//webhook` → 307.** A literal mismatch against V04's
  "every other method on those two is refused", and the health-path ruling exists precisely so a
  test agent does not have to guess here. But V04 has plenty of implementing work to point at
  (the method-aware mux, eleven pinned refusal cases), both shapes are standard `ServeMux`
  behaviour with no product consequence, and which way to rule — teach the mux to refuse `HEAD`,
  or reword the criterion — is the operator's call. Recorded with the full account so the test
  agent has the material.
- **S1 — `DockerImages` has no `.kubecoder/project.yaml`.** Out of scope; a real gap that every
  future `DockerImages` phase pays, and a genuine design question because the repo is
  heterogeneous.
- **S3 (new) — V08 cannot be earned in the phase that judges it.** The test phase checks off
  `verification.json` (`agents/test-agent.md:17`) and runs *before* the doc phase
  (`run_loop.py:2521` then `:2631`); the doc-writer never touches that file. Filed so a red or
  blank V08 reads as ordering, not as a defect.

## Fixed in this session under the mechanical-residue exception

Close-out **B3**: `architecture.yaml:4`, `README.md:9-10` and `Dockerfile:12-13` each stated that
the relay is "the estate's only internet-facing service". It is not — `grep -rn isPublic
/work/HelmCharts/configs/prd | grep -c yes` → 21, including `jenkins`, `keycloak`, `guacamole` and
`webathome-org`, and this slice's own `slice.md` says Jenkins rides the internet today. The
authoritative design states the true, narrower claim: the consult's §1 calls the relay "the only
public thing in `argocd-prd`".

Comment and prose only, no behaviour change, in three files this slice's diff created — the
exception's shape exactly, so it is neither a phase nor a report entry. All three now state the
narrower claim; `main.go:27`'s "this process is internet-facing" was already true and is untouched.
Committed to `DockerImages` `main` as `6e01ede`, with `cexec iac ./scripts/arch-validate.py
*/architecture.yaml` (23 files) and `cexec go go test ./...` re-run green after the edit. B3 is
struck in `close-out.md` with the commit named.
