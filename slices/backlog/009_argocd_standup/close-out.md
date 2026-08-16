# Close-out — slice 009 argocd_standup

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Every entry, in every section, has exactly this shape. The id is the section's letter
     (A · N · B · Q · S) and the next number — count the section's `###` headings, struck ones
     included. Severity (major | minor | nit | cosmetic) sits in the heading of Bugs only.
     `Disposition:` is the operator's line: leave it blank.

     ### B2 — <headline: one line, the claim itself> · minor · <repo or component>

     <What: the thing itself, quoted where it is text or output — the sentence, the command and
     what it printed, the file and lines. Why it matters: the consequence, or "none" said plainly.
     How it was found. As many paragraphs as it takes.>

     Provenance: <role, phase, round; the artifact that holds the full record>
     Disposition:

     An entry is never deleted. Struck, it keeps its heading, with the reason appended:

     ### ~~S3 — <headline>~~ — absorbed by P11 (97b5313), struck by consult 1
-->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first; which are in this slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — Alertmanager has no receiver, so Argo's D7 notifications land in a UI nobody can reach · minor · HelmCharts

D7 turns Argo's notifications on from day one "to Alertmanager", and R9 proves a deliberate sync
failure produces a notification. Alertmanager is live and is a real target
(`prometheus-prd-alertmanager.prometheus-prd:9093`), but its configuration is still the chart's
stock null sink — `/work/HelmCharts/configs/prd/prometheus/prd/values.yaml:120-130` sets
`alertmanager.persistence` and a memory request and nothing else, so the live config is one empty
`default-receiver` with a route that points at it. Alertmanager also carries no
`nginx.webathome.org/server-name` annotation, so its UI is not exposed at all.

The consequence: an Argo sync failure will raise an alert that reaches Alertmanager and stops
there, visible only by querying its API from inside the cluster. That is enough for R9 as worded,
and this slice's plan says so explicitly (V14) rather than promising more. But the signal D7 exists
to provide — "today's `deploy wait` swallows rollout failures; this is the replacement signal" — is
not actually delivered to a human until a receiver exists. The estate already knows: the same gap
is recorded at `/work/AnsibleSpecs/handovers/memory-issues/HANDOVER.md:318-319` ("Alertmanager has
no receiver … every alert added here reaches the Prometheus/Alertmanager UI and nowhere else") and
the real alerting rules at `values.yaml:58-118` fire into the same void. A route/receiver design
exists and is unbuilt at `/work/DockerImages/docs/alert-manager/plan.md:240-330` (Telegram via an
ESO leaf, a 2×2 route tree).

Found while planning the notifications phase, checking what "produces an Alertmanager
notification" can be proven to mean.

Provenance: plan-writer, plan pass r1; plan.md P2 and verification.json V14
Disposition:

### B2 — `slice.md`'s ApplicationSet quote drops the `hook.namespace` parameter · nit · AnsibleSpecs

`slice.md`'s "Generating Applications" extract lists three helm parameters — `hook.repo`,
`hook.revision`, `hook.stage`. `design.md:201-209` lists four; the fourth is `hook.namespace`,
`'{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'`. The library chart's Job
`required`-guards all four (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:45-48`),
so an ApplicationSet built from the quote would fail to render **every** migrated app that includes
the hook — not just the hook Job, the whole chart.

`slice.md` already flags two of its own quotes as stale and says to take the `argo-cd/` set as
authoritative, so the plan is not misled: P3 names `design.md:155-273` as the template and calls
this omission out. The entry is here because the stale quote survives in a triage artefact that
later readers will reach for.

Provenance: plan-writer, plan pass r1; plan.md P3
Disposition:

## Open questions and rulings

Focus: <!-- doc-writer -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — the register's "~44 unmigrated releases the glob matches" is 15, and Phase B has to create the file

R16 and `phases.md` A.5 both describe the ApplicationSet's git generator matching "all ~44
unmigrated releases", which the selector must then exclude. The tree does not look like that:
`configs/prd/*/*/release.yaml` resolves to **15** files (checked 2026-08-16), against 51 app-stage
directories and 46 apps. `release.yaml` is the exception in this repo, not the rule — it exists only
where a release diverges from convention (`/work/HelmCharts/tools/deploy/README.md:89-106`), and a
local-chart release carries none at all, its chart name defaulting to the config directory name
(`tools/deploy/deploy_cli/release.py:174`).

Nothing about R16's proof changes — the 15 that *are* matched all lack `reconciler:` (`grep -rn
reconciler /work/HelmCharts/configs/` is empty) and must all be excluded, and `missingkey=error`
still means one leak breaks the whole set. What changes is a Phase B expectation: migrating a
local-chart app is not "add three keys to its existing entry", it is **creating a `release.yaml`
that does not exist yet** — KubeCoder included, whose `configs/prd/kubecoder/{dev,prd}/` hold only
`values.yaml`. Worth folding into slices 010–012's planning, and worth correcting in `phases.md`
and `design.md` when the doc set is next touched.

Provenance: plan-writer, plan pass r1; plan.md P3 and P6, verification.json V21
Disposition:

### S2 — `/work/KubeCoderDeploy` will hit the same empty-repo bootstrap trap this slice hit

`ArgoCDDeploy` had no commit on `main` **and** no `origin/main`, which would have failed the run
loop's merge-time `git checkout main` before P1 ever landed — the hazard slice 006 already named and
solved by seeding a root commit during refinement
(`slices/completed/006_charts_repo_and_charts_home/plan.md:67-71`). This pass seeded one (`e8cb797`,
a minimal `README.md`, left unpushed).

`/work/KubeCoderDeploy` is in exactly the same state — `.git` and nothing else, branch `main`, zero
commits — and slice 010 (`010_kubecoder_deploy_repo`) will target it. Seed a root commit there
before that slice's first phase runs, or plan for the driver to fail on it.

Provenance: plan-writer, plan pass r1; ordering constraints in plan.md
Disposition:

### S3 — the throwaway app's Terraform state outlives the throwaway app

A.5 says to delete the disposable app entry and its repo afterwards, and V27 checks that. Neither
deletes what the proof run wrote to the estate's state repo: the hook's backend key is
`argocd/<repo>/<stage>/terraform.tfstate` in `https://github.com/pvginkel/TerraformState` @ `main`,
hard-coded in the image (`/work/ArgoCDTools/presync/backend.py:22-23,44-54`). So after the drill,
`argocd/ProofDeploy/prd/terraform.tfstate` — a real, SOPS/age-encrypted state file describing an
object that no longer exists — stays in the state repo with nothing left to reference it.

Consequence is small and entirely tidiness: a stale key costs nothing operationally, and it is
arguably useful evidence that the backend leg worked. But it is the first state key the Argo path
ever writes, and nobody has yet decided who prunes state for an unregistered app — D28 leaves
*destroy* unimplemented, so this is the same question in miniature, arriving before Phase B does.
Worth an operator keystroke at close-out (delete the key, or keep it deliberately), and worth a line
in whatever eventually answers D28.

Found while planning P5a, working out what the proof repo's `terraform/` has to contain.

Provenance: plan-writer, plan pass r2; plan.md P5a
Disposition:

### S4 — the register says the hook needs PV `get`, and the code never issues one

R3 and `design.md`'s hook-namespace inventory both specify the `tf-presync` ServiceAccount's RBAC as
"PV get/list/patch" (`/work/AnsibleSpecs/argo-cd/design.md:418`). The reattach the grant exists for
issues exactly two calls: `GET /api/v1/persistentvolumes` — the collection, i.e. `list` — and
`PATCH /api/v1/persistentvolumes/<name>` with `application/merge-patch+json`
(`/work/ArgoCDTools/presync/reattach.py:18,42-49`, `presync/kube.py:21,40-53`). There is no
single-object GET anywhere in the hook, so `get` on `persistentvolumes` is granted for nothing.

This slice's P4 grants the requirement as written rather than narrowing it on its own authority —
the difference is one verb on one cluster-scoped kind, and a wrong guess here fails a sync rather
than a test. But the register is the document Phase B and any later audit will read, and it
currently overstates what the hook does. Correct it in `design.md` (and drop the verb from the
ServiceAccount) when the doc set is next touched, or record deliberately that the extra verb stays.

Provenance: plan-writer, plan pass r2; plan.md P4
Disposition:
