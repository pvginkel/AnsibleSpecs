# Consult — the webhook edge for Argo CD (O3 + the relay design)

Requested by the operator during slice 009's planning session (2026-08-16), after ruling that Argo
CD must not be exposed to the internet: *"I feel a limited application to handle web hooks, that
also handles the fan out, is the right call. Please ask Fable for a consult on this."* Answered by
Fable. Kept verbatim as the record of why the relay is shaped the way it is.

---

**The call, in one paragraph.** Build the tiny purpose-built relay — nothing existing fits without
violating something this design depends on. It is a stateless ~150-line HTTP service: verify
GitHub's HMAC at the edge, duplicate every verified delivery to both receivers concurrently, answer
GitHub 2xx only when both legs succeeded, hold no state, no retries, no queue. Image in
DockerImages, manifests in ArgoCDDeploy's wrapper chart (not HelmCharts), exposed through the
existing annotation mechanism as the only public thing in `argocd-prd`. Split it out as its own
slice, shaped like 007, that 009 depends on. This settles **O3** as: one public endpoint; every
hook — the registry's manual one and each deploy repo's D39 Terraform one — registers the same
relay URL.

## 1. Purpose-built — the alternatives each break something load-bearing

**nginx `mirror` is a genuine near-fit and fails on the one property this design leans on.**
Mechanically it works: the shared ingress vhost proxies the primary to one receiver and `mirror`s
to the other; the subrequest copies headers (`X-Hub-Signature-256` included) and, with the default
`mirror_request_body on`, the raw body — HMAC survives. Three failure modes rule it out:

- **The mirror leg is invisible to GitHub.** The mirrored response is discarded, so *Recent
  Deliveries* shows green whenever the primary succeeded — even if the mirrored receiver 500'd or
  was down. D6's accepted stale-but-green consequence is only acceptable *because* Recent
  Deliveries is where a miss is visible and redeliverable (design.md, Triage #507). Mirror silently
  amputates that visibility for half the fan-out. This alone is disqualifying.
- **The signal inverts under slowness.** nginx does not finalize the main request until mirror
  subrequests complete, so a slow mirrored receiver delays the primary response — past GitHub's
  10-second window, the delivery is recorded failed *because of the healthy leg's sibling*, and
  connection reuse stalls behind it.
- **It is surgery on the wrong component.** The configurator template has no per-service escape
  hatch — one `location /` with one `proxy_pass`
  (`/work/DockerImages/nginx-configurator/app/template.j2`) — so mirror means new annotation
  vocabulary and template changes in the shared internet-facing data plane, exactly the component
  whose fragility `decisions.md` §"Ingress isolation" documents from a live incident. And the
  primary `proxy_pass` still lands internet traffic directly on an Argo receiver's parser — the
  thing the operator rejected, path-scoped but not removed.

**Off-the-shelf relays don't fit either.** The smee/Hookdeck class inverts the connection
(in-cluster client subscribes outbound — no public surface at all), which is elegant but puts a
third-party SaaS in the production deploy path; the estate deliberately removed its last cloud
dependency (the Azure unseal), and self-hosting `gosmee` recreates the public receiver anyway.
`adnanh/webhook` can verify GitHub HMAC but is a hook-to-shell-command runner; fanning out means a
curl script per delivery with mangled response-code fidelity — more configuration than the
purpose-built service is code. Routing through Jenkins (already public, already receiving these
pushes for `githubPush()`) consumes the delivery inside Jenkins with no raw signed body to forward,
and wires Argo's trigger path through the system D1 is retiring from CD.

**Functionally, the relay is:** one POST endpoint; read body up to a cap; constant-time HMAC-SHA256
verify against the shared secret (the same value as `webhook.github.secret` — one OpenBao leaf, no
new secret); on success, POST the raw body verbatim with the GitHub headers (`X-GitHub-Event`,
`X-GitHub-Delivery`, both signature headers, `Content-Type`) to argocd-server `/api/webhook` and
applicationset-controller `:7000/api/webhook` concurrently, ~4-second per-leg timeout; respond 2xx
only if both legs did, else 502 with a body naming the failed leg (Recent Deliveries shows response
bodies — free diagnostics). Plus a health endpoint. It never parses the payload, never filters by
event type (forward `ping` too — the receivers handle it), holds no credential toward GitHub or the
cluster, and has no config beyond the secret and two target URLs. Two replicas, stateless, so a
self-sync roll of `argocd-prd` doesn't open a drop window. Estate precedent for exactly this shape:
`backup-server`, `nginx-configurator`, `dnsmasq-config-generator`.

## 2. Security model — verify at the edge, and skip the machinery that doesn't pay

**HMAC is verified at the edge, before anything is relayed.** The receivers verify it anyway (Argo
checks `webhook.github.secret` regardless — defense in depth for free), but edge verification is
what makes this design actually different from exposing Argo: the internet-reachable parse surface
becomes *an HMAC over raw bytes in a small Go binary holding no credentials*, instead of Argo's
multi-provider webhook parser inside the binary that holds the cluster. That parser's track record
is the concrete argument: **CVE-2024-40634** — unauthenticated OOM-kill of argocd-server via a
large `/api/webhook` payload — and **CVE-2025-59537** — unauthenticated crash via a malformed
*Gogs* payload when no Gogs secret is set. Note what the second one means: the attacker picks the
provider header, so configuring the GitHub secret does not protect the other providers' code paths.
Behind the relay, nothing unsigned-by-our-secret ever reaches any of them. (Independently: set
`webhook.maxPayloadSizeMB` in `argocd-cm` to something sane — it defaults to 50 MB.)

**GitHub source-IP enforcement: no.** HMAC is strictly stronger authentication than source IP, and
the meta ranges (`api.github.com/meta` → `hooks`) change over time, so enforcement means a freshness
mechanism — a second controller-shaped moving part guarding an endpoint whose pre-auth surface is a
signature check. There is also no natural enforcement point: the configurator's allow/deny
vocabulary is the fixed RFC1918 block, so nginx-side enforcement means template changes (§1's
objection again). If ever wanted, it's an additive in-relay change; don't build it now.

**Rate limiting and the rest: no dedicated machinery.** At homelab scale the volumetric threat
saturates the PPPoE link before any app-level limiter matters. What the relay *refuses* is
structural, not semantic: non-POST, any path but the webhook path, missing or invalid signature,
missing `Content-Length` or body over the cap (a few MiB — real push events are kilobytes; GitHub
itself drops payloads over 25 MB) — refusing before reading the body where possible. No event-type
filtering, no payload inspection: filtering is the receivers' business, and every semantic check
added to the edge is new attacker-reachable code.

**Blast radius, stated D41-style:** compromise of the relay pod yields the shared HMAC secret — the
ability to send correctly-signed webhooks to two receivers whose only action is to re-read *actual*
git through Argo's own credentials. A forged "branch moved" delivery triggers a refresh that reads
the real branch. The relay holds nothing else; that is the whole point.

## 3. Fan-out — duplicate everything, fail loud, buffer nothing

**Duplicate every verified delivery to both receivers; no routing table.** Each receiver already
does its own repo matching and no-ops cheaply on irrelevant pushes: argocd-server matches the pushed
repo against Application sources (a HelmCharts push matches none), the applicationset-controller
against its generators (a deploy-repo push matches none). Routing by repository would add
per-migration relay configuration — a new deploy repo per migrated app, each an edit the relay must
not miss — to save one no-op in-cluster HTTP call per push. It would also have to be undone later:
D22's recorded upgrade path (matrix generator) explicitly needs deploy-repo pushes reaching the
applicationset-controller too. Duplication is correct today and already correct for that future.

**When a receiver is down or slow: fail fast, no buffer, no retry.** Both legs concurrent; both 2xx
→ 200 to GitHub; anything else → 502 naming the leg. GitHub does **not** auto-redeliver failed
repository-webhook deliveries — redelivery is manual, available for 3 days — so failing fast buys
visibility, not retry storms: the miss shows red in Recent Deliveries, which is precisely the ledger
D6 already leans on, now preserved end-to-end for both receivers. Redelivery re-fans-out to both;
the receiver that already processed it refreshes again harmlessly — idempotent, so both-or-502 is
safe. A relay-side queue would add state, reordering, and a second place where a delivery can
silently die, to improve on an accepted consequence (#507 exists if the stale-but-green cost ever
chafes). Per-leg timeout ~4 s keeps worst case inside GitHub's 10-second window.

## 4. Placement — ArgoCDDeploy's chart, image from DockerImages

**Recommendation: source + Dockerfile in DockerImages (`registry:5000/webhook-relay:<n>`, the
existing pipeline); Deployment/Service/secret-reference in ArgoCDDeploy's wrapper chart, namespace
`argocd-prd`, public vhost via `nginx.webathome.org/server-name` + `is-public: "yes"` on the relay's
own Service.** The public DNS record (suggest `hooks.webathome.org`) is a manual operator action,
like all public DNS here.

The bootstrap circularity is real but already solved by a lever Argo itself uses. The relay is a
*trigger* prerequisite, not a render or sync prerequisite — Argo's manual refresh/sync reads git
without any webhook. So: at slice 009's one-time manual `helm install`, the relay comes up with Argo
*before* the registry hook is created — ordering is perfect, nothing to bootstrap separately. In
steady state, ArgoCDDeploy changes are **manual syncs forever anyway** (D3's `autoSync: false`,
permanent), so relay upgrades inherit exactly Argo's own posture at zero added ceremony. The
pathological loop — relay broken, its fix pushed, the push's webhook dropped — resolves with the
same manual sync any Argo upgrade takes.

Against the HelmCharts alternative: D43 says don't add to HelmCharts, and each addition is one more
later migration. The charts.home precedent doesn't transfer — charts.home is a *render-time*
prerequisite for every migrated app including ArgoCDDeploy itself, a hard cycle if Argo-managed; the
relay's cycle is soft and manually breakable. And a relay deployed independently of Argo buys
nothing: it serves nothing when Argo is absent. A dedicated `WebhookRelayDeploy` repo is
over-machinery for one Deployment.

## 5. Slice sizing — split it out; 009 depends on it

**Recommendation: a separate slice, shaped exactly like 007** (image + credentials as a standalone
dependency of 009). 009 is already the largest slice in the set — the operator explicitly kept
A.4+A.5 whole at triage, and the relay is *new* build work landed on it since (O3 was recorded as a
decision to make, not a service to build). It belongs apart because it has a different repo
(DockerImages), a different review focus (the estate's one new internet-facing surface deserves
review that isn't buried under eleven proof items), and independent testability — HMAC verification,
fan-out, both-or-502, and every refusal are provable with unit tests and a local run against stub
receivers before Argo exists. It can run in parallel with nothing blocking it but the webhook secret
value.

Cut line: the relay slice delivers the DockerImages image with its tests, the chart fragment
authored in ArgoCDDeploy (proven by `helm template`), and the O3/D39 doc updates (relay URL becomes
the registered hook URL; decisions.md closes O3). Slice 009 deploys it at bootstrap and gains two
small proof items on top of its existing item 8: (a) a real GitHub delivery through the public URL
lands 200 with both legs green; (b) the partial-failure drill — scale one receiver to zero,
redeliver, see red in Recent Deliveries naming the dead leg, restore, redeliver green. That drill is
the whole design proving its one important property: **a missed delivery is always visible where it
can be redelivered.**

## Sources

- GitHub — handling failed webhook deliveries:
  https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries
- CVE-2024-40634 (Argo CD webhook DoS): https://github.com/advisories/GHSA-jmvp-698c-4x3w
- CVE-2025-59537 (Argo CD Gogs webhook crash): https://github.com/advisories/GHSA-wp4p-9pxh-cgx2
- nginx mirror throttling: https://alex.dzyoba.com/blog/nginx-mirror/
- nginx mirror delay thread: https://mailman.nginx.org/pipermail/nginx/2018-September/056765.html

## Verification notes carried from the consult

nginx-configurator's template and annotation vocabulary were read from source
(`/work/DockerImages/nginx-configurator/app/{template.j2,annotations.py}`) — no per-service config
escape hatch exists. Receiver no-op behaviour on irrelevant pushes (argocd-server matching
Application sources, applicationset-controller matching generator repos) is stated from knowledge of
Argo's webhook handlers, **not** verified against the pinned version — it is not load-bearing for
correctness, only for the "duplication is cheap" argument, and becomes a trivial observation during
009's proof item 8.
