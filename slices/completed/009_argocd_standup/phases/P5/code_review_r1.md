# Code review — slice 009, phase P5, round 1

Branch `phase/009-P5` @ `42b0860`, diff `008126db..HEAD` (4 files, +300).
Gate green on this commit (`kc project test`, `phases/P5/gate_r1.log`), taken as an input.

## Readiness

**Ready to merge.** The phase's outcome holds end to end, and I checked it against the things that
could falsify it rather than against the plan's prose: the relay's environment matches the image's
own contract in source (`WEBHOOK_SECRET`, `ARGOCD_WEBHOOK_URL`, `APPLICATIONSET_WEBHOOK_URL`,
`LISTEN_ADDR` defaulting to `:8080`, routes `/api/webhook` and `/healthz` —
`/work/DockerImages/webhook-relay/src/internal/config/config.go:25-28`,
`internal/relay/relay.go:24,29,89-90`); both legs resolve against the render's real Services
(`argocd-prd-server` publishes `http 80 → 8080`, `argocd-prd-applicationset-controller` publishes
`http-webhook 7000 → webhook`, and the AS controller is started with `--webhook-addr=:7000`); the
pinned tag exists (`registry:5000/v2/webhook-relay/tags/list` → `["2485","latest"]`); the exposure
annotations match the configurator's actual semantics — `target-port` names the *Service* port
because the proxy target is built as `<service>.<namespace>.svc.cluster.local:<target-port>`
(`/work/DockerImages/nginx-configurator/app/nginxconfigurator.py:155-163`), and `is-public: "yes"`
takes the certbot branch with no RFC1918 block (`:139-146`, `app/template.j2:39-45`). I also checked
the two things most likely to break this silently and found them clean: nothing in the render blocks
the relay's legs — `argocd-prd-server`'s NetworkPolicy is `ingress: [{}]` and no policy is rendered
for the applicationset-controller — and the shared nginx allows the payloads
(`client_max_body_size 500M`, `/work/HelmCharts/charts/nginx/files/conf.d/10-http-configuration.conf:1`).
The new gate is not decorative: I mutated the `ARGOCD_WEBHOOK_URL` port to 443 and the Service port
to 9090 in a scratch copy and both went red on their own assertions, exit 1.

Three findings, all advisory, none blocking. Two are about the phase's own claims (a comment whose
stated failure mode does not occur, and a gate invariant with a one-keystroke hole); one is a posture
observation on the estate's only internet-facing pod. Nothing here should cost a fix round.

## Findings

### F1 — the internet-facing pod runs as root with the cluster's default token, which is not what the design says it holds · Minor · advisory · anchor: none

`chart/templates/webhook-relay.yaml:41-49` gives the pod no `securityContext` at either level and
does not touch `automountServiceAccountToken`, so it runs under the namespace's `default`
ServiceAccount with its token mounted, as UID 0 (the image sets no `USER` —
`/work/DockerImages/webhook-relay/Dockerfile`, `FROM debian:bookworm-slim`), with a writable root
filesystem and the default capability set. The consult this phase is built to — authoritative per
the plan's P5 bullet 1 — states the opposite as the reason the relay exists: *"what an
unauthenticated caller can reach is an HMAC over raw bytes in a binary holding no credential toward
GitHub and none toward the cluster"* and, D41-style, *"compromise of the relay pod yields the shared
HMAC secret … The relay holds nothing else; that is the whole point"*
(`015 attachments/webhook-relay-consult.md` §2). As deployed it also holds an authenticated cluster
identity. The contrast is inside this one render: every other pod the chart produces
(`argocd-prd-server`, `-repo-server`, `-application-controller`, `-applicationset-controller`,
`-notifications-controller`, `-redis`) carries a container `securityContext` from the upstream
chart's defaults; the relay is the only pod without one, and the only one reachable from the
internet.

The exposure is bounded — `default` has no RBAC in this namespace, the binary never parses the
payload, and this estate's images not setting `USER` is a settled DockerImages convention (015
review r1, P1) — which is why this is advisory rather than a fix. It is the deployment-side half of
a claim the design makes, and this chart is where that half is decided.

Confidence: high on the facts, medium on the weight.

### F2 — the render's "only one public Service" invariant is keyed to the spelling `"yes"`, and the configurator also honours `"true"` · Minor · advisory · anchor: none

`tests/render-chart.py:871-877` collects the internet-facing Services as those whose
`nginx.webathome.org/is-public` annotation equals the literal `"yes"`, and asserts that list is the
relay alone — the check the done-record calls out as pinning "the whole exposure claim, not the
relay's half". The configurator reads that annotation through
`AnnotationMetadata.parse_bool`, which is `value in ("yes", "true")`
(`/work/DockerImages/nginx-configurator/app/annotations.py:191-192`). So a Service annotated
`is-public: "true"` is internet-facing in the cluster and invisible to this assertion: the gate
would report the relay as the only public surface while a second vhost had a Let's Encrypt
certificate and no RFC1918 allow block. `check_server_exposure`'s companion assertion
(`:649-653`, `is-public == "no"`) has the same shape from the other side — argocd-server annotated
`"false"` would still be internal in fact, so that one fails safe, but the exclusivity claim above
does not.

Nothing today spells it `"true"`: the render has exactly two annotated Services and both use the
canonical spelling. This is coverage of a claim the slice leans on (V10: "the relay … is the only
internet-facing surface"), not a live defect.

Confidence: high.

### F3 — the comment justifying port 80 names a failure that does not occur · Minor · advisory · anchor: none

`chart/templates/webhook-relay.yaml:59-62` explains the `:80` leg as *"a leg pointed at 443 fails
the whole delivery on the TLS handshake"*, and `tests/render-chart.py:172-176` restates it as *"a
leg pointed anywhere else fails every delivery"*. With `server.insecure: true` the upstream chart
renders argocd-server's Service as `http 80 → 8080` **and** `https 443 → 8080` — both ports target
the same plain-HTTP container port — so an `http://argocd-prd-server…:443/api/webhook` leg reaches
the identical listener and succeeds. No TLS handshake is attempted, and the "does not follow
redirects" clause has nothing to redirect either, because the insecure listener issues none. The
slice already recorded the accurate version at close-out **B3**, where the handshake failure is
attributed to an `https://` *scheme* against a listener that no longer serves TLS — not to the
port number.

Choosing 80 remains right (it is the port the vhost and every other in-cluster caller use, and it
survives `server.insecure` ever being reconsidered), and the gate pins it either way, so following
these words harms nothing — the reason attached to them is simply not the reason.

Confidence: high.

## Checked and clean

Recorded so a later round does not re-derive them:

- **Both legs, against the render, not the plan.** `argocd-prd-server` publishes port 80;
  `argocd-prd-applicationset-controller` publishes 7000 and the container is started with
  `--webhook-addr=:7000`. `check_relay_receivers` binds scheme, path, host and port to the Services
  in the same render, so an upstream port move fails the gate.
- **Nothing in-cluster blocks the fan-out.** The upstream chart's `global.networkPolicy.create`
  default is `true` and five policies render, but argocd-server's is `ingress: [{}]` and no policy
  is rendered for the applicationset-controller (`applicationSet.metrics.enabled` and the ingress
  switches are all off), so both legs are permitted. Nothing selects the relay's own pods.
- **The secret is one object with three readers.** `secretKeyRef` → `argocd-webhook#githubSecret`,
  the same object and key `argocd-secret`'s `webhook.github.secret` reference names; the gate
  asserts that equality rather than the names separately.
- **The pin is real.** `2485` is present in the registry, and the gate's regex refuses anything but
  `registry:5000/webhook-relay:<digits>`, so `latest` — which the registry also holds — cannot slip in.
- **Roll behaviour.** `replicas: 2` with `maxUnavailable: 0` and a default `maxSurge` of 25 % → one
  surge pod; the readiness probe is on the relay's own `/healthz`. The Service selector matches the
  pod labels it renders, and both objects land in `argocd-prd`.
- **Gate non-vacuity.** Two mutations run against a scratch copy, each red on its own assertion:
  `ARGOCD_WEBHOOK_URL` → `:443` ("reaches argocd-prd-server on 443, not the 80 that answers the
  webhook") and the Service port → 9090 ("the vhost proxies to port '8080', which
  Service/argocd-prd-webhook-relay does not publish: [9090]").
- **Not findings, deliberately:** no `resources` on the relay container — every pod in this render
  has `resources: {}`, so it matches the local norm; no pod anti-affinity or PDB — a node-level
  outage turns deliveries red in Recent Deliveries, which is the design's accepted and stated
  failure mode; the relay not restarting on a webhook-secret rotation — rotation is nowhere in this
  slice, the failure is visible at GitHub, and the estate runs no reloader.
