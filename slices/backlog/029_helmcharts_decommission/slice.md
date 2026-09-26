---
issue: ANS-119
---

# 029 — HelmCharts decommission: D61 cleanup, tool homes, registry move, docs

**Improvement.** Everything ANS-109 lists before HelmCharts' Jenkins jobs are deleted and the
GitHub repo is archived. The two steps only the operator can take are carded separately (ANS-121,
ANS-122). A home for `recommend-resources` (ANS-115) is added.

## What is being requested and why

All apps have been on Argo CD since the bulk migration of 2026-09-24 (ANS-103, the run record). ANS-109
gives the order: "The first four items clear the way for deleting the jobs; the registry move clears
the way for the archive." It cites argo-cd D43, D44, D60, D61 and O2.

The decision-record check at triage found no contradiction for the registry move. ANS-109 says it
"revisits D21/D22", but D20 calls the registry "a migration mechanism, not the target state", and
D43 names D21 and the registry as revisited at the endgame.

Two facts from triage research (2026-09-24) bear on the order. First, D61 keeps `configs/dev/<app>`
in HelmCharts, and the dev cluster's electronics-inventory release still reads its values from
there (ANS-73's research). Second, the only `configs/prd` entries not on Argo CD are D60's parked
apps (design-assistant ×4 stages, open-webui, shell), which are `disabled: true` (ANS-106's research).

**Timing:** the D61 cleanup is "due from 2026-09-25 19:45Z" (ANS-109). The operator ruled that it
belongs to this slice, not to ANS-103.

**Waiting on this slice:** ANS-121 (delete the `IaC/HelmCharts` and `AaC/HelmCharts` jobs) and
ANS-122 (archive the repo), both Operator Actions.

Subsumes ANS-109 (items a, b, c, d, f, g; e and h became ANS-121 and ANS-122) and ANS-115. The
triage record is AnsibleSpecs `handovers/triage_2026-09-24.md` and `…_raw.md` at `1b6cd36`;
everything below is quoted from them.

## Done outside the slice (2026-09-26)

The operator asked for what is quick to be actioned directly, and the rest planned here.

- **Requirement 1, the D61 cleanup,** is done except `terraform-modules/namespace` (D44). That
  module is still used by the `configs/dev` tree, which D61 keeps, so D44 needs a ruling first.
  Done: HelmCharts `eeceac0`, `6e8a054` and `91ce931`, the prd Helm release Secrets, DockerImages
  `6041476` (no `helmDeploy()`). storage's `_shared/` went with the retirement of
  `test_s3_storage_backup_grant.py`'s reader test. The record is in ANS-103.
- **Requirement 2, version-poller,** is done. The island is gone from the code (DockerImages
  `cbf7771`, running as `:2553`), and VersionPollerDeploy `9846433` drops the config block,
  `GIT_TOKEN` and the cluster-wide Secret-reading ClusterRole. OpenBao
  `eso/prd/version-poller/prd/git` is now unread.
- **Requirement 4, `collect-versions`,** is deleted (HelmCharts `91ce931`).
- **Requirement 3, the `helm-charts` producer, is not a config edit.** Its dataset is now 40
  product-catalog elements (38 `systemSoftware` entries such as `ss:jenkins`, `ss:keycloak`,
  `ss:nginx` and `ss:postgresql`, plus `svc:cluster-ceph-cephfs`/`-rbd`). About 30 deploy-repo
  producers target them through 91 Specialization/Realization relations, and no other producer
  publishes them. Each needs a new owner first: 31 have exactly one consumer, 6 are shared
  (nginx, samba, csi-sidecars, ceph-csi, code-server, gitblit, keycloak), and 3 are unreferenced
  (opensearch, phpmyadmin, rabbitmq). `views/infrastructure.yaml`'s `excludeProducers` names
  the producer and fails validation once it is gone. Until this is done, `AaC/HelmCharts` must
  keep running. `IaC/HelmCharts` has no caller left.


1. **[Improvement — ANS-109a] Decommission HelmCharts: the D61 cleanup**
   "D61 cleanup (ANS-103, due from 2026-09-25 19:45Z): the migrated apps' HelmCharts content, their Helm release Secrets, DockerImages' `cicd.helmDeploy()` stage and HelmCharts' `gitToken` injection. With it goes `terraform-modules/namespace` (D44)."
   Operator: "No. ANS-103 is just to track the migration. It's an Operator Actions card. It doesn't go into a slice. This card does."

2. **[Improvement — ANS-109b] Decommission HelmCharts: drop the version-poller's helm_charts block**
   "version-poller: drop the `helm_charts` block from VersionPollerDeploy's `chart/files/config.yaml`. It runs HelmCharts' `tools/collect-version-dependencies.py` and triggers `IaC/HelmCharts`."

3. **[Improvement — ANS-109c] Decommission HelmCharts: retire the helm-charts architecture producer**
   "Retire the `helm-charts` producer from Architecture's `pipeline-producers.yaml`; it still publishes 40 elements."

4. **[Decision — ANS-109d] Decommission HelmCharts: O2 — homes for recommend-resources and collect-versions, or drop them**
   "O2: `recommend-resources` and `collect-versions` get homes that enumerate the deploy repos, or are dropped."
   Operator ruling: "Delete collect-versions." `recommend-resources` is requirement 5.

5. **[Feature — ANS-115] Figure out how to run recommend-resources**
   "We need to figure out how to run recommend resources. I'm guessing the answer will be to just clone all deploy repos and do this using a script. I'm also guessing that we don't yet have a home for this tool."

6. **[Improvement — ANS-109f] Decommission HelmCharts: move the Argo CD registry out of HelmCharts**
   "Move the Argo CD registry out of HelmCharts (a slice; revisits D21/D22). Repoint ArgoCDDeploy's `releases.registry.repoURL` without recreating the 50 Applications, and move the registry's key validation, its tests, and `argo_migrate.py`'s register, flip and autosync steps."

7. **[Nit pick — ANS-109g] Decommission HelmCharts: docs that still describe HelmCharts as the deploy path**
   "Docs that still describe HelmCharts as the deploy path: Ansible's CLAUDE.md, `docs/live-infra-access.md` and about a dozen runbooks."
   Added at triage (the session's wording, from closing ANS-81): the argocd runbook's "What a cutover does not change" points at the stuck-field working copy in AnsibleSpecs `handovers/argo-adoption-blind-spot/`, a pointer the docs pass should settle.

## Triage record

Each item's block from the triage status document (`handovers/triage_2026-09-24.md`), verbatim minus
its card text: the ask, the category and its quote, questions, research verdicts (read-only
sub-agents, 2026-09-24; also posted on the cards as "Triage research" comments), the operator's
rulings (`Ruling:`, `Ruling 2:`) and the triage session's replies (`Reply:`).

### ANS-109a — Decommission HelmCharts: the D61 cleanup

- Source: ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived (checklist item 1)
- Ask: "D61 cleanup (ANS-103, due from 2026-09-25 19:45Z): the migrated apps' HelmCharts content, their Helm release Secrets, DockerImages' `cicd.helmDeploy()` stage and HelmCharts' `gitToken` injection. With it goes `terraform-modules/namespace` (D44)."
- Question: ANS-103, the bulk migration's run record (an Operator Action, Accepted), already carries this cleanup. Strike it here as covered there?
- Category: Improvement — "The first four items clear the way for deleting the jobs"
- Ruling: No. ANS-103 is just to track the migration. It's an Operator Actions card. It doesn't go into a slice. This card does.
- Reply: recorded. It goes into the decommission slice, and ANS-103 stays the migration record.

### ANS-109b — Decommission HelmCharts: drop the version-poller's helm_charts block

- Source: ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived (checklist item 2)
- Ask: "version-poller: drop the `helm_charts` block from VersionPollerDeploy's `chart/files/config.yaml`. It runs HelmCharts' `tools/collect-version-dependencies.py` and triggers `IaC/HelmCharts`."
- Category: Improvement — "It runs HelmCharts' `tools/collect-version-dependencies.py` and triggers `IaC/HelmCharts`."
- Ruling: Agree

### ANS-109c — Decommission HelmCharts: retire the helm-charts architecture producer

- Source: ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived (checklist item 3)
- Ask: "Retire the `helm-charts` producer from Architecture's `pipeline-producers.yaml`; it still publishes 40 elements."
- Category: Improvement — "it still publishes 40 elements"
- Ruling: Agree

### ANS-109d — Decommission HelmCharts: O2 — homes for recommend-resources and collect-versions, or drop them

- Source: ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived (checklist item 4)
- Ask: "O2: `recommend-resources` and `collect-versions` get homes that enumerate the deploy repos, or are dropped."
- Question: new homes or drop, for each of `recommend-resources` and `collect-versions`? ANS-115, filed today, reads as "keep" for `recommend-resources`, so the open half is `collect-versions`.
- Category: Decision — "get homes that enumerate the deploy repos, or are dropped"
- Ruling: Delete collect-versions.
- Reply: recorded: `collect-versions` is deleted; `recommend-resources` gets a home through ANS-115.

### ANS-115 — Figure out how to run recommend-resources

- Source: ANS-115 — Figure out how to run recommend resources
- Ask: "We need to figure out how to run recommend resources. I'm guessing the answer will be to just clone all deploy repos and do this using a script. I'm also guessing that we don't yet have a home for this tool."
- Category: Feature — "I'm also guessing that we don't yet have a home for this tool."
- Note: this is the `recommend-resources` half of ANS-109d (O2: homes that enumerate the deploy repos, or drop). It reads as a "keep" for that tool; ANS-109d's question narrows to `collect-versions`.
- Ruling: Agree

### ANS-109f — Decommission HelmCharts: move the Argo CD registry out of HelmCharts

- Source: ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived (checklist item 6)
- Ask: "Move the Argo CD registry out of HelmCharts (a slice; revisits D21/D22). Repoint ArgoCDDeploy's `releases.registry.repoURL` without recreating the 50 Applications, and move the registry's key validation, its tests, and `argo_migrate.py`'s register, flip and autosync steps."
- Category: Improvement — "the registry move clears the way for the archive"
- Ruling: Agree

### ANS-109g — Decommission HelmCharts: docs that still describe HelmCharts as the deploy path

- Source: ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived (checklist item 7)
- Ask: "Docs that still describe HelmCharts as the deploy path: Ansible's CLAUDE.md, `docs/live-infra-access.md` and about a dozen runbooks."
- Category: Nit pick, user-visible (runbooks and CLAUDE.md the operator and sessions follow) — "Docs that still describe HelmCharts as the deploy path"
- Ruling: Agree

## Source material

Each card whole and verbatim from the triage dump (`handovers/triage_2026-09-24_raw.md`, fetched
2026-09-24), headings demoted. A card's diagnosis, cause or line reference is the card's claim, not
verified at triage.

### ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived

- Reporter: jeeves
- Created: 2026-09-24
- Updated: 2026-09-24
- State: New · Type: Task · Tags: Architecture
- Parent: EPIC-2 [In Progress] ArgoCD
- Relates: ANS-103

##### Description

What is left before HelmCharts' Jenkins jobs are deleted and the GitHub repo is archived (argo-cd D43, D44, D60, D61, O2). The first four items clear the way for deleting the jobs; the registry move clears the way for the archive.

* [ ] D61 cleanup (ANS-103, due from 2026-09-25 19:45Z): the migrated apps' HelmCharts content, their Helm release Secrets, DockerImages' `cicd.helmDeploy()` stage and HelmCharts' `gitToken` injection. With it goes `terraform-modules/namespace` (D44).
* [ ] version-poller: drop the `helm_charts` block from VersionPollerDeploy's `chart/files/config.yaml`. It runs HelmCharts' `tools/collect-version-dependencies.py` and triggers `IaC/HelmCharts`.
* [ ] Retire the `helm-charts` producer from Architecture's `pipeline-producers.yaml`; it still publishes 40 elements.
* [ ] O2: `recommend-resources` and `collect-versions` get homes that enumerate the deploy repos, or are dropped.
* [ ] Operator: delete the `IaC/HelmCharts` and `AaC/HelmCharts` jobs.
* [ ] Move the Argo CD registry out of HelmCharts (a slice; revisits D21/D22). Repoint ArgoCDDeploy's `releases.registry.repoURL` without recreating the 50 Applications, and move the registry's key validation, its tests, and `argo_migrate.py`'s register, flip and autosync steps.
* [ ] Docs that still describe HelmCharts as the deploy path: Ansible's CLAUDE.md, `docs/live-infra-access.md` and about a dozen runbooks.
* [ ] Operator: archive the GitHub repo.

##### Comments

None.

### ANS-115 — Figure out how to run recommend resources

- Reporter: pvginkel
- Created: 2026-09-24
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none

##### Description

We need to figure out how to run recommend resources. I'm guessing the answer will be to just clone all deploy repos and do this using a script. I'm also guessing that we don't yet have a home for this tool.

##### Comments

None.
