---
issue: ANS-189
---

# 038 — Argo CD: the render gate and Terraform-only pushes

Two Argo CD defects, as the cards give them: ArgoCDDeploy's render gate stays green when
`policy.csv` widens `role:readonly` itself, so a later edit could give every prd environment's Argo
CD token write rights silently (ANS-178); and a FieldnotesDeploy push touching only `terraform/`
never triggers an Argo CD sync, so its PreSync-hook Terraform apply never runs (ANS-179).

Source: triage 2026-10-02 of the ANS intake queue. Cards: ANS-178, ANS-179. The phase count
triage guessed (~4) is a guess from the cards alone.

## Requirements

1. **ANS-178 — the render gate refuses a widened `role:readonly`.** The card: "tests/render-chart.py
   check_readonly_account (:1229-1255) checks only the policy lines whose subject is `kubecoder`
   and `policy.default`. [...] A line that widens the role the account is bound to passes the
   gate. [...] Fix: check_readonly_account also refuses any policy.csv line whose subject (field 1)
   is `role:readonly`." The wrap-up (2026-09-30) widens it: "policy_lines reads only the
   `policy.csv` key, while Argo CD also loads every `policy.*.csv` key of argocd-rbac-cm into the
   same policy [...] What a fix takes: in that one function, read the lines of policy.csv and of
   every policy.*.csv key, refuse any line whose subject is role:readonly, and hold the
   kubecoder-subject check to all of them; witnessed by the entry's two lines, and an overlay key,
   turning a scratch render red."
2. **ANS-179 — a Terraform-only FieldnotesDeploy push reaches `terraform apply`.** The card's
   title: "FieldnotesDeploy: a push touching only terraform/ never triggers an Argo CD sync, so its
   PreSync-hook Terraform apply never runs". The card: "it will recur for any future
   FieldnotesDeploy push that changes only terraform/ or only tfvars, with no accompanying
   chart/values change." The fix's shape is open — see the rulings.

## Operator rulings and Q&A

- **ANS-178's route.** Triage first proposed it as Solution Known; the operator's Q1 ruling
  ("Please separate out cards that are good candidates for a manual sweep. ANS-187 is an obvious
  one. Hand this to me and recut your slices.") sent it back to a slice — triage's reason, its
  own: it is gate code that needs a scratch-render proof, not a manual edit.
- **ANS-179's fix shape is not ruled.** The nightly card pass (2026-10-02) asked the operator to
  pick between "(a) a hash of terraform/ written into config/*/values.yaml by whoever edits
  terraform/, local to FieldnotesDeploy (it adds a manual step, perhaps checked by a gate); (b) a
  change to the shared tf-presync-hook pattern in the homelab-shared library chart, which reaches
  every app that includes it, ModelsDeploy among them; or (c) something else you have in mind?"
  Triage left that choice to planning, with no answer from the operator. The card still carries
  the `Requires Operator` tag from that pass.
- **Standing-decision check (triage, 2026-10-02):** option (a) may brush argo-cd D12 —
  "`config/{stage}/{values.yaml,*.tfvars}` holds only what genuinely differs per stage." — since a
  hash of `terraform/` is the same for every stage; the checker called it weak (D47 already puts
  per-stage image tags in the same files). Options (b) and (c) collide with nothing. ANS-178:
  no collision.

## Source material

The cards as read at triage on 2026-10-02, verbatim (headings demoted one level). A card's
diagnosis, cause or line reference is the card's claim, not verified at triage.

### ANS-178 — ArgoCDDeploy render gate: check_readonly_account stays green when policy.csv widens role:readonly itself

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Updated: 2026-10-01
- Links: Relates: KC-114

#### Description

tests/render-chart.py check_readonly_account (:1229-1255) checks only the policy lines whose subject is `kubecoder` and `policy.default`. Its docstring says 'a token that can only read'. A line that widens the role the account is bound to passes the gate. Witnessed on a scratch copy, each line on top of the committed binding: `p, role:readonly, applications, sync, */*, allow` → ok; `g, role:readonly, role:admin` → ok. Either line gives the token in every prd environment write rights on Argo CD. V05's live can-i check catches this once, at this slice's live proof, and not after. Fix: check_readonly_account also refuses any policy.csv line whose subject (field 1) is `role:readonly`.

**Consequence:** A later policy.csv edit that widens role:readonly silently gives every prd environment's Argo CD token write rights, and the ArgoCDDeploy gate stays green.

### Wrap-up, 2026-09-30

The gap is wider than the entry says: policy_lines reads only the `policy.csv` key, while Argo CD also loads every `policy.*.csv` key of argocd-rbac-cm into the same policy (argo-cd util/rbac/rbac.go PolicyCSV, :526-544), so a line in e.g. `policy.overlay.csv` that binds `kubecoder` to role:admin passes as well. What a fix takes: in that one function, read the lines of policy.csv and of every policy.*.csv key, refuse any line whose subject is role:readonly, and hold the kubecoder-subject check to all of them; witnessed by the entry's two lines, and an overlay key, turning a scratch render red.

From KubeCoder slice 239's close-out report (T1): KubeCoderSpecs `slices/completed/239_argocd_read_visibility/close-out.md`.

#### Comments

none

### ANS-179 — FieldnotesDeploy: a push touching only terraform/ never triggers an Argo CD sync, so its PreSync-hook Terraform apply never runs

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-10-02
- Links: Relates: FN-24

#### Description

From the close-out report of FieldnotesApp slice 002 (entry B4), filed in ANS on the operator's ruling. Report: `FieldnotesAppSpecs/slices/completed/002_store_availability/close-out.md`.

Terraform is applied only by the fieldnotes-prd Application's PreSync hook Job, which runs as part of a Sync operation. Argo CD's automated-sync policy (prune: true, selfHeal: false) triggers a new Sync operation only when comparing the live cluster state to the Helm-rendered manifests at the target revision shows a difference. Hook resources (PreSync/PostSync Jobs) are not part of that diff, and terraform/*.tf files are not referenced by any chart template, so a push whose only change is under terraform/ renders byte-identical manifests to the previous commit. Argo CD's webhook-triggered refresh correctly picks up the new revision, finds zero resource differences, marks the Application Synced at the new commit, and skips auto-sync entirely -- the PreSync hook (and therefore `terraform apply`) never runs for that push.

Reproduced live in this test phase: FieldnotesDeploy commit c592e49 (P4, removing `module "data"` to destroy the old fieldnotes-prd-data RBD volume per ruling D2) was pushed to origin/main once its preconditions held (fieldnotes-prd-data-pvc gone, the PV reading Available). The Application's `status.sync.revision` advanced to c592e49 and read "Synced", but `status.history`'s last entry stayed at the prior image-pin commit (ee49522) with no new operation, and the argocd-prd-application-controller-0 logs show, immediately after a full refresh against c592e49: "Skipping auto-sync: application status is Synced". `fieldnotes-prd-data-pv` is still present (5Gi, Available) after the push -- the destroy did not happen.

This is not specific to P4's own edit: it will recur for any future FieldnotesDeploy push that changes only terraform/ or only tfvars, with no accompanying chart/values change. The already-committed change is not lost -- it will apply on the next push that does produce a real resource diff (which also re-runs the PreSync hook), or if the operator triggers a manual Argo CD sync of fieldnotes-prd. The right fix likely needs to force a detectable diff on a real (non-hook) resource whenever terraform/ changes (e.g. a content-hash annotation on a chart-tracked resource), and may touch the shared tf-presync-hook pattern (sourced from a separate ArgoCDTools/HelmCharts pattern, not checked out in this environment) rather than being purely local to FieldnotesDeploy's own chart.

**Consequence:** The old fieldnotes-prd-data RBD volume (5Gi) stays provisioned and un-destroyed in prd until the operator manually syncs the fieldnotes-prd Argo CD Application, or an unrelated FieldnotesDeploy push happens to also change a chart-tracked resource; ruling D2 is not yet realized in the running system even though the Terraform source already states it

**Triage:** defect · shows on an ordinary condition · breaks a flow · silent · fix needs design · in FieldnotesDeploy

### What the wrap-up found (2026-09-30)

How it is reached, in the deployed shape. Any FieldnotesDeploy push whose diff lies only under terraform/ or in a config/*/terraform.tfvars. Argo CD auto-syncs fieldnotes-prd (automated, prune: true, selfHeal: false) from chart/ with config/prd/values.yaml. Terraform runs only inside the homelab-shared 0.3.1 library's PreSync hook Job (chart/templates/tf-presync-hook.yaml → _tf-presync-hook.tpl). The only place the synced SHA appears is that Job's args (hook.revision = $ARGOCD_APP_REVISION), and hooks are left out of Argo CD's diff. So such a push renders the same live objects: the Application reads Synced at the new revision, auto-sync is skipped, no hook runs and no apply happens, and nothing says so.

What the lasting fix takes. A Terraform-only commit has to become visible to Argo CD's diff, and there are several ways, each with consequences. The chart cannot hash terraform/: Helm's .Files reads only inside chart/. A non-hook object carrying hook.revision would make every commit a diff, so every push would sync and run an apply. A hash written into the values by whoever edits terraform/ is a manual step. Changing the shared tf-presync-hook pattern reaches every app that includes it (ModelsDeploy has Terraform too). Or the pushes could be changed. Each adds behaviour, may reach beyond FieldnotesDeploy into the homelab-shared library chart, and can only be proven by a deploy.

### Checked at close-out (2026-10-01)

The 002 instance has cleared itself. The next FieldnotesDeploy push, dce2688 (an image pin, synced 2026-09-30 21:25Z), produced a real diff, ran the hook and applied c592e49's destroy. fieldnotes-prd-data-pv no longer exists in prd. The defect itself still holds.

#### Comments

##### Comment 1/1 · 7-5367 · jeeves · 2026-10-02 01:01Z

Card pass 2026-10-02: needs your input — the fix is a design choice among the wrap-up's options, and they differ in reach. Which one should the pass build: (a) a hash of terraform/ written into config/*/values.yaml by whoever edits terraform/, local to FieldnotesDeploy (it adds a manual step, perhaps checked by a gate); (b) a change to the shared tf-presync-hook pattern in the homelab-shared library chart, which reaches every app that includes it, ModelsDeploy among them; or (c) something else you have in mind? Answer in a comment and remove the tag; the next pass continues from your answer.
