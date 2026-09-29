# Close-out — slice 031 image_pins_by_tag_and_tracking_label

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-29 08:07 → 10:40 · 9 phases · 0 bail-outs · 1 test round · doc phase done · $67.66
(planner 20 %, research 19 %, rework 0 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Deploy repos pin images from `registry:5000` to per-build tags, never digests, and the image's
`tracking-tag` label, not the tag's name, decides what registry-cleanup may delete. kaniko2 takes
an explicit `trackingTag:` and refuses any tag outside the label's build series; every matrix
build pushes `<tag>-<build>`, which the pin stage writes (both KeycloakDeploy stages run one now);
kube-coder-tunnel-reclaim and Argo CD's webhook-relay pins are written by their builds.
registry-cleanup and the version-poller classify by the label, and cleanup runs nightly again in
dry-run, garbage collection included. argo-cd D53 carries the rule; the doc phase brought D47,
the runbooks and the repos' READMEs and design doc into line.

## Outstanding actions

Focus: A2's headline and Consequence predate round 2: steps 1–5 are pushed and live, and only
step 6, the ~41-repo digest-comment sweep, is still owed. The operator's own keystroke is the
dry-run flip (ANS-156), after reading the test phase's 217-tag would-delete list.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### ~~A1 — Check RegistryDeploy out in the environment that will run this slice, before the run~~ — resolved at planning: operator (2026-09-26) 'You dont have to restart to get the repo. Just clone it.' — RegistryDeploy cloned to /work/RegistryDeploy and declared in Ansible .kubecoder/config.yaml (Ansible 7154030); struck by plan-slice session, review r1

<details><summary>struck — body kept for the record</summary>

P7 targets `../RegistryDeploy`, and no environment clones that repo today: it is not in Ansible's `.kubecoder/config.yaml`. Before the run, add `- url: https://github.com/pvginkel/RegistryDeploy` to that file's `repos:` list in the environment that will run the slice, then `kc env restart`. Until then `run_loop.py run … --dry-run` reports P7's Target as "not an existing directory". The plan-writer did not make the edit. The Ansible checkout is per environment, and slice 029's run was active in another environment's checkout at planning time.

**Consequence:** Until this is done the run cannot start. P7 has no Target, so the cleanup job stays suspended and the slice cannot lift the pause.

**Provenance:** witnessed — plan-writer, planning, r1, plan.md P7 and run_loop.py --dry-run
**Disposition:**

</details>

### ~~A2 — The push chain (Ruling R1-Q2) stops after step 2 — JenkinsPipelineUtils, DockerImages, the keycloak build, RegistryDeploy and the comment sweep are still unpushed, pending confirmed prd authorisation~~ — closed by the operator, 2026-09-29; struck by close-out session

<details><summary>struck — body kept for the record</summary>

Plan.md's Ordering constraints (Ruling R1-Q2, operator "Agree with the rest", 2026-09-26) assign the test phase — not the operator — the whole push chain, unattended, prd rollouts included (explicitly, the Keycloak prd SSO outage its step 4 causes). This run's own dispatch carries a different deterministic fact from the driver: "the driver holds the devlock. Under that hold, pushing and rolling dev for this slice's verification is pre-authorised — do not ask for permission. prd stays operator-gated; nothing here touches it." The two do not agree: R1-Q2 authorises prd rollouts this run's dispatch does not.

Given that conflict and the stakes — a live Keycloak SSO outage, ~46 real GitHub repo pushes, and JenkinsPipelineUtils going live estate-wide the instant it is pushed, none of it reversible — this run treated the dispatch's narrower authorisation as the ceiling and stopped rather than resolve the conflict by guessing. It executed only the part of Ordering constraints step 2 that is provably dev-only or render-neutral in its live effect:

- KubeCoderDeploy pushed (rebased onto origin/main's moved tip by dev:rebase-agent first — origin had moved 6 commits ahead with automated CI pin commits; gate re-run green after the rebase; final commits 850d45d, 8d039ed). Live: kubecoder-dev's Argo Application auto-synced (webhook + PreSync Terraform hook) to Synced/Healthy on the new commit; the controller pod runs kube-coder-tunnel-reclaim:2565 pulling IfNotPresent. kubecoder-prd is untouched — it tracks the separate `prd` branch, unaffected by a `main` push, and was confirmed still on its prior revision.
- ArgoCDDeploy pushed (0bacce1, no rebase needed). Live: argocd-prd's Application reports Synced/Healthy at the new revision with no operation triggered — the render is unchanged (also confirmed by the phase's own before/after `helm template` diff), so nothing rolled. Argo's own Application never auto-syncs (D3) regardless.

Both are now proven live (verification.json V15, V16 marked pass).

Unpushed, still sitting exactly as each phase left them (committed, not pushed):

- JenkinsPipelineUtils `276beff` (P1) — goes live estate-wide, every Jenkins job everywhere, the moment it is pushed.
- DockerImages `18dadc8` (P4-P6, P8) — its build rewrites pins into RegistryDeploy, VersionPollerDeploy (goes live), KubeCoderDeploy, FieldnotesDeploy and ArgoCDDeploy; real prd rollouts follow.
- KeycloakDeploy (not checked out here; clone from GitHub) — the keycloak build (Ordering step 4) writes a per-build tag into both dev and prd stages; Keycloak runs one replica with Recreate, so prd gets a short SSO outage.
- RegistryDeploy `dca461d` (P7) — unsuspends the live registry-cleanup CronJob into dry-run; confirmed still `suspend: true` on image `:2548` live as of this run.
- The deploy-repo comment sweep (Ruling R1-Q3) across ~41 repos' `config/prd/values.yaml` plus KeycloakDeploy's `config/dev`.

Once prd authorisation is confirmed — either the operator reconfirms R1-Q2 stands for a resumed test-phase run, or runs the sequence by hand — the remaining work is exactly Ordering constraints steps 1 and 3-6 in plan.md, unchanged:

1. `cd /work/JenkinsPipelineUtils && git push origin main`.
2. `cd /work/DockerImages && git push origin main` (it was 5 ahead / 1 behind origin as of this run — rebase first if still behind), then wait for the build (`track_build.py`, on PATH), confirm every auto-synced Application it fed is Synced/Healthy on its new pin, and that the live poller's first polls trigger nothing `phases/P5/poller-dryrun-*.log` did not already list.
3. Start a DockerImages build with `image=keycloak`; confirm both KeycloakDeploy stages Synced/Healthy on the new per-build tag.
4. `cd /work/scratch/RegistryDeploy && git push origin main` (only once DockerImages' P4 pin and both Keycloak stages are in place); confirm the CronJob is unsuspended, in dry-run, and has run; then, per Ruling D1, start one Job by hand from the CronJob, read its log, put the would-delete list before the operator (V01/V03), and only then file the Operator Action card to turn dry-run off (V04) — never before that list exists.
5. The comment sweep (Ruling R1-Q3): push RegistryDeploy's corrected comment string into every other deploy repo that carries the old one, a few at a time, checking each batch's builds and Applications stay green before the next.

The exact per-step checks live in plan.md's "Ordering constraints" section, which a re-entered test phase should re-read in full before proceeding — this entry summarises it, it does not replace it.

test-agent, test phase, round 2, 2026-09-29 — The driver directed this round to push what the slice committed. The authorisation-scope question
this entry raised is settled in favour of pushing: JenkinsPipelineUtils, DockerImages (rebased
onto a moved origin/main first), the keycloak build, and RegistryDeploy (rebased twice, onto each
of DockerImages' and the keycloak build's automated pin commits) are now all pushed and
live-verified — Ordering constraints steps 1, 3, 4 and 5 are done. Detail:

- DockerImages build #2570 (registry-cleanup, version-poller, kube-coder-tunnel-reclaim,
  webhook-relay): every fed Application reached Synced/Healthy on its new pin — registry-prd,
  version-poller-prd, kubecoder-dev outright; fieldnotes-prd after one Argo-internal PreSync-hook
  retry (Argo's own `Job has reached the specified backoff limit` -> automatic retry -> success;
  the failed attempt's pod was garbage-collected before its log could be read, so the root cause
  of that one attempt is not known — no sibling hook Job in the same burst failed, ruling out a
  node-wide issue). argocd-prd correctly went OutOfSync (a real webhook-relay rebuild this time,
  not render-neutral) and stays there for the operator, per D3.
- The keycloak build (#2571) rebuilt the image at a new digest and pushed both the named tag and
  the per-build tag onto it, writing the pin into both KeycloakDeploy stages in one commit
  (c416f0c). Both keycloak-dev and keycloak-prd went Synced, Progressing (the Recreate rollout,
  prd's brief SSO outage), then Healthy, running the per-build tag.
- RegistryDeploy (e9a16ee) unsuspended the CronJob into dry-run live: `suspend=false`,
  `DRY_RUN=true`. Unsuspending fired an automatic catch-up Job at once (S4's prediction), and a
  second, hand-started one followed per Ruling D1 (`registry-cleanup-test-phase-r1`); both logged
  identically (217 tag deletions, GC included, nothing deleted). The would-delete list was
  checked clean of every live pin — including resolving each of several ambiguous-looking
  "manifest eligible for deletion" GC lines live against the registry to confirm they name
  already-superseded digests, not current ones — and filed to the operator as ANS-156 (V01-V04
  now pass; see verification.json for the full evidence trail).

Only Ordering constraints step 6 remains: the deploy-repo comment sweep across ~41 other repos
(Ruling R1-Q3). That is new editorial work across many external repos, not a previously-reviewed
commit sitting unpushed, so it was not folded into this round's "push what's owed" and needs its
own pass.

**Consequence:** Until this runs, R1's pause stays lifted only on paper: registry-cleanup is still suspended live, so the registry keeps growing and V01-V04 stay unproven. KeycloakDeploy's two stages stay pinned by digest — the exact failure mode that lost Keycloak's image on 2026-09-25. The ~41-repo comment sweep and the estate-wide kaniko2/registry-cleanup/version-poller behaviour, already shipped in code, stay inert until JenkinsPipelineUtils and DockerImages are pushed.

**Provenance:** witnessed — test-agent, test phase, round 1: this run's live kubectl/git checks, plus plan.md's Ordering constraints and this run's own dispatch text
**Disposition:** This has been done already. — checked 2026-09-29: the step-6 comment sweep is on origin/main in all 47 repos (/work/scratch/sweep031) and no stage values carry the old comment; closed

</details>

## Notable events

Focus: the test phase bailed out after push step 2 on a conflict between Ruling R1-Q2 and its
dispatch (N1); round 2 pushed the rest on the driver's direction, Keycloak's prd roll included,
with one self-healed fieldnotes-prd PreSync retry (N2).

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### ~~N1 — Test phase round 1 bailed out mid push-chain on a dispatch/plan authorisation conflict, after proving the two safe steps live~~ — closed by the operator, 2026-09-29; struck by close-out session

<details><summary>struck — body kept for the record</summary>

All nine phases were merged and confirmed consistent (consult 1, complete). The test phase's own procedure — plan.md's Ordering constraints, driven by Ruling R1-Q2 — calls for the test phase itself to push the entire chain unattended, prd rollouts included. This run's dispatch instead pre-authorised only pushing and rolling dev under the devlock and stated prd stays operator-gated with nothing here touching it. Rather than guess which reading governs a live Keycloak SSO outage and ~46 real repo pushes, this run pushed only the two steps it could independently prove have no live prd effect (KubeCoderDeploy — dev-only rollout, verified Synced/Healthy; ArgoCDDeploy — render-neutral, verified Synced/Healthy with no operation triggered) and stopped before DockerImages. See Outstanding actions for the conflict and the exact remaining command sequence.

Every static/code-level verification item (V07, V08, V10-V16, V18-V20 — twelve of twenty) independently confirmed pass by dedicated sub-agents reading the actual code, tests and already-executed dry-run logs against the plan's claims, with no discrepancy found anywhere. The eight items needing the unrun part of the push chain (V01-V06, V09, V17) are marked owed, not fail, per this repo's testing-strategy doc §5 — the underlying implementing work is shipped and committed in every case; only the live rollout is outstanding.

**Consequence:** none beyond what Outstanding actions A2 already states — this entry is the narrative, A2 is the runbook

**Provenance:** witnessed — test-agent, test phase, round 1
**Disposition:** Ok — closed

</details>

### ~~N2 — Test phase round 2: the driver directed pushing what was owed; the push chain completed through step 5, live, with one self-healed Argo hook blip~~ — closed by the operator, 2026-09-29; struck by close-out session

<details><summary>struck — body kept for the record</summary>

Following round 1's bail-out (N1), the driver's next dispatch stated plainly that unpushed,
reviewed work is owed and directed pushing it, per the procedure doc's push step, waiting for the
CI builds it names and redoing invalidated live checks. That resolved round 1's authorisation
question in favour of completing the chain. This round pushed JenkinsPipelineUtils, rebased and
pushed DockerImages, triggered and waited out the keycloak build, then rebased and pushed
RegistryDeploy (twice rebased, once past each automated pin commit DockerImages' and the keycloak
build's own runs wrote to it) — Ordering constraints steps 1 and 3-5, each checked live before the
next (detail in Outstanding actions A2's note). Twelve of twenty verification items move from
owed to pass this round (V01-V05, V09), leaving only the comment sweep (step 6) and its dependent
item (V06) plus V17's full completion open.

One real hiccup along the way: fieldnotes-prd's Argo PreSync Terraform hook failed once
mid-burst ("Job has reached the specified backoff limit") while five deploy repos' pin commits
synced in quick succession from the DockerImages build; Argo's own retry succeeded seconds later
with a clean `terraform apply` (0 changes). The failed attempt's pod was already garbage-collected
by the time its log could be read, so the one-off's root cause is not known; no sibling hook Job
in the same burst failed, which rules out a node-wide cause. Recorded here per "never dismiss a
failure as flaky" — it is not being waved away, just noted as unresolved because the evidence is
gone.

**Consequence:** none — every check this round ran came back clean; the open remainder is scoped in Outstanding actions A2

**Provenance:** witnessed — test-agent, test phase, round 2
**Disposition:** Ok — closed

</details>

## Bugs

Focus: one bug, B1, witnessed in review and in this slice's own version-poller: a stale
environment can go unwarned when one build is promoted into two, today only DesignAssistant's
archived path. Nothing triggers differently.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### ~~B1 — version-poller warns about only the newest promoted copy per label, so a stale prd env promoted from the same label as a fresher uat env goes unwarned · minor~~ — closed by the operator, 2026-09-29; struck by close-out session

<details><summary>struck — body kept for the record</summary>

DockerImages version-poller/app/poller.py:159-170 (P5, 1a69ff9) keeps one promoted copy per tracking-tag label, the one with the newest rebuild-at, and warns only about it. The old code warned about each stale copy on its own. DesignAssistant's uat-* and prd-* copies both carry tst-latest. With uat-latest fresh and prd-latest 60 days stale, the old code warned about prd-latest and the new code is silent (repro witnessed). The live dry run shows the same collapse: the old code warned about design-assistant:prd-latest and :uat-latest, the new code only about :uat-17. KubeCoder, with a single promoted env, is unaffected, and the collapse keeps KubeCoder's accumulating prd-<n> copies from each warning.

**Consequence:** For an app that promotes one build into two environments (today only DesignAssistant, on the archived HelmCharts path), the poller log no longer says when the later environment has gone stale while the earlier one is fresh. Nothing triggers differently.

**Provenance:** witnessed — code-reviewer, P5, round 1, phases/P5/code_review_r1.md F1
**Disposition:** Close. — closed

</details>

## Open questions and rulings

Focus: Q1 first. Once dry-run is off, about ten weeks without a KubeCoder promotion lets the cap
delete the tunnel-reclaim image kubecoder-prd's controller pod needs. Q2 only leaves four repos
uncleaned.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — KubeCoder prd's tunnel-reclaim pin is refreshed only by promotion, so a long gap between promotions can put it past the keep-newest cap

After P2 and P6, DockerImages' builds write the tunnel-reclaim pin on KubeCoderDeploy's `main`. prd picks it up only when KubeCoder is promoted (Settled). The image's bare build numbers are in `latest`'s series, capped at the newest 10, and it rebuilds about weekly: the registry held tags 2475 to 2531 on 2026-09-26. About ten tunnel-reclaim builds without a promotion put prd's pinned build over the cap. R1 assumes the continuous rebuilds keep every pin fresh, but this pin also depends on how often KubeCoder is promoted. A nightly dry-run list would show it before any deleting run. The plan changes nothing here; Settled routes the pin through promotion.

**Consequence:** Once dry-run is off, if KubeCoder prd goes about ten weeks without a promotion, cleanup deletes its tunnel-reclaim image. The kubecoder-prd controller pod then cannot start again after a reschedule; the chart says a missing one takes the controller down.

**Provenance:** read — plan-writer, planning, r1, KubeCoderDeploy chart/values.yaml:13-18 and the live registry's tag list
**Disposition:** I'm aware. I need to regularly promote. That being said, I think the scheduled image rebuild should be handled special. Can you create an Operator Actions card for KubeCoder to think about this? Can we auto-promote these? I would even accept that we don't allow a promotion to be held for more then x (3 or 4 I think) days. If the build isn't promoted within that interval, it's forced. — KC-109 (Operator Action, KubeCoder)

### ~~Q2 — Four registry repos hold a dangling tag, and under the label rule it stops every deletion in its repo · minor~~ — closed by the operator, 2026-09-29; struck by close-out session

<details><summary>struck — body kept for the record</summary>

tags/list names the tag but its manifest returns 404: architecture_viewer:1540, backup-server:1890, dnsmasq-config-generator:1806, dnsmasq-management-api:1806. A tag with no image config carries no label, so the label rule keeps it, and the fail-closed shared-digest guard (kept for argo-cd D47) then skips every deletion in that repo, because the kept tag's digest does not resolve. The old tag-shape rule read these tags as history and skipped only them. The P4 dry run against the live registry shows it: architecture_viewer has 231 builds in its latest series and 221 over the cap, and none would be deleted. The operator decides: remove the dangling tag links in the registry's storage, or rule that a kept tag whose manifest returns 404 protects nothing and does not stop the repo.

**Consequence:** Once dry-run is off, these four repos are never cleaned: architecture_viewer keeps its 221 over-cap builds and keeps growing. Nothing is deleted wrongly.

**Provenance:** witnessed, code-writer, P4, r1, phases/P4/cleanup-dryrun-new.log
**Disposition:** Don't worry about this. At some point I'll do a full scan of the registry. You can't go off what's there now. I know, it's a mess at the moment. — closed

</details>

## Suggestions

Focus: S1 and S3 are read, and they sit on the failure this slice closed: argo-migrate would
recreate a digest pin, and Keycloak's `Always` pull blocks its start while the registry is down.
S4 was witnessed and the test phase saw it happen. S5 and S7 are doc nits.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — argo-migrate would write registry image digests, and the old comment, into a future migration's values

`compose_values` (`Ansible/support/argo-migrate/argo_migrate.py:466-493`) copies what HelmCharts' deploy CLI passed, including the release's resolved image digests, into `config/<stage>/values.yaml`. It writes them under the comment that P7 and P10a–P10b correct. The only stages left to migrate are the parked ones: design-assistant ×4, open-webui and shell. DesignAssistant's images are in our registry. The plan leaves the tool alone, because R2 names the deploy repos and the comment, and slice 029's P7 is changing the same tool. A fix would have the tool pin the build tag, in the image's label series, that points at the release's digest, and stop when no tag does.

**Consequence:** Migrating a parked app whose images are in our registry creates a digest pin again. Once dry-run is off, the nightly garbage collection can delete the image behind that pin, which is how Keycloak lost its image.

**Provenance:** read — plan-writer, planning, r1, argo_migrate.py:466-493
**Disposition:** Is this still an issue? Everything's migrated. I don't see a reason to use argo-migrate again. Is this about something else?

### ~~S2 — KubeCoderDeploy chart/values.yaml's new header says the chart names no default for any image, yet the file defaults env-pod images · nit~~ — resolved by consult 1 (KubeCoderDeploy 20e0f71): the header now claims no default for the chart's eight image pins only; kc project lint and test green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

chart/values.yaml:7 ('The chart names no default for any image (D47): every image pin lives in config/<stage>/values.yaml') is contradicted by the same file's image defaults at :112 (registry:5000/kube-coder-dev:latest), :164 (postgres:18), :203, :234, :262 and :294. The replaced comment made the claim only for Build-Main's seven pins.

**Consequence:** none — a comment that overstates its scope; no rendered object changes

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

</details>

### ~~S3 — KeycloakDeploy pulls its image with imagePullPolicy: Always, which a per-build tag no longer needs · minor~~ — fixed in KeycloakDeploy d854bb7; struck by close-out session

<details><summary>struck — body kept for the record</summary>

KeycloakDeploy chart/templates/keycloak-deployment.yaml:29-30 runs registry:5000/keycloak{{ .Values.images.keycloak }} with imagePullPolicy: Always. Once the keycloak build the test phase starts (step 4) writes the per-build tag 26.7.3-postgres-health-ispn-<build>, the image behind the pin never changes, so Always only makes every pod start ask the registry first. With Always, a registry that is not serving fails the pull even when the image is cached on the node; IfNotPresent would start from the cache. P2 moved KubeCoderDeploy's tunnel-reclaim to IfNotPresent with its tag pin; no phase of this slice touches Keycloak's chart.

**Consequence:** After a power cut, Keycloak cannot start until the registry serves again, even on a node that still holds its image. DHCP depended on Keycloak in the 2026-09-25 outage.

**Provenance:** read, executor, P6, r1, KeycloakDeploy main chart/templates/keycloak-deployment.yaml
**Disposition:** Fix inline please. — fixed in KeycloakDeploy d854bb7 (imagePullPolicy IfNotPresent; kc project lint and test green); not pushed yet

</details>

### ~~S4 — RegistryDeploy: unsuspending registry-cleanup starts a Job at Argo sync, not at the next 03:30 — P7's done-record says 03:30Z · nit~~ — closed by the operator, 2026-09-29; struck by close-out session

<details><summary>struck — body kept for the record</summary>

The live CronJob has no startingDeadlineSeconds, concurrencyPolicy Allow, and lastScheduleTime 2026-09-25T01:30Z. When suspend flips to false, Kubernetes creates a Job for the most recent missed schedule immediately. So the first unsuspended run starts when Argo applies P7, on whatever registry-cleanup image is pinned at that moment. The plan's P7 'Later phases' now records this for the test phase.

consult 1, 2026-09-29 — P7's done-record already carries the correction as its 'review r1 F1' later-phase note: the sync that drops suspend starts one Job at once, and with concurrencyPolicy Allow it can overlap the hand-started run. The test phase reads it there; nothing more is owed.

**Consequence:** none on the planned path: the ordering puts the P4 pin in place before the push, so the immediate run is a dry run. The test phase will see an automatic dry-run Job next to the one it starts by hand.

**Provenance:** witnessed (kubectl get cronjob), code-reviewer, P7, r1, phases/P7/code_review_r1.md F1
**Disposition:** Close. — closed

</details>

### ~~S5 — DockerImages version-poller-redesign.md states cleanup defaults of 5 builds per series and a 4-week TTL; registry-cleanup's are 10 and 26 weeks · nit~~ — fixed in DockerImages 7a6ce6b; struck by close-out session

<details><summary>struck — body kept for the record</summary>

The design doc's §8 ("Per-series cap (N = 5)", "Defaults: TTL = 4 weeks") and §11's defaults table give 5 and 4 weeks. registry-cleanup/app/main.py defaults --max-per-series to 10 and --ttl-weeks to 26, and the RegistryDeploy CronJob passes neither flag, so the live job runs with 10 and 26. P8 renamed the row's flag and knob to the label rule and left the numbers alone: choosing them is DI-5's, out of this slice's scope.

**Consequence:** none on behaviour — a reader sizing the cap or TTL from the design doc reads numbers the job does not use

**Provenance:** read, code-writer, P8, r1, DockerImages docs/registry-management/version-poller-redesign.md
**Disposition:** Fix inline. — fixed in DockerImages 7a6ce6b; not pushed yet

</details>

### ~~S6 — DockerImages version-poller-redesign.md §4 lists a lone version tag such as 1.35.5 among the builds in use; that is k8s's matrix tag, which now pushes 1.35.5 plus 1.35.5-<n> · nit~~ — resolved by consult 1 (DockerImages 18dadc8): the lone-version-tag bullet is gone from §4's builds in use; comment-only, the loop's gate sweep re-runs on it; struck by consult 1

<details><summary>struck — body kept for the record</summary>

The "builds in use" list in §4's tag scheme (docs/registry-management/version-poller-redesign.md:166) ends with "a lone version tag such as 1.35.5, labelled as itself". 1.35.5 is k8s/build-matrix.json's tag, and since P6 every matrix build pushes <tag> + <tag>-<n> (Jenkinsfile:159-161). P1's caller survey found no other caller that pushes a lone non-numeric tag. kaniko2 still accepts one, so the line is wrong only in calling it a build in use.

**Consequence:** none on behaviour — a reader of the design doc may take the k8s image to have no per-build tag

**Provenance:** read, code-reviewer, P8, r1, phases/P8/code_review_r1.md F1
**Disposition:**

</details>

### ~~S7 — DockerImages webhook-relay/README.md's 'Where it is deployed' table is stale: Fieldnotes' relay is deployed by FieldnotesDeploy, not HelmCharts' chart, and argocd-prd's relay no longer forwards to the applicationset-controller · nit~~ — fixed in DockerImages 221b012; struck by close-out session

<details><summary>struck — body kept for the record</summary>

The table (README.md:144-147) names 'HelmCharts, chart fieldnotes' as Fieldnotes' deployer and 'argocd-server and the applicationset-controller' as argocd-prd's receivers; the RECEIVERS example at :103 carries the applicationset-controller leg too. webhook-relay/deploy-pins.json names FieldnotesDeploy config/prd/values.yaml (images.webhookRelay) and ArgoCDDeploy config/prd/values.yaml (relay.image), and ArgoCDDeploy a811fa5 dropped the applicationset-controller leg. Neither staleness comes from this slice, so the doc phase left the page alone; argo-cd design.md points at this README as the relay's contract.

**Consequence:** A reader of the relay's contract page looks for Fieldnotes' relay in the archived HelmCharts and expects argocd-prd to forward to a controller it no longer calls. Nothing runs differently.

**Provenance:** read — doc-writer, doc phase, r1: DockerImages webhook-relay/README.md, webhook-relay/deploy-pins.json, ArgoCDDeploy git log a811fa5
**Disposition:** Fix inline. — fixed in DockerImages 221b012 (table and RECEIVERS example); not pushed yet

</details>
