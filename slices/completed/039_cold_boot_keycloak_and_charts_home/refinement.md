# Slice 039 — refinement

## D1 — How far the documented charts.home rebuild bootstrap goes: desk-checked, or rehearsed on a throwaway cluster

**Context.** Every Argo-managed app takes the homelab-shared library from charts.home, and "charts.home down means no new syncs" is an accepted estate-wide dependency. At triage you approved a one-render bootstrap for a rebuilt cluster — render the charts deploy repo by hand from a Charts checkout, apply it, let Argo adopt it — and said a rebuild has little value at the moment. That premise no longer holds. For Argo's repo-server to fetch charts.home on a freshly rebuilt cluster, six Argo-managed releases must already run, in order: External Secrets, the CephFS CSI driver, the registry, dnsmasq (the .home DNS), nginx (the TLS front door), then charts itself — plus step-ca and the RBD CSI driver only if nginx's stored certificates are lost. Every one of them takes the library from charts.home. The vendoring in two repos never made a rebuild work either; it covered two of six.

**The ask.** Make a rebuild's charts.home bootstrap work by hand, documented — "if this can be made to work in a decent manner, then that is enough for me."

**Background.** Rendering a release by hand from a Charts checkout works (tested for the charts repo only). Four of the six need persistent volumes their Argo Terraform hook normally creates; the hooks' state lives in the TerraformState repo, so you could run a repo's Terraform by hand from srviac, outside the cluster — not verified. There is a cycle: External Secrets reaches OpenBao by a name only dnsmasq serves, dnsmasq needs a CephFS volume, and the CephFS driver's credentials come from External Secrets; hand-staging two Secrets breaks it. Argo CD itself installs without charts.home (its runbook already says how), and then every Application fails to render until charts.home answers.

**Why yours.** What you approved as one render is a six-release chain; whether that is still "decent", and how much proof it gets, is yours.

**Recommendation.** A rebuild section in the runbooks that maps the chain in order (the six releases, the two conditional ones), gives the one per-release recipe — package the library from a Charts checkout into the repo, render without hooks, apply; where a release needs a volume, run its Terraform by hand from srviac first; hand-stage the two Secrets that break the cycle — and ends with Argo adopting the rest on its first sync. Desk-checked, not rehearsed: every chain repo is rendered offline from a Charts checkout, and a server-side dry run of each hand render against live prd shows the apply matches what Argo already owns. Trade-off: an unrehearsed procedure for a rare event — its first real use will find gaps. Not verified: running a hook's Terraform by hand from srviac; Argo adopting hand-applied objects cleanly on first sync (its annotation tracking says it should).

**The other way.** Rehearse it end to end on a throwaway cluster on the scratch fleet: proves it, at several more phases and operator-run Terraform and Ansible for a scenario you value little.

**If this is wrong.** On a real rebuild you debug the procedure live, with charts.home and everything behind it down; no data at risk.

**Operator.** Agreed. (chat, 2026-10-03)

## D2 — Keycloak availability: leave it at one replica

**Context.** Keycloak runs as one replica with a Recreate strategy, no disruption budget and no anti-affinity. The card's other availability items are already done: the registry-retention slice moved the pull policy to IfNotPresent and pinned the image by a per-build tag instead of a digest. The outage of 2026-09-25 was not a node or replica problem: a power cut took all three Proxmox hosts down, and on restart Keycloak's pinned image digest had been garbage-collected from the in-estate registry, so the pod sat in ImagePullBackOff until it was repinned three hours later. A second replica would have hit the same missing image. That cause is fixed.

**The ask.** The card's availability item: whether Keycloak gets a second replica, a disruption budget and anti-affinity, so that Keycloak down does not take the estate with it.

**Background.** Keycloak already runs Infinispan with JDBC_PING discovery through the shared Postgres, so a second replica should cluster without config changes — not tested. The headless discovery Service the card cites is unused. Prd has four nodes with memory headroom; a second 768Mi request fits.

**Why yours.** The card's headline is "Keycloak down must not take the estate with it", and you could want HA regardless of what caused the last outage.

**Recommendation.** No change to Keycloak's replicas or strategy. What remains is node loss or a drain, where Keycloak reschedules within minutes and the break-glass paths (D3) cover admin access. Trade-off: a node failure still drops SSO for a few minutes.

**The other way.** Two replicas, a disruption budget of one, spread across nodes — should cluster as-is (not tested); costs another 768Mi request, a Keycloak deploy-repo change and a clustering test, and upgrades across Keycloak minor versions still restart everything.

**If this is wrong.** A node loss takes SSO down for minutes; apps fail fast, as already accepted.

**Operator.** Agreed. (chat, 2026-10-03)

## D3 — Break-glass: document the paths that exist, store nothing new

**Context.** During the outage every SSO admin UI was unusable, and Argo CD being among them blocked you mid-incident. The card's client list is wrong for two: Headlamp logs in with a Kubernetes service-account token, and Prometheus has no SSO. Grafana and pgAdmin keep a local login form; Guacamole likely does (not confirmed). OpenBao does not depend on Keycloak. The cold-boot runbook already carries a two-line "Argo CD without Keycloak" note, nothing on Jenkins, and nothing on where Argo's password lives.

**The ask.** Make sure Argo CD's local admin credential is reachable without Keycloak, decide the same for Jenkins, and document both in the cold-boot runbook.

**Background.** Argo CD's local admin is enabled; its password sits in the chart-minted initial admin Secret, which exists live on prd and is recorded nowhere else, not in OpenBao. Your admin kubeconfig is certificate-based, so the password is readable without Keycloak while the Kubernetes API is up. The runbook's fallback — write a new bcrypt hash into Argo's secret if the initial one is gone — has never been exercised. Jenkins' SSO plugin has an escape hatch, a local username and password login alongside SSO, and a local admin user exists (tooling uses its API token, which is in OpenBao); whether you hold that user's password is unknown (F1).

**Why yours.** Where a break-glass credential lives is your risk.

**Recommendation.** The cold-boot runbook documents Argo CD (read the chart-made admin Secret with the certificate-based admin kubeconfig; on a rebuild the install mints a fresh one) and Jenkins (the escape-hatch local login as the admin user), plus one line each on the other SSO clients' fallback (Grafana's and pgAdmin's local login, Headlamp's token, Guacamole if confirmed). The test phase has you log in once by each path with Keycloak's login bypassed, so both are proven. No new secret storage. Trade-off: Argo's password lives only in the cluster, so if that Secret is deleted the fallback is the never-exercised hash reset.

**The other way.** Manage Argo's admin password from OpenBao through External Secrets — durable and known across reinstalls, at an Argo CD deploy-repo change and one more credential to manage.

**If this is wrong.** In a Keycloak outage you are locked out of Argo or Jenkins until you go in through kubectl.

**Operator.** Agreed. (chat, 2026-10-03)

## Open facts — questions only you can answer

**F1.** Do you hold Jenkins' local admin password (the escape-hatch login), and where — and do you keep Argo CD's admin password anywhere outside the cluster? Settles whether the runbook points at your copy or the plan needs a reset step.

**Operator.** "Yes, I do have the Jenkins' local admin and Argo CD's admin password. I keep these things in RoboForm. It could be I'm missing one or two. I just recently stored the Argo CD admin password in RoboForm." (chat, 2026-10-03)

## Settled

- The "template fix" the Keycloak card points to (four template-based apps crash-loop at startup while Keycloak is down) was closed Won't Do on 2026-09-30 — crash-looping while the IdP is down is accepted fail-fast — and nothing in this slice reopens it.
- The slice cites a commit for the registry's deploy repo that does not exist; the vendoring commit there is a different one, the charts deploy repo's cite is right, and both repos still commit the 0.3.1 library tarball.
- The revert is a forward change to the shape every other deploy repo has (tarball gitignored, the dependency build step in lint and test, the check script removed), not a git revert — later commits touched the same files; the Charts README paragraph and the argo-cd design doc's vendoring note go with it, and the design doc's accepted-dependency caveat is restated without the vendoring. That the vendoring never covered a rebuild strengthens it.
- Consequence to confirm: once reverted, a broken charts.home release can no longer be repaired through Argo while charts.home is down — it is repaired by hand with the same recipe, or a rollout undo.
- No Ansible change to break the External Secrets/DNS cycle (such as pinning OpenBao's name in CoreDNS); the rebuild procedure hand-stages the two Secrets instead, and a power-cut cold boot is unaffected because the Secrets survive in the cluster.
  **Reversed** after the desk check: CoreDNS pins OpenBao's name instead, which removes the loop (one hand-staged Secret left, External Secrets' own). **Operator.** "Go" (chat, 2026-10-03)
- Keycloak's cold-start chain — the shared CNPG Postgres cluster through its pooler, the registry for the image unless cached on the node, the 100Mi CephFS themes volume made by Terraform, nginx for its public hostname — is written into the existing cold-boot runbook's Keycloak step, and into the rebuild section where its volume is Terraform-made.
- Alerting on Keycloak down is the alerting slice, not this one.
- Size: about four implementation phases plus the test and doc phases — the forward revert in the charts deploy repo and in the registry deploy repo, the rebuild bootstrap procedure in the Ansible runbooks with its desk check, break-glass and Keycloak's chain in the cold-boot runbook; plus a Charts README paragraph and the argo-cd design doc in AnsibleSpecs. Repos: ChartsDeploy, RegistryDeploy, Ansible, Charts, AnsibleSpecs; KeycloakDeploy only if D2 goes the other way, ArgoCDDeploy only if D3 goes the other way.

## Outcome

**Not planned or run as a slice.** The operator asked whether the slice was still worth one
("Is this slice sized? Writing the runbook you can do now.") and, on the proposal to do the
revert ad hoc as well and close the card, said "Go" (chat, 2026-10-03). Delivered in the
planning session: Ansible 1588a7f (cold-boot break-glass and Keycloak's chain), f9d2e08 (the
CoreDNS pin; takes effect at the operator's next site-k8s.yml), 3c9ca32 (cluster-bootstrap
runbook and scripts/argo-hand-render.py, desk-checked against prd, not rehearsed); ChartsDeploy
69ecb9f and RegistryDeploy e53c36b reverts; Charts cfae346 README; AnsibleSpecs 07c9d5b argo-cd design.md.
