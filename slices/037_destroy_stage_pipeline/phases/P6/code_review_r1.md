# P6 code review — round 1

**Readiness: signoff.** `docs/runbooks/argocd.md` gains § Destroying a retired stage, and it meets
the phase's outcome and V19. It says when the procedure applies (after the undeploy, with a link),
gives the dry run then the apply with their stage names, covers the guard's three refusals, what
the build forgets, re-runs, a root that does not plan alone, and the webhook. The undeploy
paragraph no longer says "until D28 is designed" and points to the section, citing D66.

I checked each quoted log line and message verbatim against ArgoCDTools `main`:
`presync/destroy.py` (`d7db58f`), `declarations.py:50` and `proc.py:13`, and
`Jenkinsfile.destroy-stage` (`fa32363`). The stage names, the Job name, the 1800 s deadline, the
`waitForJobContainer` path (JenkinsPipelineUtils `vars/kubectl.groovy:43-91`) and the lock branch
(`decisions.md:576`) all match. So do the KubeCoderDeploy variable claim (`terraform/variables.tf`
at `origin/main` `5b23a28`) and every in-page anchor.

The three findings are prose and advisory. F1 is the only one whose words would do harm if
followed, and it cannot be reached until KubeCoderDeploy's destroy plans (close-out I2). The root
gate ran green and does not cover markdown.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high · close-out P5

§ The webhook (`docs/runbooks/argocd.md:577-580`) tells the operator to restore the surviving
stage's hook this way: "set `manage_webhook = true` in its tfvars after the destroy, on the branch
it tracks, push". The case the paragraph names is KubeCoderDeploy's `prd`, which tracks the `prd`
branch (ArgoCDDeploy `releases/values.yaml:172-174`). For that case, the step is a commit pushed
straight to `prd`. argo-cd D35 forbids exactly that: "`prd` never carries a commit `main` doesn't"
(`argo-cd/decisions.md:594`). KubeCoderDeploy's promote job refuses "a move that is not a
fast-forward" (KubeCoderDeploy `README.md:30-33`) and has no force-move (D47). So an operator who
follows the runbook leaves every later KubeCoder promotion refused until `prd` is reconciled by
hand. Today this cannot happen: KubeCoderDeploy's destroy fails at the plan (close-out I2), as the
runbook's own § A build that fails at the plan says. It becomes reachable once that is fixed, and
nothing in I2's fix would touch this paragraph.

### F2 — Minor · advisory · anchor: none · confidence: high · close-out P6

§ A build that fails at the plan (`docs/runbooks/argocd.md:553-554`) says that a root needing more
fails the Job "at `init` or `plan`, before anything is written". That holds for a dry run, but not
for an apply whose state holds namespaced objects. There, `destroy()` runs `terraform state rm`
against the stored state (`presync/destroy.py:143-145`) before the plan that fails
(`destroy.py:149`). The runbook's own apply log list shows the same order
(`docs/runbooks/argocd.md:455-456`). The operator reads that nothing was written while the
namespaced entries are already gone from the stage's state. No harm follows: those objects are
forgotten by design, and a re-run is unaffected.

### F3 — Minor (nit) · advisory · anchor: none · confidence: medium · close-out P7

The undeploy paragraph (`docs/runbooks/argocd.md:391-396`) now defines what stays as "what the
stage's Terraform made" and lists "the deploy repo's GitHub webhook if the stage manages it". The
old text named the webhook unconditionally. A repo whose hook was made by hand (§ Webhooks,
"Any other deploy repo needs its webhook made by hand") keeps that hook after an unregister, and
the paragraph no longer says so. The same sentence also takes in the stage's namespaced Terraform
objects, which do not stay: they go with the namespace, as § What the build forgets says.

## Out of scope, recorded for the doc phase

`docs/runbooks/kubecoder-cutover.md:988` still cites D28 ("nothing prunes a state"). The states it
names are `helm-charts/…`, which Destroy Stage does not reach. P6's scope was `argocd.md`, so this
is not a finding. It is noted under P6's Later phases in the plan.
