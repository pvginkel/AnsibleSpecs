# Internal TLS everywhere — registry first (TLS + push auth), then the HTTPS sweep

**One line:** Put the container registry on step-ca TLS with authenticated pushes (review
C3 — the estate's weakest security link), and fold in the standing "all internal services
must become HTTPS" ambition (Triage card #47) as the estate-wide sweep the registry work
leads.

Triage sources: 2026-07 IaC review C3 (`../../reviews/2026-07-iac-review/findings.md`);
Triage card **#47** "All internal services must become HTTPS" (Ansible, no description —
absorbed here). Operator disposition: "Registry TLS via step-ca, then push auth:
obviously yes."

## Review C3 (abstract, verified)

`registry:5000` has no TLS and no auth. `iac` pulls `registry:5000/iac:latest` with
`--pull=always` and runs it **with every secret the estate has** (`IaCAgent/bin/iac:15,40`);
kaniko pushes over the same channel; the Jenkins agent floats
`jenkins/inbound-agent:latest` from Docker Hub. Anything with LAN position that can spoof
or push to the registry owns the estate — the code-delivery channel bypasses the otherwise
well-reviewed secrets architecture. step-ca (internal-tls slices, completed) makes TLS
feasible now; push auth is the larger lift: kaniko push creds, containerd/docker pull
trust across the fleet (k8s nodes' registry-mirror config in the microk8s role, srviac's
docker daemon, dev workstation), `etc/docker/daemon.json`'s `insecure-registries` removal
(both copies — IaCAgent + iac_agent role), and the registry chart itself (HelmCharts).
Pull can stay unauthenticated per the review's DockerImages advice ("htpasswd for push at
minimum; pull can stay open").

## Card #47 (absorbed)

"All internal services must become HTTPS" — no description; read together with existing
doctrine it means: finish the internal-TLS rollout beyond the v1 scope.
`decisions.md` §"Internal TLS / homelab CA" already records the mechanism and the
leftover set: "Everything else (dnsmasq UI, other in-cluster service endpoints, IoT,
printers) stays on snakeoil / self-signed until later sweeps; in-cluster services migrate
by flipping their Ingress annotation when they get touched anyway." This bundle is that
later sweep, done deliberately instead of opportunistically. Inventorying the remaining
plain-HTTP endpoints is part of the work (registry, tfmirror.home?, dnsmasq management
UI/API surfaces, any NodePort/LB services bypassing the ingress).

## Dependencies / interplay

- **Blocks OCI chart hosting** for the ArgoCD migration (`../argocd_migration/`) — don't
  point a deployer at an unauthenticated writable registry.
- Interacts with `../ci_quality_gates/` (kaniko stages gain push creds) and the
  version-poller/registry-cleanup tooling (API access over TLS).
- The iac shim's `--pull=always` coupling (review I5) stays as-is by operator decision
  (workstation is the break-glass) — TLS/auth changes the trust, not the availability,
  story.
- Learning value called out in the review: end-to-end supply-chain integrity (cert
  issuance, containerd/docker trust, kaniko creds) — a natural slice.
