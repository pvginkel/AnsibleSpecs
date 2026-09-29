# Slice 031 — Deploy repos pin per-build tags, never digests; every matrix build gets a per-build tag; the image's tracking-tag label decides what registry-cleanup may delete; cleanup runs again in dry-run

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

#### Requirements (slice.md, verbatim)

- R1. **[Major — DI-8] registry-cleanup must never delete an image a deploy repo pins, and the
  pause is lifted.** Card: "registry-cleanup must never delete an image a deploy repo pins (GC
  --delete-untagged, keep-newest cap)" … "**The job is paused; lifting the pause is part of this
  card.**" As ruled by the operator (2026-09-26), **without** reading what is deployed: "I decided
  earlier that knowing what's deployed is out of scope. If our continuous rebuilds work, there
  will always be a fresh image. And I haven't yet enabled auto cleanup, so it's not yet a
  problem." The card's "once cleanup reads the in-use set (deploy-repo pins, running pods and
  ReplicaSets) and fails closed when it can't read it" is therefore **not** a requirement.
- R2. **[Decision — ANS-125] Deploy repos pin tags, never digests.** Operator: "I didn't realize
  DockerImages is writing hashes. I really don't like that. I would like a card explaining how
  this came to be and an ask by me to reconsider this." Ruled ("Go", 2026-09-26) on the
  session's recommendation: "pin tags only, never digests" for images from the estate's
  registry; "every image from our registry would be pinned to a build-number tag. A
  build-number tag is never rebuilt, so it always points at the same image"; "correct the
  'digest the release runs' comment that the migration left in every deploy repo, and amend
  D53."
- R3. **[Decision — ANS-125, operator's extension] Every matrix build gets a per-build tag.**
  Operator: "Arguably all matrix builds get this behavior." Ruled ("Go") on the session's
  wording: "Every matrix build would push `<tag>-<build>` next to the named tag, and the pin
  stage would write the per-build tag wherever a `deploy-pins.json` exists, which today is only
  Keycloak. The other seven keep pulling their named tag."
- R4. **[Minor — C3, superseded by the operator's ruling] The image's label, not the tag's name,
  decides what is build history.** Operator: "As for what counts as a build number. I feel the
  now obvious answer is that we just make this explicit using a label. That solves a whole slew
  of problems. It does need an alternate Kaniko invocation and a cross repo migration." …
  "Let's go with this then." The session's proposal it answered (session's wording):
  `kaniko2` already stamps `org.webathome.poller.tracking-tag`; a tag is tracking only if its
  name equals that label on the image it points to, every other tag is build history; `kaniko2`
  takes an explicit `trackingTag:` with the current derivation from tag shapes as the default;
  images without the label are never cleaned, so the migration can be gradual; the
  version-poller's fallback to the label (`version-poller/app/poller.py`) stops being a
  fallback. — **Refined by Ruling D2 below** (which non-label tags are build history).
- R5. **[Minor — C2] `kube-coder-tunnel-reclaim:latest`.** Session's wording, folded in by the
  operator ("Go"): "**KubeCoderDeploy runs `kube-coder-tunnel-reclaim:latest`,** a moving tag
  that nothing pins."

#### Standing rulings from triage (slice.md)

- The standing tag-scheme rule in DockerImages `docs/registry-management/version-poller-redesign.md`
  §4 ("one tag … by definition the tracking tag", "No exotic schemes", the mirror classifier
  `^\d+$` / `^.+-\d+$`) is overruled by R3 and R4: the plan moves §4, and wherever else the
  design doc and argo-cd D53 state them, to match.
- Knowing what's deployed is out of scope (argo-cd D47's scope note, 2026-08-16; DI-5).
- The full registry analysis is the operator's own action (Operator Action DI-9), not this
  slice's work.
- Outside (upstream) images pinned by digest are ANS-139, not this slice.

#### Rulings (2026-09-26, operator: "Agree" on each decision in refinement.md)

- **Ruling D1 — how the pause comes off.** The slice adds a dry-run setting to the
  registry-cleanup chart (RegistryDeploy), removes the suspension with dry-run on, and lets the
  nightly job run for real in that mode: it logs what it would delete — garbage collection
  included — and deletes nothing. The slice's test phase shows the operator the would-delete
  list: once the unsuspended dry-run CronJob is live, the test phase starts one run from it by
  hand (a Job created from the CronJob — dry-run, garbage collection included), reads that
  run's log and puts the list before the operator; the nightly runs follow on their own
  (review r1 Q1, operator 2026-09-26: "Agree"). Turning dry-run off is the operator's one-line
  change, filed as an Operator Action card (ANS project) by the test phase, after that list
  exists — never before. Accepted
  trade-off: the registry keeps growing until the operator flips it; "the pause is lifted" is
  met as "the job runs again", not "the job deletes again". The slice itself never runs cleanup
  in deleting mode.
- **Ruling D2 — build history is the label's own build series.** Cleanup deletes only tags it
  recognises as the build's own history — the label's build series: label `latest` owns the
  bare build numbers; label `dev-latest` owns `dev-<n>`; a matrix label such as
  `26.7.3-postgres-health-ispn` owns `26.7.3-postgres-health-ispn-<n>`. A tag that is neither
  the label nor in its series is kept. Accepted trade-off: KubeCoder's promoted `prd-<n>` tags —
  one per promotion — are never cleaned and accumulate; the operator's registry analysis can
  set a rule for them later.
- **Ruling D3 — Argo CD's webhook-relay pin is written by the relay's builds.** ArgoCDDeploy
  joins `webhook-relay/deploy-pins.json`; the pin moves from ArgoCDDeploy's chart default into
  its production stage values, and every relay build writes it there as it does
  FieldnotesDeploy's. Accepted trade-off: every relay rebuild leaves Argo CD's own application
  (`argocd-prd`, synced by hand) out of sync until the operator next syncs it.
- **Settled (session, shown to the operator in refinement.md, not objected to):**
  - Unlabelled tags are neither cleaned nor counted toward the keep-newest cap.
  - Builds that push only a build number are labelled so that number falls in the label's
    series; otherwise each such build would be its own tracking tag and never be cleaned.
  - The migration's digest comment is corrected in batched deploy-repo pushes (every
    deploy-repo push starts a Jenkins build and an Architecture rebuild) — by the test phase,
    per Ruling R1-Q3 below.
  - KubeCoderDeploy's "deliberate float" chart comment and its render test's assertion of
    `:latest` change with the tunnel-reclaim pin; the pin reaches prd through KubeCoder's normal
    promotion like its other images.
  - KubeCoder environments: no change (the controller resolves toolchain images to a digest
    afresh at every bring-up — `KubeCoder/controller/src/kubecoder_controller/image_digests.py`, D274).
  - Keycloak pins a per-build tag before cleanup deletes anything: the slice gets the first tag
    pin into KeycloakDeploy itself rather than waiting for the 2026-10-01 rebuild.
  - The version-poller classifies tags by the same label rule; its copy of the old tag-shape
    regex goes with cleanup's.
  - `registry garbage-collect --delete-untagged` stays: with tag-only pins it can no longer
    delete a pinned image.

#### Rulings from plan review r1 (2026-09-26, operator: "Agree with the rest")

- **Ruling R1-Q2 — no phase pushes; the test phase pushes everything, in dependency order,
  and is authorised to roll prd.** Every phase commits only and is reviewed before anything it
  wrote goes live. The test phase then pushes in the order the live chain needs — the shared
  library (JenkinsPipelineUtils) → KubeCoderDeploy and ArgoCDDeploy → DockerImages (its build
  writes the pins: RegistryDeploy, VersionPollerDeploy, KubeCoderDeploy, FieldnotesDeploy,
  ArgoCDDeploy) → the keycloak build (both KeycloakDeploy stages onto the per-build tag) →
  RegistryDeploy (the dry-run CronJob) → the deploy-repo comment batches — each step's live
  check green before the next, stopping at the first red. The operator authorises this run's
  test phase to make these pushes and the prd rollouts they cause unattended, including
  Keycloak prd's short SSO outage (the same rollout the poller's 2026-10-01 rebuild would
  cause). Argo CD's own application (argocd-prd) stays synced by the operator (Ruling D3).
- **Ruling R1-Q3 — the comment sweep is not a phase.** The corrected wording is written and
  reviewed once, in RegistryDeploy's copy (the RegistryDeploy phase). The test phase applies
  that exact string in place of the old one in every other deploy repo and pushes them in
  batches (Settled). The five repos with a different migration header change only where they
  claim digests, and each such change is listed in the close-out.
- **Ruling R1-A1 — every label series keeps its newest build.** registry-cleanup's floor keeps
  the newest build of each label series whether or not the label's own tag exists in the repo,
  so an old self-labelled bare number (live example: `ssegateway-validation:56`, labelled `56`,
  built 2026-09-24) counting as a tracking tag cannot switch the floor off. Tested with the
  label rule.
- **RegistryDeploy is checked out** under `/work/scratch/RegistryDeploy`, not declared in
  Ansible's `.kubecoder/config.yaml` (operator, 2026-09-27: a repo a slice needs belongs in
  scratch). An environment that runs this slice clones RegistryDeploy and KubeCoderDeploy into
  `/work/scratch/` first.

#### Grounding (session, verified 2026-09-26 — binds the plan)

- **registry-cleanup** (`DockerImages/registry-cleanup/app/main.py`): `_VERSIONED` regex at :29
  (comment: keep in sync with `version-poller/app/tagging.py:20`, which carries the same
  regex); GC hardcoded `registry garbage-collect --delete-untagged` (:143-148), run by
  `kubectl exec` into the registry pod; defaults `--max-per-prefix 10`, `--ttl-weeks 26`
  (:408-416) — the CronJob passes only `REGISTRY_URL`. Algorithm today: non-versioned tags always
  kept; versioned tags grouped by prefix family, newest 10 kept (sorted by numeric suffix), rest
  deleted; survivors older than 26w deleted; a digest still referenced by a kept tag is never
  deleted; a repo with no tracking tag keeps its newest versioned tag. It already fetches image
  configs but reads only `org.webathome.poller.rebuild-at`. `--dry-run` exists as a CLI flag
  only. Tests: `registry-cleanup/tests/test_cleanup.py` (pytest), run by no CI.
- **RegistryDeploy**: `chart/templates/registry-cleanup-cronjob.yaml:7-10` — suspend comment +
  `suspend: true` (commit `5ccb234`, 2026-09-25); no dry-run value in the chart; pins
  `registryCleanup: ':2548'`. Argo CD auto-sync on; prd only, no dev stage. Live: suspended,
  last schedule 2026-09-25T01:30Z (the deleting run).
- **kaniko2** is in `JenkinsPipelineUtils/vars/helmCharts.groovy`: stamps
  `org.webathome.poller.tracking-tag=${trackingTag}` (:100); `resolveTrackingTag` (:144-166)
  accepts one destination, or two only as `latest`/`<n>` or `<p>-latest`/`<p>-<n>`, and throws
  otherwise — so `<tag>` + `<tag>-<build>` is refused today and the check must change. Called
  from `DockerImages/Jenkinsfile` (:147, :154) and from app repos' Jenkinsfiles (count not
  measured). Some images push a single build-number tag only (live: `ssegateway-validation:56`,
  labelled `56`, built 2026-09-24). `dhcpapp:35` (labelled `35`) is a leftover: dhcpapp has
  pushed `latest` + `<n>` since build 36 (review r1 A1).
- **DockerImages pin stage**: `Jenkinsfile:120` `if (!isMatrix) builtImages << image`;
  `collectPins()` (:33-54) reads `<image>/deploy-pins.json` only for images in `builtImages`;
  the stage (:171-187) calls `cicd.writeVersionPins(repo:, pins:, message:)`
  (`JenkinsPipelineUtils/vars/cicd.groovy:37` — clones the deploy repo, patches named YAML paths,
  commits, pushes). App repos pin their own images through the same `cicd.writeVersionPins`.
  Matrix images (8 `build-matrix.json`, one tag template each): k8s, keycloak,
  kube-coder-esp-idf/frontend/java/modern-app-toolchain, modern-app-dev-playwright,
  ubuntu-full. 26 `deploy-pins.json`; only keycloak's is on a matrix image (KeycloakDeploy
  `config/dev` and `config/prd`, `images.keycloak`).
- **Promotion**: 44 of ~47 deploy repos have no promotion — one pin commit writes the same tag
  into every stage. KubeCoderDeploy is the exception: dev tracks `main` (`dev-<n>`), prd tracks
  the `prd` branch; CI forward-writes `prd-<n>` on `main`; `Promote-PRD` does
  `crane tag dev-<n> prd-<n>` and fast-forwards `prd`. `crane tag` copies labels, so `prd-<n>` /
  `prd-latest` carry `dev-latest`; DesignAssistant's (HelmCharts-archived) `uat-latest` /
  `prd-latest` carry `tst-latest` — hence Ruling D2.
- **Pin freshness, measured against the live registry**: 73 in-registry pins; all but these are
  the newest build: KeycloakDeploy (both stages, `@sha256:45ae4959…`, commit `075184c`);
  DnsmasqDeploy/prd `dhcpapp-ui:45` and ElectronicsInventoryDeploy/prd
  `electronics-inventory-ui:251` — each has five higher-numbered **unlabelled** May/June tags
  (`dhcpapp-ui:{46,50-53}`, `electronics-inventory-ui:{308,313-316}`) crowding the cap, which the
  label rule removes from the count; ArgoCDDeploy `chart/values.yaml:58`
  `registry:5000/webhook-relay:2539` (hand-bumped `307d94f`; FieldnotesDeploy is at 2555);
  KubeCoderDeploy `chart/values.yaml:18` `tunnelReclaim: :latest` (used at
  `controller-deployment.yaml:228`; asserted by `tests/render-chart.py` R13; built at
  `DockerImages/kube-coder-tunnel-reclaim/`, non-matrix, no `deploy-pins.json`).
- **Label coverage**: registry at `http://registry:5000` (reachable from the pod); 131 repos,
  117 with tags; ~59 fully labelled, ~36 mixed, 22 with no labelled tag at all; ~1,220 of 1,395
  tags labelled.
- **The digest comment** ("each image at the digest the release runs (argo-cd D53)") is in 41
  deploy repos' `config/prd/values.yaml` plus KeycloakDeploy's `config/dev` (42 copies); 5 repos
  carry a different migration header (Elasticsearch, Fieldnotes, Filebeat, IacProvisioner,
  Zigbee2mqtt — check whether theirs mentions digests); ArgoCDDeploy and KubeCoderDeploy carry
  neither. Deploy repos are not cloned under /work — they are on GitHub under the same owner as
  this repo's origin.
- **D53** (`AnsibleSpecs/argo-cd/decisions.md:835-848`) never mentions digests: the amendment
  adds "per-build tags, never digests", it corrects no sentence. The "what's deployed" scope
  note is the Promotion-and-CI Scope Note (:465) with its "Still true after D47" amendment
  (:472-477).
- **version-poller**: label fallback at `version-poller/app/poller.py:125-132`
  (`_recover_self_tracking_tags`, :220-236).
- **Keycloak's next rebuild** is due by its `rebuild-at` label, 2026-10-01T19:11Z; harmless while
  cleanup is suspended or in dry-run.

## Task shape

cross-cutting — the ask spans the shared library's `kaniko2`, DockerImages (registry-cleanup,
version-poller, the pin stage), RegistryDeploy, KeycloakDeploy, KubeCoderDeploy, ArgoCDDeploy,
~46 deploy repos and the spec repo, and sets an estate-wide rule (the tracking-tag label decides
build history).

## Ordering constraints

- **No phase pushes; the test phase pushes, in this order (Ruling R1-Q2).** Every phase commits
  only. The test phase's dispatch says prd stays operator-gated: for this slice, Ruling R1-Q2 is
  the operator's authorisation for these pushes and the prd rollouts they cause, unattended, and
  Ruling D1 for the dry-run Job it starts in prd. Each step's check is green before the next
  step starts. At the first red — a build, an Application, a check — push nothing more and hand
  back what is left unpushed.
  1. **JenkinsPipelineUtils** (P1). Every job loads the library unpinned from `main`
     (`DockerImages/Jenkinsfile:3`), so the push is live estate-wide. Its check is the builds
     the next steps start. Step 3's DockerImages build is the first to call the new `kaniko2`.
  2. **KubeCoderDeploy and ArgoCDDeploy** (P2, P3). They go before DockerImages: its pin lists
     name the paths P2 and P3 add, and `cicd.writeVersionPins` refuses a path the values file
     does not already hold (`JenkinsPipelineUtils/vars/cicd.groovy:16-17`). Check: kubecoder-dev
     is Synced and Healthy on the pinned tunnel-reclaim tag. argocd-prd is still Synced, because
     P3's move is render-neutral.
  3. **DockerImages** (P4–P6, P8). The push builds each changed image folder: registry-cleanup,
     version-poller, kube-coder-tunnel-reclaim and webhook-relay. It writes their pins to
     RegistryDeploy (the CronJob is still suspended), VersionPollerDeploy (the new poller goes
     live), KubeCoderDeploy's `main`, FieldnotesDeploy and ArgoCDDeploy. Check:
     - the build is green (`Ansible/tools/ai_workflow/track_build.py`);
     - every auto-synced Application it fed is Synced and Healthy on its new pin;
     - argocd-prd is left out of sync for the operator (Ruling D3);
     - the live poller's first polls trigger nothing that P5's dry run did not list.
  4. **The keycloak build.** Start a DockerImages build with the job's `image` parameter
     (`DockerImages/Jenkinsfile:60`) set to `keycloak`. It pushes
     `26.7.3-postgres-health-ispn-<build>` and writes it into both KeycloakDeploy stages in place
     of the digest. Check: both stages are Synced and Healthy on the per-build tag.
     - Keycloak runs one replica with `Recreate` (ANS-126), so each stage has a short SSO outage.
       It is the same rollout the 2026-10-01 rebuild would cause.
     - A push that touched both stages once failed the second stage's sync on a hook-Job name
       clash (AnsibleSpecs `handovers/dhcp-outage-2026-09-25/plan.md:45-48`). homelab-shared
       0.3.1 has since given each app a fixed hook Job name (KeycloakDeploy `a5d978a`).
     - If a keycloak build has already written the per-build pin since step 3, that build
       counts. The poller's rebuild is due 2026-10-01T19:11Z.
  5. **RegistryDeploy** (P7). Push only once its `origin/main` pins the P4 cleanup build (step
     3's pin commit) and KeycloakDeploy pins a per-build tag in both stages (step 4). Check: the
     live CronJob is not suspended, is in dry-run and runs the P4 build. Then, per Ruling D1:
     - start one run from the CronJob by hand, as a Job created from it;
     - put its would-delete list, tags and garbage collection both, before the operator: keep
       the run's log in the slice folder and put a summary in the close-out report;
     - check that the list holds no tag or digest that a deploy repo pins (V01);
     - only then file the Operator Action card (ANS) to turn dry-run off.
  6. **The comment sweep** (Ruling R1-Q3).
     - Take RegistryDeploy's corrected comment as merged. Put that exact string in place of the
       old one in every other deploy repo that carries it. The grounding counted 41
       `config/prd/values.yaml` copies plus KeycloakDeploy's `config/dev`; measure rather than
       trust that count.
     - The five repos with a different migration header (Elasticsearch, Fieldnotes, Filebeat,
       IacProvisioner, Zigbee2mqtt) change only where they claim digests. Each such change is
       listed in the close-out. ArgoCDDeploy and KubeCoderDeploy carry neither comment.
     - Push a few repos at a time, because every deploy-repo push starts its `AaC/<Repo>` build
       and an Architecture rebuild. The next batch starts only when this batch's builds are
       green and its Applications are still Synced and Healthy. A comment renders nothing new.
     - A repo whose `origin/main` already carries the corrected comment is done, so a
       re-entered test phase resumes where a stop left off.
- **Deploy repos move under the run.** Builds commit pins to deploy repos' `main` at any time:
  KubeCoder's to KubeCoderDeploy continuously, and DockerImages' to RegistryDeploy, KeycloakDeploy
  and ArgoCDDeploy. Every push goes onto the current `origin/main`, rebased over the pin commits
  that landed meanwhile. Never force-push.
- **Deploy repos that are not under `/work` are read and edited in scratch clones.** This covers
  KeycloakDeploy and the rest. Clone them under `/tmp` (`GH_TOKEN` has repo scope), never into
  `/work`.

### P1 — kaniko2 takes the tracking tag explicitly, and every tag it pushes is the label or in its build series ✅ DONE 2026-09-29

Target: ../JenkinsPipelineUtils

`kaniko2` accepts an explicit tracking tag (R4: `trackingTag:`). Without one, it derives the
label from the destinations as it does today (`vars/helmCharts.groovy:144-165`). The exception
is a build that pushes a lone bare build number: it is labelled `latest`, so the number falls in
`latest`'s series (Settled). The destination check that refuses a matrix build's `<tag>` +
`<tag>-<build>` today (`:162-164`) changes with it. A build may push the tracking tag and tags in
its build series, as Ruling D2 defines the series, and nothing else. P4 relies on that invariant
to trust the label.

- **Every existing caller keeps building unchanged.** The library goes live estate-wide the
  moment the test phase pushes it. Not all callers are checked out here:
  - checked out: DockerImages, KubeCoder, ArgoCDTools, Charts, Architecture and Ansible's
    `Jenkinsfile.iac-image`;
  - on GitHub only: the app repos that call `helmCharts.kaniko` or `kaniko2`.

  Some callers push a single build number only. Live example: `ssegateway-validation:56`,
  labelled `56`, built 2026-09-24.
- The doc comment on `kaniko2` states the new contract.

**Done (P1).** JenkinsPipelineUtils `276beff` (`phase/031-P1`, committed, not pushed): `kaniko2`
takes `trackingTag:`. Without it, the label is the one destination whose build series holds every
other one, and a lone bare build number is labelled `latest`. It refuses a destination that is
neither the label nor in its series, and a bare-number label, explicit or derived. The series is
`inBuildSeries(tag, label)` in `vars/helmCharts.groovy`: `latest` owns `^\d+$`, `<p>-latest`
owns `<p>-<digits>`, any other label `L` owns `L-<digits>`. New `tests/.../TrackingTagTest.java`;
`kc project test` green.

Later phases:
- P4, P5: classify with exactly this series rule — a label ending `-latest` owns `<p>-<digits>`,
  not `<p>-latest-<digits>`. No image kaniko2 labels from now on carries a bare-number label, so a
  self-labelled bare number is a leftover.
- P6: pass `trackingTag: <tag>` with destinations `<tag>` + `<tag>-<build>`. No matrix tag is bare
  digits or ends in `-latest` (every `*/build-matrix.json` checked).
- P8: §4's "Tag scheme (enforced by `kaniko2`)" is now the contract in kaniko2's doc comment.
- Test phase: the one caller whose label changes is SSEGateway's `ssegateway-validation:<n>`
  (a lone bare number, now labelled `latest`, not `<n>`).

Record:
- Callers: 30 `Jenkinsfile*` on GitHub (gitblit search) plus the checked-out repos. They push
  `<n>` + `latest`, `dev-<n>` + `dev-latest` (KubeCoder), `<p>-<n>` + `<p>-latest`
  (DesignAssistant), one named matrix tag (DockerImages) or a lone `<n>` (SSEGateway). None
  passes `trackingTag`, and none is refused. Each gets today's label, except the lone `<n>`.
- The derivation is general. It gives today's label for every set the old check accepted, and it
  also accepts `<tag>` + `<tag>-<n>`. At most one destination can own all the others.
- An explicit tracking tag need not be pushed. `LibraryCompileTest.trustedLoader()` is now
  package-private, for the new test's `@NonCPS` calls.

### P2 — KubeCoderDeploy pins kube-coder-tunnel-reclaim to a build ✅ DONE 2026-09-29

Target: ../scratch/KubeCoderDeploy

KubeCoderDeploy stops running `kube-coder-tunnel-reclaim:latest` (R5). The controller pod's
tunnel-reclaim container runs a build-number tag of the image: the newest build when the phase
runs. The pin sits where the repo's pin convention puts image pins (argo-cd D47 and D53), at a
path that P6's pin list names, so DockerImages' builds rewrite it. These go with the float:

- the "deliberate float" comment (`chart/values.yaml:16-18`);
- the render test's `:latest` assertions (`tests/render-chart.py:82-83`, `:226-230`,
  `:384-389`).

The container's pull policy follows the other pinned images'. It is `Always` today
(`chart/templates/controller-deployment.yaml:229`); the controller uses `IfNotPresent` (`:47`).
prd gets the pin through KubeCoder's normal promotion (Settled), never through a commit on
`prd`.

**Done (P2).** KubeCoderDeploy `3de9ea8` (`phase/031-P2`, committed, not pushed): both stage files
pin `images.tunnelReclaim: ":2565"` (the newest build; `latest` points at the same digest), a tag
suffix the chart concatenates onto `registry:5000/kube-coder-tunnel-reclaim`. The chart names no
default (`images: {}`) and `required`-guards the key; the container pulls `IfNotPresent`. The
render gate checks each stage's pin is `:<digits>`, both stages name one build, the rendered
container runs it pulling `IfNotPresent`, and a stage without it fails to render.
`kc project test` green.

Later phases:
- P6: `kube-coder-tunnel-reclaim/deploy-pins.json` names `pvginkel/KubeCoderDeploy`, files
  `config/dev/values.yaml` and `config/prd/values.yaml`, path `images.tunnelReclaim`, default
  value template (`:{tag}`). Both files, one commit: the render gate refuses stages on different
  builds.
- Test phase: pushing KubeCoderDeploy changes kubecoder-dev's controller pod spec (`:latest` →
  `:2565`, pull policy), so the pod rolls onto the same digest. prd takes it at the next
  Promote-PRD, whose retag step reads only Build-Main's seven pins and leaves this one alone.

Record:
- prd's copy of the pin is written on `main` alongside dev's; `Jenkinsfile.promote`'s `prdPins`
  reads only the seven `kubecoder-*` paths, so the bare build number never reaches its
  `prd-<n>` check.
- `cicd.writeVersionPins` patches the quoted `":2565"` line in place (the path resolves through
  the comment above it).

### P3 — ArgoCDDeploy's relay pin moves into its production stage values

Target: ../ArgoCDDeploy

Ruling D3. The relay's image pin moves from the chart default (`chart/values.yaml:53-58`) into
`config/prd/values.yaml`, at a path that P6's pin list names. Every relay build then writes it
there, as it writes FieldnotesDeploy's. The chart comment that argues for a chart-level pin goes
with it. The render gate's relay assertions (`tests/render-chart.py:183-190`) keep holding.

The move is render-neutral: it keeps today's build (`2539`), so argocd-prd gets nothing new to
sync. The sync of Argo CD's own application stays the operator's (D3).

### P4 — registry-cleanup: the label decides what is build history, and a dry run covers garbage collection

Target: ../DockerImages

registry-cleanup classifies tags by the image's `tracking-tag` label (R4, refined by Ruling D2
and the Settled list). The label replaces the tag-shape regex (`registry-cleanup/app/main.py:27-29`):

- A tag is tracking only if its name equals the label on the image it points to.
- A tag is deletable history only if it is in that label's build series.
- Every other tag is kept and not counted toward the keep-newest cap. That covers unlabelled
  tags and promoted copies such as `prd-<n>`.

So `node-24` and `jdk-21` stop being read as builds 24 and 21.

The protections that stand today stay:

- the shared-digest guard that fails closed (`:344-370`), load-bearing since argo-cd D47;
- `--delete-untagged` (Settled);
- the floor that never empties a repo (`:317-326`), which now works per series (Ruling R1-A1).
  Every label series keeps its newest build whether or not the label's own tag exists in the
  repo. Today the floor fires only in a repo with no tracking tag (`:319`). An old
  self-labelled bare number counts as a tracking tag under the label rule, so a floor keyed that
  way would switch off. Live example: `ssegateway-validation:56`, labelled `56`, next to future
  builds labelled `latest` with no `latest` tag.

Further requirements:

- **A dry run is complete, and the chart can switch it on.** A dry run logs what the tag pass
  would delete and what garbage collection would delete, and deletes nothing. Today it skips
  garbage collection entirely (`:467`). The job takes the switch in a form the RegistryDeploy
  chart can set; today the image's command passes only `REGISTRY_URL`
  (`registry-cleanup/Dockerfile`). P7 consumes it.
- **Tests.** `registry-cleanup/tests/test_cleanup.py` covers:
  - the label rule: D2's three series shapes, a matrix per-build tag, a promoted copy and
    unlabelled tags;
  - the per-series floor, including a series whose label tag does not exist next to a
    self-labelled bare number;
  - the dry-run garbage collection.

  No CI runs these tests, so the phase runs them. No existing case is lost without a
  successor.
- **Proof.** Run a dry run of the new code against the live registry from this pod
  (`http://registry:5000`, reads only). Leave garbage collection out, because it needs the
  registry pod. The test phase's hand-started run is the first live run of it (Ordering
  constraints, step 5). The would-delete summary goes in the done-record.

### P5 — version-poller: the same label rule

Target: ../DockerImages

The version-poller classifies tracking tags by P4's label rule (Settled). Reading the label as
the rule itself (R4) replaces two things:

- its copy of the tag-shape regex (`version-poller/app/tagging.py:18-24`);
- the fallback that recovers `node-24`-shaped tracking tags from the label
  (`version-poller/app/poller.py:125-132`, `:220-238`).

Further requirements:

- **It starts no rebuild it does not start today, apart from the tracking tags the name
  heuristic misread.**
  - The registry still holds legacy build-number tags whose label names the tag itself. For
    example, `dhcpapp:35` carries `tracking-tag=35`, `pipeline=DHCP/DHCPApp` and
    `rebuild-at=2026-07-18T21:41:16Z`.
  - A literal reading of the rule makes each of these a tracking tag that is due now, and
    rebuilding an app through one redeploys the app.
  - Today they are skipped (`poller.py:233-234`). After P1, kaniko2 never stamps a bare number
    with itself, so these tags are only leftovers.
- **Tests** in `version-poller/tests/` cover the rule, the matrix per-build tag and the
  leftovers. No existing case is lost without a successor.
- **Proof.** Run a dry-run poll of the new code against the live registry. It only reads: the
  poller has a dry-run mode (`poller.py:59-67`, `:103-106`). The done-record lists what the poll
  would trigger and explains anything the old code would not have triggered. The test phase
  checks the live poller against that list (Ordering constraints, step 3).

### P6 — Matrix builds push a per-build tag, and the pin lists reach the unrefreshed pins

Target: ../DockerImages

- **Matrix builds (R3).**
  - Every matrix build pushes `<tag>-<build>` next to its named tag, and passes the named tag to
    kaniko2 as the explicit tracking tag (P1).
  - The pin stage writes the per-build tag wherever a `deploy-pins.json` exists, matrix images
    included. Today that is only `keycloak/deploy-pins.json`.
  - Today the pin stage skips matrix images (`Jenkinsfile:120-121`; `collectPins` at `:39-54`;
    the stage at `:171-187`).
  - The other seven matrix images keep pulling their named tag.
  - Keycloak's first per-build pin comes from the keycloak build the test phase starts
    (Ordering constraints, step 4). This phase is what makes that build write the pin.
- **Pin lists.**
  - `kube-coder-tunnel-reclaim` gets a pin list naming P2's path: `pvginkel/KubeCoderDeploy`,
    `images.tunnelReclaim` in both `config/dev/values.yaml` and `config/prd/values.yaml`, default
    value template.
  - `webhook-relay`'s list gains P3's ArgoCDDeploy path next to FieldnotesDeploy's (Ruling D3).
  - Every entry names a path its values file already holds with P2 and P3 merged. The pin stage
    fails on any other path (`JenkinsPipelineUtils/vars/cicd.groovy:16-17`).

### P7 — RegistryDeploy: cleanup runs again, nightly, in dry-run

Target: ../scratch/RegistryDeploy

Ruling D1. The registry-cleanup chart gets a dry-run setting, turned on, which drives P4's
switch. The CronJob's suspension and its comment go
(`chart/templates/registry-cleanup-cronjob.yaml:7-10`). The nightly job then runs for real, in
dry-run mode. This slice never runs cleanup in deleting mode.

The setting reaches a cleanup image that understands it. The test phase pushes this repo only
after DockerImages' build has pinned the P4 cleanup build here (Ordering constraints, step 5).
Until then the file pins `:2548` (`config/prd/values.yaml:32`).

RegistryDeploy's copy of the migration's digest comment (`config/prd/values.yaml:26-27`) is
corrected here. It is the one copy that is written and reviewed. The test phase puts that exact
string into every other deploy repo (Ruling R1-Q3), so the wording must stay true in any deploy
repo's stage values:

- some of those files still pin an upstream image by digest until ANS-139, as this file's
  `images.registry` does;
- others pin only per-build tags.

### P8 — DockerImages' design doc states the label rule

Target: ../DockerImages

Triage overruled the standing tag scheme (R3, R4, Ruling D2). In
`docs/registry-management/version-poller-redesign.md`, these move to what P1 and P4–P6 shipped:

- §4's "Tag scheme (enforced by `kaniko2`)" and its mirror classifier (`:142-165`);
- every other place the doc states them, such as §8's keep and delete rules (`:405-412`) and
  §14's classification.

What shipped: the label decides, build history is the label's series, each series keeps its
newest build, a matrix build pushes two tags, and unlabelled tags are left alone.

### P9 — argo-cd D53: deploy repos pin tags, never digests

Target: ../AnsibleSpecs

R2's "amend D53" (`argo-cd/decisions.md:836-848`), in the register's own amendment style, dated,
in the operator's words from R2. D53 gains:

- images from the estate's registry are pinned to a per-build tag, never a digest;
- a matrix build gets one too, and the pin stage writes it wherever a pin list exists (R3);
- Argo CD's relay pin is written by builds like any other (Ruling D3).

D53 never mentions digests today, so the amendment adds the rule; it corrects no sentence.
Upstream images are ANS-139's.

## Not in scope

- Reading what is deployed (running pods, ReplicaSets, deploy-repo pins) in cleanup (R1 ruling).
- Upstream images pinned by digest (ANS-139).
- The registry analysis and any retention rule for promoted `prd-<n>` tags and unlabelled
  images (Operator Action DI-9).
- Flipping cleanup's dry-run off (the operator's switch, Ruling D1).
- Re-tagging or relabelling existing images in the registry; migration to labelled images is
  gradual, by rebuild.
- KubeCoder environment image resolution (settled: no change).
- `valid-until` expiry labels (DI-3) and DI-5's TTL/cap numbers.
- How argo-migrate composes a future migration's values. It still writes the release's
  digests and the old comment (`Ansible/support/argo-migrate/argo_migrate.py:466-493`); the
  close-out carries it.
