# 015 — The webhook relay: one public endpoint that verifies and fans out to Argo's two receivers

A small purpose-built HTTP service — the estate's one new internet-facing surface — that receives
GitHub push webhooks, verifies the HMAC at the edge, and duplicates every verified delivery to both
Argo CD receivers. Argo CD itself stays internal.

## What is being requested and why

Cut out of slice **009** during its planning session (2026-08-16), when the exposure requirement
turned out to contradict itself. `phases.md` A.4 says *"Expose argocd-server behind the estate
ingress with homelab TLS"* — and in this estate "homelab TLS" means the internal step-ca on
`<app>.home`, which the router does not forward to. But A.4's next bullet, A.5's first proof item
and **D39** all require GitHub to reach the receivers **from the internet**. The operator had
already declined the alternative that needed no new ingress (`argo-cd/archive/qa.md`: *"Webhook. No
poll. No Jenkins relay. I will setup a web hook push from GitHub."*).

The operator's ruling, verbatim:

> It feels like a bad idea opening up argo cd to the internet. I feel a limited application to
> handle web hooks, that also handles the fan out, is the right call. Please ask Fable for a
> consult on this.

That consult is [`attachments/webhook-relay-consult.md`](attachments/webhook-relay-consult.md) —
**the authoritative design for this slice**, kept verbatim. It also settles **O3** (`decisions.md`
§"Open"): one fanned-out endpoint, not two registered hooks.

**Split from 009 because** 009 was already the largest slice in the set before this was new build
work, this lands in a different repo (`DockerImages`), it is independently testable against stub
receivers before Argo CD exists, and the estate's one new internet-facing surface deserves a review
that is not buried under eleven unrelated proof items.

## Requirements

1. A stateless HTTP service that exposes **one POST endpoint**, reads the body up to a size cap,
   verifies GitHub's `X-Hub-Signature-256` HMAC-SHA256 in constant time against a shared secret,
   and on success forwards the **raw body verbatim** — with `X-GitHub-Event`, `X-GitHub-Delivery`,
   both signature headers and `Content-Type` — **concurrently to both receivers**:
   argocd-server `/api/webhook` and applicationset-controller `:7000/api/webhook`. Plus a health
   endpoint.
2. **Both-or-502.** Answer GitHub 2xx only when both legs returned 2xx; otherwise 502 with a body
   naming the failed leg. Per-leg timeout ~4s, to stay inside GitHub's 10-second window. **No
   retries, no queue, no buffering, no state** — GitHub's *Recent Deliveries* is the ledger, and
   preserving its fidelity for **both** legs is the property this whole design exists to protect.
3. **Duplicate every delivery; no routing table.** Each receiver does its own repository matching
   and no-ops cheaply on a push it does not care about. No event-type filtering — forward `ping`
   too. Never parse the payload.
4. **Refuse structurally, not semantically**: non-POST, any path but the webhook path, missing or
   invalid signature, missing `Content-Length`, body over the cap — refusing before reading the
   body where possible.
5. The service holds **no credential toward GitHub and none toward the cluster** — its only config
   is the shared secret and the two target URLs. The secret is the same value as
   `webhook.github.secret` in `argocd-secret`: **one OpenBao leaf, not a second secret.**
6. Source, Dockerfile and tests in **`DockerImages`**, published by the existing pipeline as
   `registry:5000/webhook-relay:<n>`. Unit tests must cover HMAC verification (accept and reject),
   the fan-out, both-or-502 including each leg failing alone, and every refusal in requirement 4 —
   all provable against stub receivers, with no Argo CD in the loop.
7. Update the `argo-cd/` document set: **close O3** in `decisions.md` in favour of one fanned-out
   endpoint; record in `design.md` that the registered hook URL — the registry repo's manual hook
   and each deploy repo's D39 `github_repository_webhook` alike — is the relay's public URL, not
   argocd-server's; and correct A.4's "homelab TLS" exposure bullet in `phases.md`, which as
   written contradicts D39.

## Rulings carried in from 009's planning session (2026-08-16)

- **Hostname: `deploy-hooks.webathome.org`** (operator: *"deploy-hooks please"*). Public DNS in this
  estate is a manual operator action outside any repo, as is the router NAT rule.
- **Argo CD is not exposed to the internet.** argocd-server keeps `is-public: no` and an internal
  `.home` name. The relay is the only internet-facing surface.
- **No GitHub source-IP allowlist, no rate limiting** — the consult's §2 argues both; HMAC is
  strictly stronger than source IP, and the meta ranges would need a freshness mechanism.
- **The cut line against 009, moved from the consult's §5 to avoid a circular dependency.** The
  consult puts the relay's chart fragment in `ArgoCDDeploy` — but `ArgoCDDeploy` does not exist
  until 009's first phase creates it, which would make the two slices mutually blocking. So:
  **this slice delivers the image, its tests and the doc updates only**, all self-contained in
  `DockerImages` and `AnsibleSpecs`. **Slice 009 authors the relay's Deployment, Service and
  `deploy-hooks.webathome.org` annotation** in the wrapper chart it is already building, pinned to
  this slice's image tag — the same shape as 007's hook image pinned by 006's library chart.
  Ordering is therefore linear: **015 → 009**.

## What this slice does not do

- **The chart manifests.** Deployment, Service, the public annotation and the ExternalSecret for the
  shared webhook secret are 009's, per the ruling above.
- **Creating the webhooks on GitHub.** The registry repo's hook is an operator keystroke in 009
  (A.4's last bullet); each deploy repo's is D39's Terraform resource in Phase B.
- **The public DNS record and the router NAT rule** — operator actions outside every repo.
- **Proving it end to end.** The live proof is 009's, which gains two items on top of its existing
  proof item 8: a real GitHub delivery through the public URL landing 200 with both legs green, and
  the partial-failure drill (scale one receiver to zero, redeliver, see red in *Recent Deliveries*
  naming the dead leg, restore, redeliver green).

## Estate facts this slice relies on (verified 2026-08-16)

- **There are no `Ingress` objects, no ingress-nginx and no cert-manager in this estate.** A
  workload is exposed by annotating its own plain `Service`; the in-house `nginx-configurator`
  (`/work/DockerImages/nginx-configurator`) watches all Services and renders vhost config.
  `nginx.webathome.org/server-name`, `/is-public`, `/target-port`, `/enable-ssl`.
  `is-public: "yes"` gets a Let's Encrypt cert and faces the internet; `is-public: "no"` gets a
  step-ca leaf via `https://ca.home/acme/acme/directory` behind an `allow 192.168.0.0/16` block.
- **The inbound path already exists and is proven**: public IP → router NAT (configured on the
  UniFi router, outside any repo) → the shared nginx LoadBalancer at `10.2.1.7`. Jenkins rides it
  today at `jenkins.webathome.org` and every Jenkinsfile in the estate uses `githubPush()`.
- **The configurator has no per-service escape hatch** — one `location /` with one `proxy_pass` in
  `app/template.j2` — which is why the nginx-`mirror` alternative was rejected as surgery on the
  shared internet-facing data plane.
- Argo CD will live in namespace **`argocd-prd`** (ruled in 009's session; the estate's universal
  namespace convention is `<app>-<stage>`).

## Operator boundary

The estate rule stands: the operator runs every apply and every deploy, creates the public DNS
record, the router rule and the GitHub webhooks, and writes the OpenBao secret value. Claude
prepares the exact commands and waits.

## Interlocks

- **Slice 009** — depends on this slice's image; deploys the relay and proves it live.
- **Triage #507** — revisits a slow fallback poll for the dropped-webhook consequence. Not this
  slice; this slice's both-or-502 makes a drop *visible*, which is the cheaper half of what #507
  wants.
- **D39** — each deploy repo's `github_repository_webhook` points at this relay's URL. Phase B.
