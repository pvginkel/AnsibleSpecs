# IaC estate review — July 2026

Full review of the IaC estate: **Ansible** (incl. `terraform/`), **HelmCharts**,
**IaCAgent**, **HomelabTerraformProvider**, and (lighter) **DockerImages**, plus
the cross-repo delivery system they compose. Conducted 2026-07-03 by six
parallel review agents (one per repo/area, one cross-cutting, one researching
the mid-2026 GitOps/IaC landscape); critical findings spot-verified by hand.

## The documents

| Doc | What it is |
|---|---|
| [findings.md](findings.md) | Consolidated per-repo + system-level findings, severity-ranked, with evidence |
| [gitops.md](gitops.md) | App note: Argo CD as a **push-model** deployment for this estate — the design, the migration path, what it does and doesn't replace |
| [tech-radar.md](tech-radar.md) | Adopt / trial / hold guidance across the 2026 tooling landscape |

## Verdict

The estate is in genuinely good shape. Several practices are top-decile by
industry standards, not just homelab standards: the check-mode/drift-detection
discipline in the Ansible roles, the SSH host-CA trust model, the data-loss
safety engineering in the HelmCharts deploy harness (`prevent_destroy` +
Retain/claimRef + PV-reattach), the deliberately-cut bootstrap circularity, and
an OpenBao restore that has been **drilled and timed**, not just documented.
Organic growth has not produced rot — the repo boundaries mostly earn their
keep (one exception: IaCAgent should fold into Ansible), and the doctrine in
`decisions.md` is unusually honest about its own gaps.

The problems that do exist are concentrated, and almost all of them are small
to fix:

1. **The safety rails don't match the doctrine (critical, composite).**
   `decisions.md` claims `prevent_destroy` on srviac and the three srvvaultN
   plus a plan-stage guard for both. In reality: zero `prevent_destroy` in
   `Ansible/terraform/`, the guard script protects only srviac, its jq match
   misses Terraform's *default* replace ordering (`["delete","create"]`), and
   the plan it checks is not the plan that gets applied (apply re-plans in a
   fresh container). Compounding it: **no OpenBao backup has ever shipped** —
   slice 005 is authored but not run. Today a bad `vms.tf` refactor pushed to
   main can destroy the secrets root unattended, with no restore artifact.
2. **Secrets stragglers outside the (otherwise principled) tiered design.**
   Worst: the step-ca intermediate CA + SSH host CA encryption passwords are
   committed k8s Secrets in HelmCharts, next to the encrypted keys they
   protect — the homelab's root of trust, in every clone and on the
   unauthenticated LAN git mirror. Plus a plaintext GitHub PAT and a few
   passwords in configs, fleet SSH private keys in Obsidian, plaintext tfstate
   in TerraformState's pre-encryption git history.
3. **Process gaps in a push-to-prod pipeline.** No lint/validation gate
   anywhere on the push path (Ansible, Terraform, Helm, or the Go provider —
   which publishes untested binaries); versions float at almost every layer
   (upstream charts to latest-on-sight, TF providers `-upgrade` per deploy,
   galaxy collections `>=`); a failed HelmCharts deploy silently *consumes*
   the change that triggered it; alerting lives inside its own blast radius;
   Jenkins job config (crons, SCM bindings) exists only on a PVC.
4. **The prd Ceph fleet is managed in name only** — known (Phase 5 /
   microceph-prod), but it's the largest coverage asymmetry: no baseline, no
   drift detection, no orchestrated patching on the three storage nodes under
   everything, and hand-applied tuning accumulating uncodified.

**On evolution and new technology** — short version (long version in
[gitops.md](gitops.md) and [tech-radar.md](tech-radar.md)):

- **Adopt Argo CD, in push mode.** Your instinct is right and the poll
  objection is solved: auto-sync is a first-class *option* (`syncPolicy.
  automated.enabled: false`), and CI-triggered `argocd app sync` is a
  documented, supported pattern. Jenkins stays the deployer; Argo supplies
  drift *visibility*, health gating, rollback UX, and — via multi-source
  Applications — the charts-live-with-their-repos property you're missing.
  It's also the highest-career-value item on the board. Your harness's TF
  substrate phases are *not* replaced and should stay.
- **The supporting cast is adoptable independently, now:** update-train
  batching for the layers that today float onto prd unattended (charts, TF
  providers), trivy scanning as the cadence-interrupt line, `helm lint` +
  kubeconform + ansible-lint gates, a dead-man's switch for scheduled jobs,
  registry TLS/auth (the unauthenticated HTTP registry is the estate's
  weakest security link — it delivers the code that runs with all secrets).
- **OpenTofu: migrate eventually, no urgency.** Its native state encryption
  (keys via OpenBao!) is a made-for-this-estate fit that could delete the
  sops layer. Try it on the scratch root first.
- **Skip:** Crossplane, kro, Timoni, cdk8s, Dagger, Atlantis (PR-workflow
  tools don't fit commit-to-main doctrine).

## Action plan

**This week — close the critical window (all small):**
1. Fix `check-protected-vms.sh` (`.change.actions | contains(["delete"])`),
   extend the protected list to `srvvault1-3` (decide: ceph/k8s fleets too),
   add the `prevent_destroy` blocks doctrine already claims, and make the
   apply consume the checked plan artifact (one `iac -c` invocation).
2. Run slice **005** — commission the OpenBao backup pipeline; prove the
   round-trip.
3. Rotate + relocate the committed secrets: step-ca passwords → the
   ansible-vault materialisation path `decisions.md` already specifies;
   newsfilter/elasticsearch passwords → ESO; revoke the git-sync PAT.

**This month — process rails (small/medium):**
4. Lint/validate gates on the push pipelines: `ansible-lint` (+fix 6 findings,
   go strict) + `yamllint` + `--syntax-check`; `terraform fmt -check` +
   `validate`; `helm lint` + kubeconform render pass; `go test` before
   provider publish.
5. Put the prd-affecting float layers on the update train: upstream chart
   versions in `release.yaml` bumped as a batch (poller detects and reports;
   the train applies, dev soak → prd), TF provider constraints + drop
   `-upgrade`, de-duplicate the galaxy collections story. (Doctrine:
   cadence-based bulk update, not continuous proposals — see tech-radar.)
6. HelmCharts pipeline: per-release failure isolation (try/catch) +
   desired-state hash instead of edge-triggered changesets; make `deploy
   wait` failures fail the stage.
7. Dead-man's switch (healthchecks.io ping on success from drift/update
   jobs) + investigate why Scheduled Update failed 3 of its last 4 runs.
8. Secret-residue sweep: SSH keys out of Obsidian, KubernetesConfig deletion,
   TerraformState LAN-mirror exclusion + rotate creds in pre-encryption
   history, fact-cache out of /tmp.

**This quarter — structural (medium/large):**
9. **microceph-prod** slice — bring prd Ceph under management; biggest
   coverage gap, best remaining learning artifact (rolling storage-cluster
   orchestration).
10. Registry TLS (step-ca) + push auth; then trivy in DockerImages CI.
11. Jenkins jobs as code (JCasC/job-dsl for the IaC/DockerImages folders).
12. Argo CD pilot per [gitops.md](gitops.md) — including the
    one-chart-decoupling pilot that de-risks it.
13. Fold IaCAgent into `Ansible/support/`; master site-DR runbook; OpenBao
    lookup integration in Ansible (close the loop — provisioned superbly,
    never read from).

Natural next step when you've digested this: a `/triage` pass over the action
plan to turn accepted items into change-request bundles and slices. Items 1-3
arguably shouldn't wait for ceremony.
