# Slice 038 — ArgoCDDeploy's render gate refuses a widened role:readonly, and a Terraform-only push to any deploy repo reaches terraform apply

## Requirements / rulings

- R1. **ANS-178 — the render gate refuses a widened `role:readonly`.** The card: "tests/render-chart.py
  check_readonly_account (:1229-1255) checks only the policy lines whose subject is `kubecoder`
  and `policy.default`. [...] A line that widens the role the account is bound to passes the
  gate. [...] Fix: check_readonly_account also refuses any policy.csv line whose subject (field 1)
  is `role:readonly`." The wrap-up (2026-09-30) widens it: "policy_lines reads only the
  `policy.csv` key, while Argo CD also loads every `policy.*.csv` key of argocd-rbac-cm into the
  same policy [...] What a fix takes: in that one function, read the lines of policy.csv and of
  every policy.*.csv key, refuse any line whose subject is role:readonly, and hold the
  kubecoder-subject check to all of them; witnessed by the entry's two lines, and an overlay key,
  turning a scratch render red." The card's two lines: `p, role:readonly, applications, sync, */*, allow`
  and `g, role:readonly, role:admin`.
- R2. **ANS-179 — a Terraform-only FieldnotesDeploy push reaches `terraform apply`.** The card's
  title: "FieldnotesDeploy: a push touching only terraform/ never triggers an Argo CD sync, so its
  PreSync-hook Terraform apply never runs". The card: "it will recur for any future
  FieldnotesDeploy push that changes only terraform/ or only tfvars, with no accompanying
  chart/values change."
- Ruling (2026-10-03, D1 — operator: "D1/D2 are agreed as is."): **the fix lives in the
  homelab-shared library.** The library's hook template (`homelab-shared.tf-presync-hook`, Charts
  `charts/homelab-shared/templates/_tf-presync-hook.tpl`) also renders a small ordinary, non-hook
  ConfigMap carrying the synced commit (`hook.revision`). Every push then changes the render, so Argo
  auto-syncs and the hook runs terraform apply on every commit — doc and test commits included.
  No manual step, no gate, no new credential. The card pass's option (a) (a hash of terraform/ in
  config/*/values.yaml) is not built: it needs the same chart object plus a manual step and a
  staleness gate, and puts a non-per-stage value into per-stage config (argo-cd D12).
- Ruling (2026-10-03, D2 — same words): **rolled out estate-wide in this slice.** After
  FieldnotesDeploy proves the new library version live, every other deploy repo that pins
  homelab-shared is bumped to it, in batches, as its own phase. Before pushing, that phase lists
  any app whose terraform/ or config/*/*.tfvars changed since its last sync operation (a commit
  the defect left unapplied), since the bump push will apply it; those are reported in the
  phase's done-record. Pushing these deploy repos — and with it one Argo sync and one hook
  terraform apply per app on prd — is authorized by this ruling; it is the same effect a daily
  image-pin commit has.
- Ruling (2026-10-03, settled and shown to the operator): **the live proof.** The test phase
  pushes FieldnotesDeploy's library bump, then a commit that only edits a comment in terraform/;
  Argo must sync fieldnotes-prd at that commit (`status.operationState` / `status.history` at the
  new SHA) and the hook Job `tf-presync-fieldnotes-prd` must run, with a no-op apply on prd — no
  Terraform state change.
- Ruling (2026-10-03, settled and shown to the operator): **the Argo CD decision register**
  (`/work/AnsibleSpecs/argo-cd/decisions.md`, Terraform and the PreSync hook section) gets a new
  decision recording that every push syncs and runs the hook, and why. That is a doc task, so it
  is a phase.
- Ruling (2026-10-03): the registry-owned hook (one global pin instead of per-repo pins) was
  weighed and parked — operator: "Ow this feels far too cumbersome. Let's stick to the plan. If
  it bothers me again, I'll revisit this." Filed as ANS-199 (Later). Not in this slice.

#### Grounding (verified 2026-10-03, binds the plan)

- R1's premise holds. `policy_lines` (ArgoCDDeploy `tests/render-chart.py`, now :1240) reads only
  `rbac["policy.csv"]`; `check_readonly_account` (now :1249-1276) checks only lines whose field 1
  is `kubecoder`, plus `policy.default`. The card's line numbers are stale by ~20 lines. The
  committed policy (`config/prd/values.yaml`, `configs.rbac.policy.csv`) has exactly
  `g, pvginkel@gmail.com, role:admin` and `g, kubecoder, role:readonly`; nothing else names
  role:readonly, so refusing every role:readonly-subject line keeps the committed render green.
  The gate runs as `cexec iac tests/render-chart.py` (after `cexec aac-tools chart-deps`).
- R2 is estate-wide, not FieldnotesDeploy-only. 48 of the 49 `*Deploy` repos carry
  `chart/templates/tf-presync-hook.yaml` and `terraform/`; only ArgoCDDeploy has no Terraform.
  Their sync policy comes from the ArgoCDDeploy registry (`releases/values.yaml`): automated,
  prune: true, selfHeal: false. Every consumer read pins homelab-shared exactly at `0.3.1`
  (argo-cd D17), and the deploy repos vendor no tarball (Chart.yaml + Chart.lock only; the
  repo-server runs helm dependency build against https://charts.home).
- Why the defect happens: hooks are excluded from Argo's diff; terraform/ and tfvars sit outside
  `chart/`, so Helm's `.Files` cannot hash them; auto-sync fires only on OutOfSync (Argo CD
  v3.5.1, `controller/appcontroller.go` autoSync: "Skipping auto-sync: application status is
  Synced"). No Argo sync option forces a sync on an identical render.
- `hook.revision` is passed by the registry as the Helm parameter `$ARGOCD_APP_REVISION`, which
  Argo substitutes per commit (argo-cd D30/D56; this is how the hook Job already gets its SHA).
  In a multi-source upstream app the companion `chart/` source is built at the deploy repo's own
  revision (D56), so the same holds there.
- Jenkins holds no Argo credential and no deploy-repo pipeline calls Argo (argo-cd D1); deploy
  repos' only pipeline is `Jenkinsfile.architecture`, so each deploy-repo push also queues one
  Jenkins architecture build — batch the D2 pushes (pushing all ~47 at once loads Jenkins and
  re-triggers Architecture builds).
- The ChartsDeploy app (serves charts.home) consumes homelab-shared too — a known bootstrap
  trap (argo-cd D17; slice 029 close-out). Its bump is the same one-line change; backlog slice
  039 (cold boot of Keycloak and charts.home) touches that repo, so keep its change to the pin.
- Exposure, measured: one Terraform-only commit did real work in the 7 locally cloned deploy
  repos (FieldnotesDeploy c592e49, 2026-09-30, applied by the next pin push the same evening);
  the other ~41 were not counted.

## Ordering constraints

- The library change is published to charts.home before any deploy repo pins the new version
  (a pin to an unpublished version breaks that app's render).
- FieldnotesDeploy proves the new version live before the estate rollout pushes.

## Not in scope

- Moving the Terraform hook out of the per-repo pin (registry-owned hook, a floating library
  range, or moving the hook image tag to a registry parameter) — parked as ANS-199.
- The app-facing homelab-shared helpers (Ceph PV/PVC, node affinity, ExternalSecrets) — unchanged.
- ArgoCDDeploy has no Terraform and gets no bump.
