# Slice 030 — refinement

## D1 — The validation pipelines run in the existing modern-app toolchain image and download Chromium at test time, rather than in a purpose-built browser image

**Context.** DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl run their validation
suite as a Kubernetes Job in modern-app-dev-playwright, tagged with the Playwright version read
from each app's pnpm lockfile. The suite is polyglot: a Python suite runner runs pytest for the
backend, then installs and builds the frontend, installs Chromium, and runs the Node Playwright
tests. This slice retires that image together with modern-app-dev underneath it, so the four
pipelines need another base.

**The ask.** The card that asked for the retirement left this one design point open: move the
validation stages onto the kube-coder toolchain images, or build a small purpose-built image for
what they actually run — "the four validation stages need a decided Playwright base either way".

**Background.** modern-app-dev-playwright adds exactly one thing to its base: Chromium for one
Playwright version, pre-downloaded into the user's cache. The suite runner already runs
Playwright's browser install on every run — with a comment saying it is a fast no-op on the
pre-baked image — so each app's browser already follows its own lockfile whenever it does
download. The kube-coder modern-app toolchain image (Node 24, pnpm, poetry, uv, ruff) already
carries Playwright's OS dependencies, only not the browser. Today an app's Playwright upgrade
first needs DockerImages' build matrix to declare the new version; the registry holds a 1.58.2
tag the matrix no longer declares, which shows the drift.

**Why yours.** It trades image-build cost against a per-run external download, and the card
left it to you.

**Recommendation.** Run the validation Job in the modern-app toolchain image, its Node 24
variant, and let the suite runner download Chromium at test time; drop the lockfile-derived
image tag. No new image, no per-version build matrix, and Playwright upgrades stop needing a
DockerImages change. Trade-off: every validation run downloads Chromium (on the order of
150 MB) from Playwright's download host, which adds time and an external dependency to each
run. Not verified: that the validation Job pods reach Playwright's download host (they reach the
npm registry today for the frontend install — itself not re-verified), and that the apps'
frontends are fine on Node 24; the first app's phase proves both on a real build before the
others follow.

**The other way.** A small purpose-built Playwright image — the modern-app toolchain plus a
baked Chromium per Playwright version. No download per run, but it keeps an image, its version
matrix and its weekly rebuild, which is what the retirement set out to remove.

**If this is wrong.** Slower or flaky validation runs from the download; recoverable by adding
the purpose-built image later without changing the pipeline shape much.

**Operator.** Agree

## D2 — DesignAssistant keeps its reference to the Playwright image: archived and disabled, it is exempt from "nothing references either image"

**Context.** Your done-criterion for the slice reads "nothing outside DockerImages references
either image". DesignAssistant's pipeline hardcodes the Playwright image on both its main and
develop branches, and its suite runner's remote mode names it too. When the retirement was split
into its own slice, the research called DesignAssistant's Jenkins job "still existing"; checked
this week, its jobs are archived and disabled since July, the app is deployed nowhere (every
stage disabled in HelmCharts, nothing on the cluster), and it was one of the apps deliberately
left unmigrated during the Argo CD migration.

**The ask.** Whether DesignAssistant gets the same pipeline change as the four live apps, or is
left as it is and recorded as an exemption from the done-criterion.

**Background.** With the image deleted, nothing breaks in DesignAssistant now: nothing builds
it. If it is ever revived, its pipeline needs reworking for Argo CD anyway, and the missing image
fails loudly at the first build.

**Why yours.** The done-criterion is your wording; exempting a repo narrows it.

**Recommendation.** Leave DesignAssistant untouched and record the exemption. Trade-off: one
repo keeps a reference to a deleted image, so the done-criterion holds for live pipelines, not
literally.

**The other way.** Make the same change there as in the other apps, on both branches — one more
phase, in a repo with no project gates, and it cannot be proven: its jobs are disabled, so the
edit ships untested.

**If this is wrong.** Nothing breaks now; a revival hits a missing image at its first build.

**Operator.** Design Assistant is archived. Do not include it in your work.

## D3 — The registry deletion is your final step: tags deleted through the API, the two repository entries removed from storage, and the space left to the next regular garbage collect

**Context.** The card pins the deletion itself: done when "the registry repos are deleted". You
have so far deliberately held off deleting registry images, and a deletion cannot be undone. The
registry's nightly cleanup job — a garbage collect that also removes untagged manifests — has
been suspended since 2026-09-25, after it deleted Keycloak's pinned image and contributed to the
DHCP outage; lifting that pause belongs to the registry-retention slice. The two repositories
hold about 2.8 GB between them: modern-app-dev, and modern-app-dev-playwright with two Playwright
tags.

**The ask.** How and when the two repositories go, the deletion itself being settled.

**Background.** No whole-repository delete exists anywhere in the estate. The registry's API
deletes manifests per tag — that is what the cleanup job does — and a repository's name leaves
the catalog only when its entry is removed from registry storage. Space is reclaimed only by a
garbage-collect pass. Not verified: the registry's storage backend and its delete setting — the
registry's deploy repo is not in this environment; the cleanup job's use of the delete API
implies deletes are enabled.

**Why yours.** The deletion cannot be undone, and the mechanism that reclaims the space is the
one behind the outage and is currently paused.

**Recommendation.** After every moved consumer has a green build, you delete both repositories'
tags through the registry API and remove the two repository entries from storage, following a
short procedure the slice adds to DockerImages' registry-management docs; no manual garbage
collect is run — the ~2.8 GB is reclaimed by the first regular pass once the registry-retention
slice lifts the pause. Trade-off: the space stays occupied until then.

**The other way.** Also run a one-off garbage collect right away, without the untagged removal,
to reclaim the space now — it needs the registry quiet for the run, and it is the kind of manual
pass you have held off on.

**If this is wrong.** A premature deletion breaks a consumer that was not moved; the green-build
gate before the step is what prevents it.

**Operator.** Agreed

## Open facts — questions only you can answer

**F1.** Is any of KubeCoder, FieldnotesApp, DHCPApp, ElectronicsInventory, IoTSupport or
ZigbeeControl mid-slice in another environment right now? A pipeline edit from here would
collide with that lane's branch; the answer settles whether those phases wait or go ahead.

**Operator.** Yes, but I'll just wait with implementing this slice into there's a quite moment.

## Settled

- KubeCoder and FieldnotesApp move to the modern-app toolchain image through a new
  shared-library container template beside the one the build-and-test-gates slice added for the
  iac toolchain; the Terraform provider's one stage on modern-app-dev — publishing to the
  provider registry — moves to that iac template; both toolchain images run as the same user
  (uid 1000) as modern-app-dev and carry every tool those stages run.
- "Nothing outside DockerImages references either image" is read over live pipelines, scaffolds
  and current docs and runbooks; historical records — completed slices, archived triage
  documents, about a hundred files — keep their mentions.
- The frontend scaffold template gets the image change only; its validation pipeline is stale
  beyond the image name (an older validation entrypoint, not the suite-runner shape the live
  apps use), and bringing it up to date goes into the close-out as a follow-up.
- The repos not in this environment — FieldnotesApp, DHCPApp, ElectronicsInventory,
  IoTSupport, ZigbeeControl, the frontend scaffold template, and DesignAssistant only if D2 goes
  the other way — are added to the environment's configuration during planning; you restart the
  environment before the run.
- Order: the new container template first, then each consumer, pushed and proven by a green
  Jenkins build — about seven app builds, each also deploying to the app's dev stage as any main
  push does; the old template and the two image directories go only after all consumers are
  green; the registry deletion last.
- Size: about twelve phases across ten repos plus the registry — the shared Jenkins library twice (a template
  for the modern-app toolchain image first, removing the modern-app-dev template last),
  KubeCoder, FieldnotesApp, the Terraform provider, DHCPApp, ElectronicsInventory, IoTSupport,
  ZigbeeControl, the frontend scaffold template, DockerImages (the two directories plus a
  registry-management doc section), and the registry deletion as your final step; DesignAssistant
  adds one phase if D2 goes the other way.
