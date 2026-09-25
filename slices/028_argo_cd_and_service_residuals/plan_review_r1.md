# Slice 028 — plan review r1

Verdict: **questions**. Two findings need the operator. Two advisory notes follow. Everything else
checked holds; the checks are listed at the end.

## Operator-decidable

### Q1 — P3 and P5 add permanent tests to two deploy repos' gates. This conflicts with the operator's "deploy repos run no tests" and pre-empts slice 027's open question on the same point.

**Problem.** P3 says "Prove the rules and the routing offline, in the repo's own gate"
(plan.md:198-206). P5 says "Prove the prune offline in the repo's gate" (plan.md:256-259). V04
("PrometheusDeploy's own gate proves the rule edges offline") and V13 ("GitSyncDeploy's gate
proves the prune offline") make those in-gate proofs acceptance criteria. Neither plan.md's
rulings nor refinement.md mentions the operator's standing position on tests in deploy repos, or
slice 027.

**Evidence.**
- argo-cd `decisions.md:769-772` (D61) records the operator's 2026-09-24 ruling. The five
  prometheus alert tests were retired rather than moved to PrometheusDeploy, "since deploy repos
  run no tests and the alert timings checked other apps' CronJobs, which a copy in PrometheusDeploy
  could not follow". HelmCharts `4d02286` is the commit that retired them. P3's edge "arrives after
  the retry window and not during it" is a timing tied to another repo's value: ArgoCDDeploy's
  `applicationsets.yaml:53-57` retry policy.
- Slice 027 (backlog), R3 / ANS-74, is "promtool in the iac toolchain so alert rules are
  unit-tested", retargeted at PrometheusDeploy (027 `slice.md:37-39`). 027's refinement (a working
  draft, not yet committed) puts exactly this to the operator as D2: "Your 'deploy repos run no
  tests' and your 'Good one' on this card both stand; which one governs the Prometheus deploy repo
  is yours to say." That ruling is still pending.
- P3 also leaves open how promtool and amtool reach the gate: "The iac sidecar has neither
  `promtool` nor `amtool` today, so this phase decides how the proof runs" (plan.md:205-206).
  That is the toolchain question 027 R3 owns. The `iac` toolchain comes from the environment
  catalog (`use: iac` in `.kubecoder/config.yaml`), so no phase executor can add a tool to it
  mid-run.
- P4 in the same plan proves its change with a hand run before handover (plan.md:226-227), outside
  the gate. So the plan uses both forms of proof without saying why.

**Impact.**
- **If D61's position governs these repos:** V04 and V13 cannot be earned as written. P3 and P5
  would also commit test harnesses of a kind the operator declined the day before.
- **If it does not:** P3's executor improvises the promtool/amtool supply and the test layout
  that slice 027 is about to rule on. The two slices then collide in PrometheusDeploy's gate
  whichever runs first.

The executor cannot settle this. Only the operator can.

### Q2 — The standing out-of-sync alert covers only auto-synced apps. Ruling D1 has no such limit, and no ruling records it.

**Problem.** Ruling D1 says "an app still out of sync, or still degraded, some minutes after the
failure … fires and stays up until the app recovers". The attachment (`standing-alerts.md:35-40`)
and Not in scope (plan.md:266-267) exclude every app Argo CD does not auto-sync:

- `argocd-prd` today;
- any app in a D5 cutover with `autoSync` off.

A failed sync of such an app gets only D7's event, which expires in 5 minutes. That is ANS-47's
defect as filed, left in place for those apps. V01 and V04 are worded to the narrowed scope.

**Evidence.** The design separates a failed sync from D5 drift with the `SyncError` condition
(`standing-alerts.md:72-74`). Upstream v3.5.1 sets that condition only inside `autoSync`, and
`autoSync` returns early for an app without automated sync (`controller/appcontroller.go:2332-2334`,
condition at `:2396-2399`). `argocd_app_info` alone cannot tell "manual sync failed" from "manual
sync not yet run". So the exclusion follows from the chosen signal. It is not something the
executor could close. The plan-writer flagged it in its r1 verdict summary, but no ruling in
plan.md accepts it.

**Impact.** One app today, and the operator runs that sync at the keyboard. Still, it narrows an
operator ruling without the operator's word. The rulings section is the only steering the doc
phase gets, so the doc phase will describe D1 as ruled, not as planned.

## Blocking

None.

## Advisory

### A1 — P4 numbers the record-only tag differently from the runbook's manual recovery, which the plan says stays valid

**Evidence.**
- P4: "The tag number is the build writing it" (plan.md:216-217), and "The manual recovery …
  stays valid" (plan.md:223-224).
- The runbook the plan cites uses the other number: "`<m>` is the failed build's number"
  (`Ansible/docs/runbooks/kubecoder-cutover.md:775-778`). Its recipe writes "promoted to prd by
  KubeCoder/Promote-PRD #<m>".

**Impact.** One situation gets two outcomes, depending on which recovery path is taken:

- recovered by hand, it is `release-<failed build>`;
- recovered by a job re-run, it is `release-<re-run build>`, and the tag carries the re-run's
  date.

D48 makes this tag "the only durable record of when anything was released". The doc phase will
meet both conventions when it updates the runbook's now-stale "A rerun refuses with *nothing to
promote*" line.

### A2 — No push order is recorded between ArgoCDDeploy and PrometheusDeploy

**Evidence.**
- `## Push holds` has four independent bullets (plan.md:132-137).
- V01-V03 are `owed_after` `../PrometheusDeploy`.
- The series they read are owed after `../ArgoCDDeploy` plus a manual sync of `argocd-prd` (V06).
- The plan loop seeds one Outstanding-actions entry per held repo, so nothing in the operator's
  runbook orders the two.

**Impact.** If PrometheusDeploy is pushed first, the blind warning (V05) fires as soon as the
rules load. It stays up until ArgoCDDeploy is pushed and synced. That push alone also cannot
settle V01/V02's live check.

## Checked and holding

- **AC coverage.** Every requirement maps to criteria, and none falls to the doc phase:

  | Requirement | Criteria | Earned by |
  |---|---|---|
  | R1 | V01-V07 | P1-P3; V07 by P1 |
  | R2 | V08 | P2 |
  | R3 | V09 | closed by Ruling D2; checkable from the diff |
  | R4 | V10-V11 | P4 |
  | R5 | V12-V13 | P5 |

  The criteria use the operator's wording. There are no doc-truth universals.
- **Task shape.** `cross-cutting` holds. slice.md leaves R1's mechanism to the planner ("Leave to
  the planner"), and the work lands in four deploy repos plus the spec repo.
- **Targets.** All five are existing sibling repos. The spec repo is a legal `Target:`. The
  bullets in `## Push holds` follow the template's shape.
- **R2.**
  - Upstream v3.5.1 checks `return_url` against `url` + `additionalUrls` (`util/oidc/oidc.go:449-450`)
    and picks the redirect URI per request host (`util/settings/settings.go:2301-2323`;
    `oidc.go:282-289`).
  - Chart 10.3.3 passes `configs.cm` keys through unchanged (`_helpers.tpl` `argo-cd.config.cm`).
  - Keycloak's auth endpoint for client `argocd` answers 200 for
    `redirect_uri=https://argocd/auth/callback` and 400 for an unlisted one. So the "not checked in
    Keycloak itself" hedge now holds on evidence.
- **R1 signals.**
  - `argocd_app_info` carries `autosync_enabled`, `sync_status`, `health_status` and `operation`
    (`metrics.go:66-68`, `:424-451`).
  - `argocd_app_condition` exists only with `--metrics-application-conditions` (`metrics.go:177-183`,
    cmd `:286`). The chart templates only `--metrics-application-labels`, and it has
    `controller.extraArgs`.
  - Each refresh sets or clears `SyncError` (`appcontroller.go:1955-1966`), and a completed
    operation forces a refresh (`:1646`). This works even with `timeout.reconciliation: 0s`.
  - Prometheus chart 29.33.0's `kubernetes-service-endpoints` job has `honor_labels: true`, maps
    Service labels to target labels (including `helm.sh/chart`) and adds `node` from the pod. That
    is consistent with the attachment's "identity is the app, not the scrape target".
- **R1 routing.** The route tree, `repeat_interval: 12h` and both receivers' `send_resolved: true`
  are at `PrometheusDeploy/config/prd/values.yaml:327-367`. `resolve_timeout` is unset.
- **R4.**
  - `Jenkinsfile.promote` has the refusal at `:71-74`, the other refusals at `:75-82`, "Advancing
    prd" at `:112-116` and "Recording the release" at `:118-131`.
  - D48 says "`<n>` is the promote job's build number".
  - Live origin: `prd` is at `release-5`'s commit, so the first run after P4 does not turn the
    current tip into a record-only case.
- **R5.**
  - `gitblit-deployment.yaml:30-40` is the busybox `clean-lucene-locks`.
  - `git-sync.sh:42-75` keeps `gitblit.indexBranch` as full ref names for heads and tags.
  - The iac sidecar has `/usr/bin/busybox`.
- **Rulings.** No correction chains. The plan carries no doc-deliverable content. P1's bullets are a
  doc-task phase's outcome statement.
