---
issue: ANS-118
---

# 028 — Argo CD and service residuals: standing sync alert, argocd login, PreSync init, promote re-run, gitblit index

**Minor.** Five residual defects: four on the Argo CD platform (ArgoCDDeploy, ArgoCDTools'
PreSync hook, KubeCoderDeploy's promotion job) and one on gitblit's search index. Each card states
its own consequence; none is an outage.

## What is being requested and why

These are loose ends from the Argo CD adoption (slices 009–012, the Phase A.5 drill) and one
operational incident (gitblit's index frozen from 2026-09-07 to 2026-09-23). They share a slice
because each is small and none has a neighbour elsewhere. ANS-105 is the loose fit: it is about
gitblit, not Argo CD.

ANS-26 changed shape at triage. Its HelmCharts half is gone (all apps are on Argo CD), and what
remains is the same exposure on the Argo side: the PreSync hook runs `terraform init` from a fresh
clone on every sync. The operator agreed to retarget it (the rulings below). The operator's
2026-09-15 ruling on that card still stands: "I don't want persistence on srviac."

ANS-47 leaves a decision open: an `endsAt` far ahead, or a Prometheus rule over
`argocd_app_info`. The operator left it to the planner.

Subsumes ANS-47, ANS-46, ANS-26, ANS-96 and ANS-105. The triage record is AnsibleSpecs
`handovers/triage_2026-09-24.md` and `…_raw.md` at `1b6cd36`; everything below is
quoted from them.

## Requirements

1. **[Minor — ANS-47] Argo CD sync-failed alert expires after 5 minutes while the app stays failed**
   "D7's notification is therefore a 5-minute event, not a standing alert. `on-health-degraded` has the same shape. … Decide, then apply in ArgoCDDeploy."
   Operator on the option: "Leave to the planner."

2. **[Minor — ANS-46] Login through https://argocd/ does not work**
   "Login through https://argocd/ does not work … `Invalid redirect URL: the protocol and host (including port) must match and the path must be within allowed URLs if provided`"

3. **[Minor — ANS-26] Deploys fail on transient terraform provider checksum fetches**
   "HelmCharts deploys fail on transient terraform provider checksum fetches … Transient, but it takes a whole deploy down. … Same exposure on the Argo CD side: ArgoCDTools' PreSync hook (presync/terraform.py) inits from a fresh clone with no lock file and unpinned providers, and KubeCoderDeploy has the same gitignored-lock, unpinned-provider pattern."
   Retargeted at triage to the Argo side: the PreSync hook's `terraform init`, and the deploy repos' unpinned providers with no committed lock. Operator: "Agree."

4. **[Minor — ANS-96] KubeCoderDeploy Jenkinsfile.promote: a failed release-tag push cannot be finished by a re-run**
   "If 'Recording the release' fails after 'Advancing prd' succeeded (Jenkinsfile.promote:115, then 128-129), the re-run refuses at :72-74 with 'prd is already at <sha>: nothing to promote'."

5. **[Minor — ANS-105] gitblit: prune stale branch entries from gb_lucene.conf so indexing doesn't stall**
   "HelmCharts' gitblit index was frozen from 2026-09-07 to 2026-09-23. … Fix: extend the `clean-lucene-locks` init container (git-sync chart, gitblit deployment) to drop `[aliases]`/`[branches]` entries in each `lucene/*/gb_lucene.conf` whose branch is not in that repo's `gitblit.indexBranch`."

## Triage record

Each item's block from the triage status document (`handovers/triage_2026-09-24.md`), verbatim minus
its card text: the ask, the category and its quote, questions, research verdicts (read-only
sub-agents, 2026-09-24; also posted on the cards as "Triage research" comments), the operator's
rulings (`Ruling:`, `Ruling 2:`) and the triage session's replies (`Reply:`).

### ANS-47 — Argo CD sync-failed alert expires after 5 minutes while the app stays failed

- Source: ANS-47 — Argo CD sync-failed alert expires after 5 minutes while the app stays failed
- Ask: "D7's notification is therefore a 5-minute event, not a standing alert. `on-health-degraded` has the same shape. … Decide, then apply in ArgoCDDeploy."
- Question: the card asks you to decide: set `endsAt` far ahead in the template, or add a Prometheus rule over `argocd_app_info` and keep the notification as the event? Answer now or leave it to the planner.
- Category: Minor — "D7's notification is therefore a 5-minute event, not a standing alert."
- Ruling: Leave to the planner.

### ANS-46 — Login through https://argocd/ does not work

- Source: ANS-46 — Login through https://argocd/ does not work
- Ask: "Login through https://argocd/ does not work … `Invalid redirect URL: the protocol and host (including port) must match and the path must be within allowed URLs if provided`"
- Category: Minor — "Login works when logging in through [https://argocd.home](…)"
- Ruling: Agree

### ANS-26 — Deploys fail on transient terraform provider checksum fetches

- Source: ANS-26 — HelmCharts deploys fail on transient terraform provider checksum fetches
- Ask: "HelmCharts deploys fail on transient terraform provider checksum fetches … Transient, but it takes a whole deploy down. … Same exposure on the Argo CD side: ArgoCDTools' PreSync hook (presync/terraform.py) inits from a fresh clone with no lock file and unpinned providers, and KubeCoderDeploy has the same gitignored-lock, unpinned-provider pattern."
- Question: HelmCharts no longer deploys the migrated apps, since the bulk migration put all 50 on Argo. Does the card now carry only its Argo half (the PreSync hook's `terraform init`, and the deploy repos' unpinned providers with no committed lock), or does it close with HelmCharts?
- Category: Minor — "Transient, but it takes a whole deploy down."
- Ruling: Please advise.
- Reply: advice: keep it, retargeted to the Argo side. HelmCharts no longer deploys the migrated apps, but every Argo sync runs the PreSync hook's `terraform init` from a fresh clone, which is the same exposure. The card's own measurement says only the init retry would have saved 5751/5752; locks or a warm cache is the planner's call. Your 09-15 ruling against persistence on srviac rides along.
- Ruling 2: Agree. (operator, in chat)

### ANS-96 — KubeCoderDeploy Jenkinsfile.promote: a failed release-tag push cannot be finished by a re-run

- Source: ANS-96 — KubeCoderDeploy Jenkinsfile.promote: a promotion whose release-<m> push fails after prd moved cannot be finished by a re-run
- Ask: "If 'Recording the release' fails after 'Advancing prd' succeeded (Jenkinsfile.promote:115, then 128-129), the re-run refuses at :72-74 with 'prd is already at <sha>: nothing to promote'."
- Category: Minor — "After a failed tag push, the operator gets a red build and a refusal on re-run, and the release has no D48 record unless the tag is written by hand."
- Ruling: Agree

### ANS-105 — gitblit: prune stale branch entries from gb_lucene.conf so indexing doesn't stall

- Source: ANS-105 — gitblit init container: prune stale branch entries from gb_lucene.conf so indexing doesn't silently stall
- Ask: "HelmCharts' gitblit index was frozen from 2026-09-07 to 2026-09-23. … Fix: extend the `clean-lucene-locks` init container (git-sync chart, gitblit deployment) to drop `[aliases]`/`[branches]` entries in each `lucene/*/gb_lucene.conf` whose branch is not in that repo's `gitblit.indexBranch`."
- Category: Minor — "HelmCharts' gitblit index was frozen from 2026-09-07 to 2026-09-23."
- Ruling: Agree

## Source material

Each card whole and verbatim from the triage dump (`handovers/triage_2026-09-24_raw.md`, fetched
2026-09-24), headings demoted. A card's diagnosis, cause or line reference is the card's claim, not
verified at triage.

### ANS-47 — Argo CD sync-failed alert expires after 5 minutes while the app stays failed

- Reporter: jeeves
- Created: 2026-09-13
- Updated: 2026-09-13
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-980

##### Description

Seen in the Phase A.5 drill (Triage #849), 2026-09-13. `on-sync-failed` fires once per condition: the notifications controller sends to Alertmanager at the failure and logs "already sent" every minute after. The `app-sync-failed` template (ArgoCDDeploy `config/prd/values.yaml`) sets no `endsAt`, so Alertmanager applies its resolve timeout: `ArgoCDSyncFailed` for proofdeploy-prd started 14:18:35Z and ended 14:23:35Z with the app still Failed. D7's notification is therefore a 5-minute event, not a standing alert. `on-health-degraded` has the same shape.

Options: set `endsAt` far ahead in the template (then a re-fire depends on the trigger's oncePer), or a Prometheus rule over Argo's `argocd_app_info` sync/health metrics for the standing state and keep the notification as the event. Decide, then apply in ArgoCDDeploy.

##### Comments

None.

### ANS-46 — Login through https://argocd/ does not work

- Reporter: pvginkel
- Created: 2026-09-13
- Updated: 2026-09-13
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-977

##### Description

Return URL:

[https://argocd/auth/login?return_url=https%3A%2F%2Fargocd%2F](https://argocd/auth/login?return_url=https%3A%2F%2Fargocd%2F "‌")

Message:

> `Invalid redirect URL: the protocol and host (including port) must match and the path must be within allowed URLs if provided`

Return URL in Keycloak:

[https://argocd.home/*](https://argocd.home/* "‌")

[https://argocd/*](https://argocd/* "‌")

Login works when logging in through [https://argocd.home](https://argocd.home "‌").

The error is a plain text result. My guess is it’s an ArgoCD error (page).

##### Comments

None.

### ANS-26 — HelmCharts deploys fail on transient terraform provider checksum fetches

- Reporter: jeeves
- Created: 2026-08-13
- Updated: 2026-09-15
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-567

##### Description

Jenkins IaC/HelmCharts 5752 failed in "Deploying prometheus@prd": terraform init could not install cyrilgdn/postgresql v1.27.0 — "failed to retrieve authentication checksums" fetching SHA256SUMS. 5751 failed the same way on keycloak; 5753 passed on retry. Transient, but it takes a whole deploy down.

Why it recurs: .terraform.lock.hcl is gitignored (.gitignore:11), _providers/providers.tf pins no versions, and _init passes -upgrade (tf.py:129) — so every release and phase re-resolves and re-authenticates every provider. The iac container is `docker run --rm` with no /work mount, so nothing persists between releases.

Measured, not assumed: a plugin cache does not help — warm cache with no lock still fetches checksums. A committed lock does: zero downloads, one registry version-list call. Pinning makes -upgrade a no-op for the public providers while homelab still floats to the newest tfmirror build.

Agreed fix:
- pin kubernetes, keycloak, postgresql, random in _providers/providers.tf
- un-ignore .terraform.lock.hcl, commit per-chart locks
- retry terraform init on transient failure
- verify what a stale committed homelab entry does under -upgrade

Deferred: routing public providers through tfmirror.

https://jenkins.webathome.org/job/IaC/job/HelmCharts/5752/

##### Comments

###### jeeves — 2026-09-14 07:17Z (7-4861)

Triaged 2026-09-14: Minor — "Transient, but it takes a whole deploy down."

Operator ruling: "Agreed"

###### jeeves — 2026-09-14 07:39Z (7-4862)

Filed at triage 2026-09-14 into slice 021 — AnsibleSpecs/slices/backlog/021_build_and_deploy_pipeline_reliability/ (Kanban [021]). The card text and its ruling are quoted in slice.md.

###### jeeves — 2026-09-15 10:01Z (7-4863)

Planning slice 021, 2026-09-15: taken out of the slice and moved to the Argo CD project. Operator ruling: "I don't want persistence on srviac. Plus, HelmCharts is EOL. I'm replacing it fully with Argo CD. So any change should probably be made part of the Argo CD project. Right now I feel like taking this out of the slice, and tagging it Project-ArgoCD would be best."

Premise correction, measured 2026-09-15 (Terraform 1.16, pinned random + postgresql): a committed lock alone does not avoid the checksum download. With an empty plugin cache, init with a lock (with or without -upgrade) fetches SHA256SUMS and its .sig from GitHub exactly as without one; a warm cache without a lock also fetches; only warm cache + lock fetches nothing. Each HelmCharts release deploys in its own fresh iac container, and the deploy CLI's TF_PLUGIN_CACHE_DIR defaults to ~/.terraform.d/plugin-cache inside it, so the cache is always empty. Of the "Agreed fix" above, only the init retry would have saved 5751/5752. The earlier "zero downloads" measurement most likely ran where a cache persisted (the KubeCoder pod's iac sidecar sets TF_PLUGIN_CACHE_DIR).

Same exposure on the Argo CD side: ArgoCDTools' PreSync hook (presync/terraform.py) inits from a fresh clone with no lock file and unpinned providers, and KubeCoderDeploy has the same gitignored-lock, unpinned-provider pattern. A fix that removes the download needs a lock plus a cache that is already warm (or a mirror); a retry only absorbs it.

### ANS-96 — KubeCoderDeploy Jenkinsfile.promote: a promotion whose release-<m> push fails after prd moved cannot be finished by a re-run

- Reporter: jeeves
- Created: 2026-09-22
- Updated: 2026-09-22
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Relates: ANS-33

##### Description

If 'Recording the release' fails after 'Advancing prd' succeeded (Jenkinsfile.promote:115, then 128-129), the re-run refuses at :72-74 with 'prd is already at <sha>: nothing to promote'. D48's annotated tag for that promotion is then never written by the job. Every other partial failure converges on a re-run. Possible remedies: the P3 runbook names the manual recovery (git tag -a release-<m> on the promoted sha, then push), or the job treats 'prd already at sha' with no release tag on the sha as 'record only'.

doc-writer, doc phase, 2026-09-22 — The runbook half is closed in the doc phase (Ansible 68dc5de): P2's recovery command writes the job's whole message. The job itself is unchanged, so a re-run still refuses.

**Consequence:** After a failed tag push, the operator gets a red build and a refusal on re-run, and the release has no D48 record unless the tag is written by hand.

Provenance: read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1

Report: AnsibleSpecs slices/completed/012_kubecoder_argo_cutover/close-out.md (S6)

##### Comments

None.

### ANS-105 — gitblit init container: prune stale branch entries from gb_lucene.conf so indexing doesn't silently stall

- Reporter: jeeves
- Created: 2026-09-23
- Updated: 2026-09-23
- State: New · Type: Task · Tags: none

##### Description

HelmCharts' gitblit index was frozen from 2026-09-07 to 2026-09-23. Rebuilt live on 09-23.

Cause: `gb_lucene.conf` still listed branches that are no longer indexed (`dhcp`, `storage`, `restructure`, …). Gitblit never removes these entries. Instead, every 2-minute cycle it opens the repo's Lucene writer to delete them. As a result, the writer opens about a minute after pod start. On CephFS, the `write.lock` mtime drifts after creation, so by the midnight git-sync every write fails with `AlreadyClosedException: Underlying file changed by an external force`. Gitblit then still advances the branch bookmark, so it never retries, and the logs of later pods look clean.

Fix: extend the `clean-lucene-locks` init container (git-sync chart, gitblit deployment) to drop `[aliases]`/`[branches]` entries in each `lucene/*/gb_lucene.conf` whose branch is not in that repo's `gitblit.indexBranch`. The busybox image has no git, so it has to parse the repo `config` directly.

This only removes one trigger. Searches also open writers early, so a log-based alert on `Exception while indexing commit` / `external force` is worth considering alongside. The existing corruption check can't see this, because the index stays structurally valid.

##### Comments

None.
