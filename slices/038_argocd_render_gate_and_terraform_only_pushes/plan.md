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
- Ruling (2026-10-03, D2 — same words; sequencing per D4, review r1 F2 agreed): **rolled out
  estate-wide in this slice.** Every other deploy repo that pins homelab-shared is bumped to the
  new version in its own phase; when and how those bumps are pushed is D4's. The phase lists any
  app whose terraform/ or config/*/*.tfvars changed since its last sync operation (a commit the
  defect left unapplied), since the bump push will apply it; those are reported in the phase's
  done-record. Pushing these deploy repos — and with it one Argo sync and one hook terraform
  apply per app on prd — is authorized by this ruling; it is the same effect a daily image-pin
  commit has.
- Ruling (2026-10-03, review r1 F1 — operator: "Agree"): **a consumer's bump is its library
  version, wherever the repo states it** — the `chart/Chart.yaml` pin, its re-resolved
  `Chart.lock`, and any test of the repo's own that pins the library version (KubeCoderDeploy's
  `tests/render-chart.py` `LIBRARY`, checked by `check_library`; the reviewer found no other
  repo that hard-codes it). The rollout phase runs each bumped repo's own `kc project test`
  where the repo has one, and records the result in its ledger; "nothing but its pin" wording in
  the phases and verification.json becomes "nothing but its library version".
- Ruling (2026-10-03, settled and shown to the operator): **the live proof.** The test phase
  pushes FieldnotesDeploy's library bump, then a commit that only edits a comment in terraform/;
  Argo must sync fieldnotes-prd at that commit (`status.operationState` / `status.history` at the
  new SHA) and the hook Job `tf-presync-fieldnotes-prd` must run, with a no-op apply on prd — no
  Terraform state change.
- Ruling (2026-10-03, settled and shown to the operator): **the Argo CD decision register**
  (`/work/AnsibleSpecs/argo-cd/decisions.md`, Terraform and the PreSync hook section) gets a new
  decision recording that every push syncs and runs the hook, and why. That is a doc task, so it
  is a phase.
- Ruling (2026-10-03, D3 — operator: "Agree"): **the FieldnotesDeploy phase publishes the library.**
  It opens by pushing Charts' `main` — the library change already reviewed and merged — and waits
  until https://charts.home/index.yaml lists the new version before bumping FieldnotesDeploy's pin.
  That push is authorized by this ruling (it changes no app: every consumer still pins `0.3.1`).
- Ruling (2026-10-03, D4 — same word): **the deploy-repo pushes are the test phase's.** The rollout
  phase prepares every bump commit and its ledger and pushes nothing. The test phase pushes
  FieldnotesDeploy's bump, then the comment-only terraform/ commit, checks the live proof, and only
  then pushes the ledger's repos in batches — rebasing any repo whose origin moved and re-checking
  its pending-Terraform status just before its push.
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

## Task shape

pre-settled — R1's fix is spelled out by the card and its wrap-up (one function, the lines to
refuse, the keys to read), and R2's mechanism and reach are fixed by rulings D1 (a non-hook
ConfigMap carrying `hook.revision` in the library hook template) and D2 (estate-wide pin bump);
planning is transcription.

## Ordering constraints

- Slice 039's unpushed commits — Charts `cfae346`, ChartsDeploy `69ecb9f`, RegistryDeploy
  `e53c36b` — are on origin before the run starts (close-out action): otherwise P4's Charts push
  and the rollout's pushes carry them.
- P1 lands before P3: the library template's comment cites the decision P1 records, by the id
  P1's done-record gives.
- The library change is published to charts.home before any deploy repo pins the new version: a
  pin to an unpublished version fails `chart-deps` (the repo-server's `helm dependency build`,
  ArgoCDTools `aac-tools/image/chart_deps.py:100`) and breaks that app's render. P4 opens with
  that publish.
- FieldnotesDeploy proves the new version live before the estate rollout pushes. The pushes of
  the deploy repos are the test phase's, in this order: FieldnotesDeploy's bump (P4); then a
  commit that only edits a comment in its `terraform/` — the live-proof ruling; only once that
  proof holds, the repos in P5's ledger, in batches. Each deploy-repo push queues that repo's
  `AaC/<Repo>` architecture build, which re-triggers `AaC/Architecture`, and one Argo sync with
  one hook apply on prd. A repo whose origin moved after P5 (Jenkins' image-pin commits land
  daily) has its bump rebased onto it, and its at-risk check (P5) is re-read just before its
  push; an app that turns at-risk in between is reported in the test phase's record beside P5's
  list.
- ChartsDeploy is the rollout's last push, in a batch of its own: every other app's next render
  fetches the library from charts.home, so charts-prd's sync has to leave it serving every
  version (V08).
- ArgoCDDeploy (P2) may be pushed at any point: it syncs only by manual sync (argo-cd D3).

### P1 — The Argo CD decision register records that every deploy-repo push syncs and runs the Terraform hook ✅ DONE 2026-10-03

Target: ../AnsibleSpecs

`argo-cd/decisions.md`, section "Terraform and the PreSync hook" (`:477`), gains a Decided entry
for ruling D1 (2026-10-03, operator): the library's hook include also renders an ordinary,
non-hook ConfigMap carrying the synced commit, so every push to a deploy repo changes its render,
Argo auto-syncs it, and the PreSync hook runs `terraform apply` on every commit — doc and test
commits included.

- **The why** is the plan's grounding: hooks are outside Argo's diff; `terraform/` and the stage
  tfvars sit outside `chart/`, where Helm's `.Files` cannot reach; auto-sync fires only on
  OutOfSync and no Argo option forces a sync on an identical render; no deploy pipeline calls
  Argo and Jenkins holds no Argo credential (D1).
- **What was turned down, and the trade-off taken**, from the ruling: a hash of `terraform/` in
  `config/*/values.yaml` (the same chart object plus a manual step and a staleness gate, and a
  non-per-stage value in per-stage config, D12); the registry-owned hook (parked as ANS-199). An
  apply per push, mostly no-op, is the accepted cost.
- Entries it touches — the sync policy (D5, D46), the hook (D30), the exact library pin (D17) —
  are cross-referenced; one whose text it makes untrue is amended in the register's own
  `> **Amended …**` style.

The id is allocated at append time and given in the done-record.

**Done (P1).** `argo-cd/decisions.md` carries **D67 — Every push to a deploy repo syncs its app
and runs the Terraform hook**, last entry of "Terraform and the PreSync hook" (before "Promotion
and CI"). No existing entry amended: none of D5, D14, D17, D30, D46, D56 states anything D67 makes
untrue; D67 cross-references them instead.

Later phases:
- P3 — the template's header comment cites **D67** (argo-cd decisions.md); edited in place.

Record:
- D67 states the mechanism (non-hook ConfigMap carrying `hook.revision`, passed as
  `$ARGOCD_APP_REVISION`, per source in a multi-source app per D56), the why (hooks outside the
  diff; `terraform/` and `config/{stage}/*.tfvars` outside `chart/`, D12/D14; auto-sync only on
  OutOfSync, Argo CD v3.5.1; no pipeline or credential can start a sync, D1), what was turned down
  (terraform/ hash in per-stage values, D12; registry-owned hook, ANS-199) and the cost taken (a
  sync and an apply per push, mostly no-op).
- The ConfigMap's name is left to P3; D67 names no object.
- Gate: AnsibleSpecs has no manifest or linter (plain Markdown, README); checked D67 is unique.

### P2 — ArgoCDDeploy's render gate refuses a widened role:readonly, in every policy key ✅ DONE 2026-10-03

Target: ../ArgoCDDeploy

R1, as the card and its wrap-up pin it. Today `policy_lines` (`tests/render-chart.py:1240-1246`)
reads only `rbac["policy.csv"]`, and `check_readonly_account` (`:1249-1275`) holds only the lines
whose subject is the `kubecoder` account, plus `policy.default`. After this phase the check reads
the lines of `policy.csv` and of every `policy.*.csv` key of argocd-rbac-cm — Argo CD loads them
all into one policy (the wrap-up's citation: argo-cd `util/rbac/rbac.go` PolicyCSV) — refuses any
line whose subject is `role:readonly`, and holds the kubecoder-subject check to all of them.

- **The committed render stays green.** The committed policy (`config/prd/values.yaml:69-71`) is
  exactly `g, pvginkel@gmail.com, role:admin` and `g, kubecoder, role:readonly`; no committed line
  has `role:readonly` as its subject.
- **Witnessed red on a scratch render**, each line on its own on top of the committed binding:
  `p, role:readonly, applications, sync, */*, allow`; `g, role:readonly, role:admin`; and a
  `policy.*.csv` overlay key binding `kubecoder` to `role:admin`. The three reds go in the
  done-record.

**Done (P2).** ArgoCDDeploy 63c370f: `policy_lines` (`tests/render-chart.py`) reads every
argocd-rbac-cm key matching `policy.*.csv` (`policy.csv` included, as Argo's PolicyCSV joins
them); `check_readonly_account` holds the kubecoder-binding check to all of them and adds a
refusal of any rule whose subject (field 1) is `role:readonly`. `kc project test` green on the
committed policy.

Later phases:
- None changed.

Record:
- Reds witnessed by scratch edits of `config/prd/values.yaml` (restored; not committed), each
  `cexec iac tests/render-chart.py` exiting 1:
  - `p, role:readonly, applications, sync, */*, allow` → `FAIL: argocd-rbac-cm widens role:readonly
    by [('p', 'role:readonly', 'applications', 'sync', '*/*', 'allow')], and with it the kubecoder account`
  - `g, role:readonly, role:admin` → `FAIL: argocd-rbac-cm widens role:readonly by [('g',
    'role:readonly', 'role:admin')], and with it the kubecoder account`
  - `policy.overlay.csv: g, kubecoder, role:admin` → `FAIL: argocd-rbac-cm binds the kubecoder account
    by [('g', 'kubecoder', 'role:readonly'), ('g', 'kubecoder', 'role:admin')], not by role:readonly alone`
- The reds are not a standing self-check in the gate (close-out T1).

### P3 — homelab-shared's hook include renders a ConfigMap carrying the synced commit, as a new version

Target: ../Charts

Ruling D1. Today `homelab-shared.tf-presync-hook`
(`charts/homelab-shared/templates/_tf-presync-hook.tpl:34-91`) renders only hooks — the PreSync
RoleBinding (`:42-59`) and the PreSync Job (`:61-90`) — and its one per-commit value,
`hook.revision`, reaches only the Job's args (`:85`), which Argo leaves out of its diff. After
this phase the same include also renders a small ordinary (non-hook) ConfigMap carrying
`hook.revision`, so two commits of a deploy repo render differently and Argo auto-syncs every
push.

- **A consumer changes nothing but its library version** (ruling r1 F1). The one-line include
  every deploy repo carries (`chart/templates/tf-presync-hook.yaml`, e.g. FieldnotesDeploy's)
  stays as it is, and no new value is asked of it.
- **It lives with the app's own objects**, in `hook.namespace`, so it is pruned with the app;
  the AppProject restricts only cluster-scoped kinds (ArgoCDDeploy
  `chart/templates/appproject.yaml:33`). Not in argocd-hooks: that namespace holds the hook's
  run and credentials (D33).
- The template's header comment says why the object exists, citing P1's decision — argo-cd
  decisions.md **D67**.
- **Published per the Charts README** (§ Publishing a version): a new version, its tarball
  packaged into the committed `dist/`; `tests/publish.sh` stays green. The consumer gate
  (`tests/render-consumer.sh`) asserts the ConfigMap is in the render, is not a hook, and
  carries the revision the render was given. Nothing is pushed here: P4 publishes.

### P4 — FieldnotesDeploy pins the new library version, once charts.home serves it

Target: github:pvginkel/FieldnotesDeploy

FieldnotesDeploy is not one of this environment's checkouts; the driver clones it (or adopts the
clean clone already there) at `/work/scratch/FieldnotesDeploy` for this slice alone.

The phase opens by publishing: it pushes Charts' `main` — P3's reviewed, merged commit — and
waits until `https://charts.home/index.yaml` lists the new version. That push runs `IaC/Charts`,
which builds the charts-home image, commits its build pin into ChartsDeploy, and Argo syncs
charts-prd (Charts README § How a publish reaches charts.home). No app changes yet: no consumer
pins the new version.

Then FieldnotesDeploy's library version moves to the new one wherever the repo states it — its
homelab-shared pin (`chart/Chart.yaml:8`, `"0.3.1"` today) and its re-resolved `chart/Chart.lock`;
no test of its own pins the version — and nothing else changes. The gate (`kc project test`,
whose first step `chart-deps` resolves the lock against charts.home) is green, and its prd render
carries the ConfigMap with the revision the gate passes. Nothing is pushed: this commit is the
first push of the test phase's live proof.

### P5 — Every other deploy repo pins the new library version, ready to push in batches

Target: root

Ruling D2. Every deploy repo whose chart pins homelab-shared, FieldnotesDeploy aside (P4), gets
the same bump — its library version wherever the repo states it, and nothing else (ruling r1 F1):
the `chart/Chart.yaml` pin, its re-resolved `Chart.lock`, and any test of the repo's own that pins
the version. The one known is KubeCoderDeploy's `tests/render-chart.py` `LIBRARY` (`:26`), which
`check_library` (`:209-213`) holds `chart/Chart.yaml`'s dependency list equal to. The set comes
from the registry (ArgoCDDeploy `releases/values.yaml`, one `repo` per app); every consumer read
at planning pins `0.3.1` (Grounding). ArgoCDDeploy pins nothing and is not bumped.

- **Where the edits land.** Each repo's clone under `/work/scratch/<Repo>` (cloned there when
  absent), on `main`, brought to origin's head first; one commit, its only one ahead of origin.
  Nothing is pushed: the test phase pushes after P4's live proof (Ordering constraints).
- **ChartsDeploy and RegistryDeploy** take homelab-shared from charts.home like every other
  deploy repo — no deploy repo commits the library tarball (AnsibleSpecs `argo-cd/design.md:140`)
  — so theirs is the same bump. At planning their clones each carry an unpushed commit of slice
  039's (ChartsDeploy `69ecb9f`, RegistryDeploy `e53c36b`); it is on origin before the run starts
  (close-out action), which keeps the bump each clone's only commit ahead.
- **KubeCoderDeploy** takes its commit on `main` as well: kubecoder-dev syncs from it, and
  kubecoder-prd tracks the `prd` branch (`releases/values.yaml:172-174`, D34), which only the
  operator's KubeCoder/Promote-PRD moves.
- **Each bumped repo's own gate runs at its bump commit.** Its `kc project test`, where the repo
  has one, is run in this phase (KubeCoderDeploy's, like FieldnotesDeploy's, opens with
  `chart-deps`, which resolves against charts.home); a repo without one is proven by resolving
  its dependencies against charts.home and rendering. Either way the bumped render carries the
  ConfigMap. The bump turns no gate red: a red it causes because the repo states the version in
  another place makes that place part of the bump; a red it causes for any other reason is
  outside a library-version bump and is raised, not worked around. A red the parent commit
  already shows is not the bump's: it is recorded as such, with the parent's result, and goes in
  the close-out report; the repo is pushed like the rest, since the bump changes nothing that red
  rests on.
- **The at-risk list (ruling D2).** For every app-stage the bumps reach: did its deploy repo's
  `terraform/` or `config/*/*.tfvars` change between the revision of its last sync operation
  (its Application's status, read-only from prd; a multi-source app's deploy-repo revision is
  one of several) and the bump's parent? Every app that did is named in the done-record with the
  commits its bump push will apply.
- **A ledger in the slice folder** lists every bumped repo — repo, clone path, branch, commit,
  its gate's result, and its at-risk finding. It is the test phase's push list, and the review
  reads the commits through it: this phase leaves no commit on the Ansible branch.

## Not in scope

- Moving the Terraform hook out of the per-repo pin (registry-owned hook, a floating library
  range, or moving the hook image tag to a registry parameter) — parked as ANS-199.
- The app-facing homelab-shared helpers (Ceph PV/PVC, node affinity, ExternalSecrets) — unchanged.
- ArgoCDDeploy has no Terraform and gets no bump.
- Promoting KubeCoderDeploy's `prd` branch: kubecoder-prd takes the bump at the operator's next
  KubeCoder/Promote-PRD.
