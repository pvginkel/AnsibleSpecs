# Close-out — slice 031 image_pins_by_tag_and_tracking_label

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### ~~A1 — Check RegistryDeploy out in the environment that will run this slice, before the run~~ — resolved at planning: operator (2026-09-26) 'You dont have to restart to get the repo. Just clone it.' — RegistryDeploy cloned to /work/RegistryDeploy and declared in Ansible .kubecoder/config.yaml (Ansible 7154030); struck by plan-slice session, review r1

P7 targets `../RegistryDeploy`, and no environment clones that repo today: it is not in Ansible's `.kubecoder/config.yaml`. Before the run, add `- url: https://github.com/pvginkel/RegistryDeploy` to that file's `repos:` list in the environment that will run the slice, then `kc env restart`. Until then `run_loop.py run … --dry-run` reports P7's Target as "not an existing directory". The plan-writer did not make the edit. The Ansible checkout is per environment, and slice 029's run was active in another environment's checkout at planning time.

**Consequence:** Until this is done the run cannot start. P7 has no Target, so the cleanup job stays suspended and the slice cannot lift the pause.

**Provenance:** witnessed — plan-writer, planning, r1, plan.md P7 and run_loop.py --dry-run
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — version-poller warns about only the newest promoted copy per label, so a stale prd env promoted from the same label as a fresher uat env goes unwarned · minor

DockerImages version-poller/app/poller.py:159-170 (P5, 1a69ff9) keeps one promoted copy per tracking-tag label, the one with the newest rebuild-at, and warns only about it. The old code warned about each stale copy on its own. DesignAssistant's uat-* and prd-* copies both carry tst-latest. With uat-latest fresh and prd-latest 60 days stale, the old code warned about prd-latest and the new code is silent (repro witnessed). The live dry run shows the same collapse: the old code warned about design-assistant:prd-latest and :uat-latest, the new code only about :uat-17. KubeCoder, with a single promoted env, is unaffected, and the collapse keeps KubeCoder's accumulating prd-<n> copies from each warning.

**Consequence:** For an app that promotes one build into two environments (today only DesignAssistant, on the archived HelmCharts path), the poller log no longer says when the later environment has gone stale while the earlier one is fresh. Nothing triggers differently.

**Provenance:** witnessed — code-reviewer, P5, round 1, phases/P5/code_review_r1.md F1
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — KubeCoder prd's tunnel-reclaim pin is refreshed only by promotion, so a long gap between promotions can put it past the keep-newest cap

After P2 and P6, DockerImages' builds write the tunnel-reclaim pin on KubeCoderDeploy's `main`. prd picks it up only when KubeCoder is promoted (Settled). The image's bare build numbers are in `latest`'s series, capped at the newest 10, and it rebuilds about weekly: the registry held tags 2475 to 2531 on 2026-09-26. About ten tunnel-reclaim builds without a promotion put prd's pinned build over the cap. R1 assumes the continuous rebuilds keep every pin fresh, but this pin also depends on how often KubeCoder is promoted. A nightly dry-run list would show it before any deleting run. The plan changes nothing here; Settled routes the pin through promotion.

**Consequence:** Once dry-run is off, if KubeCoder prd goes about ten weeks without a promotion, cleanup deletes its tunnel-reclaim image. The kubecoder-prd controller pod then cannot start again after a reschedule; the chart says a missing one takes the controller down.

**Provenance:** read — plan-writer, planning, r1, KubeCoderDeploy chart/values.yaml:13-18 and the live registry's tag list
**Disposition:**

### Q2 — Four registry repos hold a dangling tag, and under the label rule it stops every deletion in its repo · minor

tags/list names the tag but its manifest returns 404: architecture_viewer:1540, backup-server:1890, dnsmasq-config-generator:1806, dnsmasq-management-api:1806. A tag with no image config carries no label, so the label rule keeps it, and the fail-closed shared-digest guard (kept for argo-cd D47) then skips every deletion in that repo, because the kept tag's digest does not resolve. The old tag-shape rule read these tags as history and skipped only them. The P4 dry run against the live registry shows it: architecture_viewer has 231 builds in its latest series and 221 over the cap, and none would be deleted. The operator decides: remove the dangling tag links in the registry's storage, or rule that a kept tag whose manifest returns 404 protects nothing and does not stop the repo.

**Consequence:** Once dry-run is off, these four repos are never cleaned: architecture_viewer keeps its 221 over-cap builds and keeps growing. Nothing is deleted wrongly.

**Provenance:** witnessed, code-writer, P4, r1, phases/P4/cleanup-dryrun-new.log
**Disposition:**

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — argo-migrate would write registry image digests, and the old comment, into a future migration's values

`compose_values` (`Ansible/support/argo-migrate/argo_migrate.py:466-493`) copies what HelmCharts' deploy CLI passed, including the release's resolved image digests, into `config/<stage>/values.yaml`. It writes them under the comment that P7 and P10a–P10b correct. The only stages left to migrate are the parked ones: design-assistant ×4, open-webui and shell. DesignAssistant's images are in our registry. The plan leaves the tool alone, because R2 names the deploy repos and the comment, and slice 029's P7 is changing the same tool. A fix would have the tool pin the build tag, in the image's label series, that points at the release's digest, and stop when no tag does.

**Consequence:** Migrating a parked app whose images are in our registry creates a digest pin again. Once dry-run is off, the nightly garbage collection can delete the image behind that pin, which is how Keycloak lost its image.

**Provenance:** read — plan-writer, planning, r1, argo_migrate.py:466-493
**Disposition:**

### S2 — KubeCoderDeploy chart/values.yaml's new header says the chart names no default for any image, yet the file defaults env-pod images · nit

chart/values.yaml:7 ('The chart names no default for any image (D47): every image pin lives in config/<stage>/values.yaml') is contradicted by the same file's image defaults at :112 (registry:5000/kube-coder-dev:latest), :164 (postgres:18), :203, :234, :262 and :294. The replaced comment made the claim only for Build-Main's seven pins.

**Consequence:** none — a comment that overstates its scope; no rendered object changes

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### S3 — KeycloakDeploy pulls its image with imagePullPolicy: Always, which a per-build tag no longer needs · minor

KeycloakDeploy chart/templates/keycloak-deployment.yaml:29-30 runs registry:5000/keycloak{{ .Values.images.keycloak }} with imagePullPolicy: Always. Once the keycloak build the test phase starts (step 4) writes the per-build tag 26.7.3-postgres-health-ispn-<build>, the image behind the pin never changes, so Always only makes every pod start ask the registry first. With Always, a registry that is not serving fails the pull even when the image is cached on the node; IfNotPresent would start from the cache. P2 moved KubeCoderDeploy's tunnel-reclaim to IfNotPresent with its tag pin; no phase of this slice touches Keycloak's chart.

**Consequence:** After a power cut, Keycloak cannot start until the registry serves again, even on a node that still holds its image. DHCP depended on Keycloak in the 2026-09-25 outage.

**Provenance:** read, executor, P6, r1, KeycloakDeploy main chart/templates/keycloak-deployment.yaml
**Disposition:**

### S4 — RegistryDeploy: unsuspending registry-cleanup starts a Job at Argo sync, not at the next 03:30 — P7's done-record says 03:30Z · nit

The live CronJob has no startingDeadlineSeconds, concurrencyPolicy Allow, and lastScheduleTime 2026-09-25T01:30Z. When suspend flips to false, Kubernetes creates a Job for the most recent missed schedule immediately. So the first unsuspended run starts when Argo applies P7, on whatever registry-cleanup image is pinned at that moment. The plan's P7 'Later phases' now records this for the test phase.

**Consequence:** none on the planned path: the ordering puts the P4 pin in place before the push, so the immediate run is a dry run. The test phase will see an automatic dry-run Job next to the one it starts by hand.

**Provenance:** witnessed (kubectl get cronjob), code-reviewer, P7, r1, phases/P7/code_review_r1.md F1
**Disposition:**

### S5 — DockerImages version-poller-redesign.md states cleanup defaults of 5 builds per series and a 4-week TTL; registry-cleanup's are 10 and 26 weeks · nit

The design doc's §8 ("Per-series cap (N = 5)", "Defaults: TTL = 4 weeks") and §11's defaults table give 5 and 4 weeks. registry-cleanup/app/main.py defaults --max-per-series to 10 and --ttl-weeks to 26, and the RegistryDeploy CronJob passes neither flag, so the live job runs with 10 and 26. P8 renamed the row's flag and knob to the label rule and left the numbers alone: choosing them is DI-5's, out of this slice's scope.

**Consequence:** none on behaviour — a reader sizing the cap or TTL from the design doc reads numbers the job does not use

**Provenance:** read, code-writer, P8, r1, DockerImages docs/registry-management/version-poller-redesign.md
**Disposition:**
