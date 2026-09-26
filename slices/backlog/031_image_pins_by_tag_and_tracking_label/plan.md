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
  included — and deletes nothing. The slice's test phase shows the operator one night's
  would-delete list. Turning dry-run off is the operator's one-line change, filed as an
  Operator Action card (ANS project) once the test phase has shown that list. Accepted
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
    deploy-repo push starts a Jenkins build and an Architecture rebuild).
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
  measured). Some app images push a single build-number tag only (e.g. `dhcpapp:35`, whose label
  is `35`).
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

## Ordering constraints

- Cleanup never runs in deleting mode in this slice (Ruling D1). Before the dry-run CronJob is
  unsuspended, the new cleanup image (label rule) is built and pinned in RegistryDeploy, and
  KeycloakDeploy pins a per-build tag, so the dry-run list the operator reviews is the one the
  live switch would delete.
- The kaniko2 change (JenkinsPipelineUtils) lands before any DockerImages build that relies on
  the two-tag matrix push or the explicit tracking tag.

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
