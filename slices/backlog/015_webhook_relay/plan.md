# Slice 015 — the webhook relay image: one public endpoint that verifies GitHub's HMAC and fans out to Argo's two receivers

## Requirements / rulings

Requirements R1–R7 are `slice.md`'s numbered requirements, carried over as the authoritative
statement of intent. The design behind them is `attachments/webhook-relay-consult.md`, kept
verbatim and authoritative for *why* the relay is shaped this way.

- **R1.** A stateless HTTP service that exposes **one POST endpoint**, reads the body up to a size
  cap, verifies GitHub's `X-Hub-Signature-256` HMAC-SHA256 in constant time against a shared
  secret, and on success forwards the **raw body verbatim** — with `X-GitHub-Event`,
  `X-GitHub-Delivery`, both signature headers and `Content-Type` — **concurrently to both
  receivers**: argocd-server `/api/webhook` and applicationset-controller `:7000/api/webhook`.
  Plus a health endpoint.
- **R2.** **Both-or-502.** Answer GitHub 2xx only when both legs returned 2xx; otherwise 502 with a
  body naming the failed leg. Per-leg timeout ~4s, to stay inside GitHub's 10-second window. **No
  retries, no queue, no buffering, no state** — GitHub's *Recent Deliveries* is the ledger, and
  preserving its fidelity for **both** legs is the property this whole design exists to protect.
- **R3.** **Duplicate every delivery; no routing table.** Each receiver does its own repository
  matching and no-ops cheaply on a push it does not care about. No event-type filtering — forward
  `ping` too. Never parse the payload.
- **R4.** **Refuse structurally, not semantically**: non-POST, any path but the webhook path,
  missing or invalid signature, missing `Content-Length`, body over the cap — refusing before
  reading the body where possible.
- **R5.** The service holds **no credential toward GitHub and none toward the cluster** — its only
  config is the shared secret and the two target URLs. The secret is the same value as
  `webhook.github.secret` in `argocd-secret`: **one OpenBao leaf, not a second secret.**
- **R6.** Source, Dockerfile and tests in **`DockerImages`**, published by the existing pipeline as
  `registry:5000/webhook-relay:<n>`. Unit tests must cover HMAC verification (accept and reject),
  the fan-out, both-or-502 including each leg failing alone, and every refusal in R4 — all provable
  against stub receivers, with no Argo CD in the loop.
- **R7.** Update the `argo-cd/` document set: **close O3** in `decisions.md` in favour of one
  fanned-out endpoint; record in `design.md` that the registered hook URL — the registry repo's
  manual hook and each deploy repo's D39 `github_repository_webhook` alike — is the relay's public
  URL, not argocd-server's; and correct A.4's "homelab TLS" exposure bullet in `phases.md`, which
  as written contradicts D39.

#### Rulings carried in from 009's planning session (2026-08-16)

- **Hostname: `deploy-hooks.webathome.org`** (operator: *"deploy-hooks please"*). Public DNS in this
  estate is a manual operator action outside any repo, as is the router NAT rule.
- **Argo CD is not exposed to the internet.** argocd-server keeps `is-public: no` and an internal
  `.home` name. The relay is the only internet-facing surface. The operator's ruling that produced
  this slice, verbatim: *"It feels like a bad idea opening up argo cd to the internet. I feel a
  limited application to handle web hooks, that also handles the fan out, is the right call."*
- **No GitHub source-IP allowlist, no rate limiting** — the consult's §2 argues both; HMAC is
  strictly stronger than source IP, and the meta ranges would need a freshness mechanism.
- **The cut line against 009.** The consult puts the relay's chart fragment in `ArgoCDDeploy`, but
  that repo does not exist until 009's first phase creates it, which would make the two slices
  mutually blocking. So **this slice delivers the image, its tests and the doc updates only**, all
  self-contained in `DockerImages` and `AnsibleSpecs`. **Slice 009 authors the relay's Deployment,
  Service and `deploy-hooks.webathome.org` annotation**, pinned to this slice's image tag — the same
  shape as 007's hook image pinned by 006's library chart. Ordering is linear: **015 → 009**.

#### Rulings from this planning session (2026-08-17)

- **Ruling (2026-08-17) — the relay is written in Go.** The consult's §1/§2 specify a "small Go
  binary", and that is what ships. `DockerImages` has the precedent twice — `backup-server` and
  `iac-provisioner`, both Go, both concurrency-shaped like this. On the estate's one
  internet-facing surface a static binary means no interpreter and no dependency tree to patch,
  which is the parse-surface argument the whole design rests on. Follow `backup-server`'s layout
  and Dockerfile shape: `src/` holding `go.mod`, `cmd/webhook-relay/main.go` and `internal/<pkg>/`,
  multi-stage build from `golang:*-bookworm` into a slim runtime stage carrying only the binary.
  (This overrides the Python/Flask+waitress convention that the repo's other 14 small services
  follow; it was chosen deliberately, not by default.)
- **Ruling (2026-08-17) — the endpoint path is `/api/webhook`.** The registered hook URL is
  therefore `https://deploy-hooks.webathome.org/api/webhook`. It mirrors both receivers' own path,
  so the URL reads identically whether it points at the relay or, in a debug bypass, straight at a
  receiver. This is the URL R7 records in `design.md` and the one D39's Terraform resource carries.
- **Ruling (2026-08-17) — the image ships an `architecture.yaml`.** `DockerImages/CLAUDE.md`
  requires every in-house app to carry a hand-authored `<app>/architecture.yaml`, validated with
  `./scripts/arch-validate.py */architecture.yaml`. This slice adds a brand-new app and the
  estate's only internet-facing service; leaving it out would put a hole in the federated model.
- **Ruling (2026-08-17) — the tests are not wired into CI.** Operator, verbatim: *"No, don't run
  the tests in CI. The DockerImages repo is not setup for that. Just add tests like other projects
  do in the repo. If I ever want them run in CI, I need to move this to its own repo."* R6's suite
  is therefore run the way the repo already runs tests — for a Go image, `go test ./...` as
  `backup-server` documents — and the shared root `Jenkinsfile`, which builds and pushes every
  image and runs no tests today, is **not** touched.

## Task shape

pre-settled — `slice.md` names `attachments/webhook-relay-consult.md` "the authoritative design for
this slice", R1–R6 fix the functional contract clause by clause, and this session's rulings pin the
language, the layout precedent, the endpoint path and the CI posture; planning is transcription.

## Ordering constraints

- **015 → 009.** Slice 009 pins this slice's published image tag; it cannot deploy a relay that has
  not been built. Nothing in 015 depends on 009.
- The slice has **one coding phase**. R7 is in scope and `verification.json` checks it, but its
  `argo-cd/` document-set edits are the run loop's own doc phase — steered by R7 above, in the
  operator's words — not a phase here.

### P1 — The webhook relay image

Target: ../DockerImages

**Outcome.** A new in-house app directory `webhook-relay/` at the repo root that the existing
pipeline builds and publishes as `registry:5000/webhook-relay:<n>`, holding the service, its unit
tests, its Dockerfile, its README and its `architecture.yaml`. R1–R6 above are the functional
contract, clause by clause; the reasoning behind each — why both-or-502 rather than a queue, why
duplication rather than a routing table, why no source-IP allowlist, why the parse surface is the
whole point — is `attachments/webhook-relay-consult.md` §§1–3, authoritative and worth reading
before the handler is written. Nothing in it needs re-deciding. When this phase merges, slice 009
must be able to pin the tag and write the Deployment and Service without reopening this slice.

Constraints the repo will not tell you:

- **The directory name is the image name, and there is no registration anywhere to edit.** Both
  pipelines glob: the build discovers any top-level directory holding a `Dockerfile`
  (`tools/dockerfile_deps.py:21-28`), rebuilds it only when that directory changed
  (`Jenkinsfile:46`) and pushes `registry:5000/<dir>:<build#>` plus `:latest`
  (`Jenkinsfile:100-101`); the architecture producer copies every `*/architecture.yaml`
  (`Jenkinsfile.architecture:32`). Creating the directory *is* the whole of "wire it into the
  pipeline" — and per the ruling the root `Jenkinsfile` is not touched.
- **Layout follows `backup-server`** per the Go ruling — module under `src/`, `cmd/<app>/main.go`,
  `internal/<pkg>/`, and its multi-stage Dockerfile shape (`backup-server/Dockerfile:1-29`). Keep
  the `go.mod` language version and the builder image tag consistent with each other and buildable
  by this environment's Go toolchain (1.26.5 today), or the suite and the image disagree about
  which Go this is.
- **The gates run in sidecars, not the dev container** — there is no `go` and no `python` here.
  `cexec go go test ./...` from the module root, and `cexec iac ./scripts/arch-validate.py
  */architecture.yaml` from the repo root — the whole set validated together so cross-file `svc:`
  references resolve (`DockerImages/CLAUDE.md:27-30`). Those two green are this phase's gate; the
  tests stay out of CI per the ruling.
- **Exactly two paths are served**: the webhook path `/api/webhook` (ruling) and a health path.
  Every other path is one of R4's structural refusals.
- **The README is 009's input.** 009 authors the Deployment, Service and public annotation against
  this image with no further contact with this slice, so what it needs must be findable there: the
  listen port, the environment variables carrying the shared secret and the two receiver URLs, the
  health path, and the fact that the process is stateless and safe above one replica.
- `architecture.yaml` is hand-authored source of truth for a brand-new `SoftwareProduct` in the
  federated model; `DockerImages/CLAUDE.md` §"What each producer owns" and §"Conventions" govern
  its shape, and `backup-server/architecture.yaml` is the worked example.

## Not in scope

- **The chart manifests.** Deployment, Service, the public annotation and the ExternalSecret for the
  shared webhook secret are 009's, per the cut-line ruling above.
- **Creating the webhooks on GitHub.** The registry repo's hook is an operator keystroke in 009
  (A.4's last bullet); each deploy repo's is D39's Terraform resource in Phase B.
- **The public DNS record and the router NAT rule** — operator actions outside every repo.
- **Proving it end to end.** The live proof is 009's, which gains two items on top of its existing
  proof item 8: a real GitHub delivery through the public URL landing 200 with both legs green, and
  the partial-failure drill (scale one receiver to zero, redeliver, see red in *Recent Deliveries*
  naming the dead leg, restore, redeliver green).
- **Running the tests in CI**, and any change to the shared root `Jenkinsfile` — per the ruling
  above.
- **A GitHub source-IP allowlist and rate limiting** — ruled out in 009's session.
