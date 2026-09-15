# Slice 021 — refinement

## D1 — How the iac image pipeline hears the poller's weekly rebuild request: a build parameter, or a second always-building job

**Context.** The iac image pipeline builds the image only when a build's changeset is empty — its inference that the version poller started it — or touches one of six image inputs; a changeset carrying only other commits skips the image. The job declares no parameters, and the image does not carry the build-parameter label the poller stores on other images. The earlier slice that restructured the IaC pipelines declined a force parameter for this job, reasoning about manual forcing only ("replay the job or push a trivial change"); the poller case was left open. Jenkins jobs in the IaC folder are hand-created in the Jenkins UI; there is no job-as-code anywhere in the estate. Your ruling on the card widened it to every pipeline that conditionally builds an image, named two shapes — two-stage, or a signal the pipeline tests for, "e.g. the trigger field" — and called the first cleaner but more verbose.

**The ask.** The weekly rebuild the poller asks for actually builds, whatever else the changeset happens to carry.

**Background.** Two premises of the ruling no longer hold. The sweep is done: of the roughly 25 image pipelines the poller tracks, only two build conditionally, and DockerImages already hears the poller — the poller stores a build parameter in a label on the built image and hands it back when it triggers the rebuild, and DockerImages builds whatever image that parameter names regardless of what changed. Every other tracked pipeline builds on every trigger. So the iac image pipeline is the only deaf one, and this is one pipeline, not a sweep. And the trigger field cannot carry the signal: the poller triggers Jenkins as your own Jenkins user, so a poller build reads "Started by user Pieter van Ginkel", indistinguishable from a manual click. A build parameter is the signal that works. In the three weeks of builds Jenkins still holds, the card's skip never happened — both poller builds had empty changesets and built.

**Why yours.** You named both shapes and leaned toward two-stage as cleaner; you could still pick it.

**Recommendation.** The signal shape, reusing DockerImages' mechanism: the iac image carries the parameter label, the poller hands it back, and the pipeline builds whenever it is set. One pipeline, the estate's existing pattern, no new Jenkins job. Trade-off: the job gains a visible parameter under Jenkins' "Build with Parameters", which in practice is the manual force switch the earlier slice declined.

**The other way.** Two-stage — a detection job that starts a separate, always-building job the poller targets; costs a second Jenkins job you create by hand in the UI, a second pipeline file, and an estate solving the same problem two ways, since DockerImages keeps its parameter.

**If this is wrong.** Rework confined to one pipeline file; nothing breaks.

**Operator.** I think this is fine. So an optional image parameter, right? Comma separated like DockerImages? And then the image is built when either there are changes, or when the image name matches.

## D2 — How far the slice reaches into the version poller, where the rebuild that actually went missing was lost

**Context.** The card that reported the skip says a missed weekly rebuild is never retried — the poller's rebuild-at does not advance, and after its grace period the poller reports the image orphaned. The cards name the pipelines, not the poller, which lives in DockerImages.

**The ask.** A weekly rebuild that does not happen is retried rather than silently dropped.

**Background.** The complaint is real: the iac image went 19 days without a rebuild, Monday 24 August to Saturday 12 September, on a weekly schedule. The card's mechanism did not cause it. The poller runs daily at 03:00 UTC, and no build of the iac image job started at that hour on any day in between; the thirteen builds in the gap were daytime push builds that correctly skipped. The pipeline never got a poller build to skip. The cause is unknown: the poller's daily runs from that period are pruned from the cluster; one run, on 11 September, is on record as failed, its pod and logs gone; rebuilds resumed on 12 September. Not verified: whether the poller failed daily through the gap. Separately, a confirmed poller bug has the card's exact symptom: when a rebuild is due, the poller records it as triggered before checking whether the job is already building or queued; if it is, the poller moves on without triggering, the record persists, and it never triggers that rebuild again until the image is rebuilt some other way. Its "orphaned" report is only a log line. Nothing surfaces a stale image or a failed poller run to you — no alert rule for failed Kubernetes jobs was found; not verified: whether Prometheus's file-based rules cover it.

**Why yours.** This adds a repo and a component the cards did not name, and how much of the poller's silence the slice fixes — the retry alone, or the visibility too — is a scope call you make.

**Recommendation.** Bring the poller's retry into the slice: record a rebuild as triggered only once a build actually started, so a trigger that collided is retried the next day. File the unexplained 19-day gap and the silent orphaned report as a Triage card rather than grow this slice with an alerting design. Trade-off: the next poller outage is as silent as this one was — the slice fixes the retry, not the visibility.

**The other way.** Also make a stale image reach you in this slice — the poller's orphaned condition or a failed poller run turned into a notification; costs about one more phase and a choice of channel.

**If this is wrong.** At worst one more small change to the poller later; no breakage.

**Operator.** Agree. We could do something with Alertmanager or something like that. I'm not there yet on Alertmanager, so maybe this is a card in the Later list, to report this issue.

## D3 — Whether the HelmCharts provider fix gains a cache that survives between deploys, since the agreed fix alone still downloads on every deploy

**Context.** A HelmCharts deploy failed in the prometheus release when Terraform's init could not fetch a public provider's checksum file from GitHub — transient, but it took the whole deploy down. On 14 September you agreed a fix list: pin the four public providers, commit lock files, retry init on transient failure, and verify what a stale committed homelab-provider lock entry does under the upgrade flag; routing public providers through the homelab provider mirror was deferred. The same day you said HelmCharts has no change block, so changing it is fine. Every HelmCharts release deploys in its own fresh iac container, and the deploy tool's plugin cache sits inside that container.

**The ask.** A transient checksum fetch stops failing deploys.

**Background.** The card's premise — that a committed lock file means zero downloads — does not hold here. Measured today with Terraform 1.16: with an empty cache, init with a lock file, with or without the upgrade flag, downloads the checksum file and its signature from GitHub exactly as without one; a warm cache with no lock still downloads; only a warm cache plus a lock downloads nothing. Since the cache is empty at every deploy, of the agreed items only the retry would have saved the failed deploys; pins and lock files add version stability, not reliability. The card's measurement was most likely taken where a cache persisted — this dev pod's toolchain container keeps one, and the session tripped on the same thing. Exposure is not measurable: Jenkins keeps about a day and a half of HelmCharts builds, all green; about 46 releases carry Terraform, and each deploy of one downloads the four public providers.

**Why yours.** It changes the list you agreed and adds a change to srviac that you apply yourself.

**Recommendation.** Keep every agreed item and add a provider cache that survives between iac containers — a directory on srviac mounted into the container, which the deploy tool already uses when pointed at it. With pins and a lock, a warm cache means no download; the first deploy after a version bump downloads once, with the retry as backstop. Ansible's own Terraform runs in the same container and gets the same benefit. Trade-off: a shared cache directory on srviac written by every iac run — Terraform does not promise the cache is safe for two runs at once; Jenkins serializes its runs on a single executor, so only a hand-run overlapping a job could race — and an Ansible change to srviac you apply with a playbook run.

**The other way.** Ship the agreed fix as filed and let the retry absorb transient failures; no srviac change, but every release still downloads on every deploy.

**If this is wrong.** One phase of extra work; a cache problem would fail deploys until the directory is cleared.

**Operator.** I don't want persistence on srviac. Plus, HelmCharts is EOL. I'm replacing it fully with Argo CD. So any change should probably be made part of the Argo CD project. Right now I feel like taking this out of the slice, and tagging it Project-ArgoCD would be best.

## Open facts — questions only you can answer

**F1.** Did anything happen to the version poller, the registry or the prd cluster between about 31 August and 11 September? The poller started no rebuild for twelve days, had a failed run on 11 September, and resumed on 12 September. The answer settles whether the gap has a known cause or goes to the Triage card for diagnosis.

**Operator.** Not that I know.

**F2.** Do you run iac by hand on srviac while a Jenkins IaC job may be running? The answer settles whether the shared provider cache can see two runs at once.

**Operator.** Generally not. But it can happen, in theory.

## Settled

- One lock file shared by every release, the way the provider declarations are already one shared file linked into each release, instead of the per-chart lock files on the agreed list — 46 identical copies; the planner confirms no release declares a provider of its own.
- Routing public providers through the homelab provider mirror stays deferred, as you ruled.
- The Argo CD PreSync hook and KubeCoder's deploy repo have the same unpinned, lock-less Terraform setup; they stay out of this slice and get a Triage card.
- Verifying the iac image fix needs one real run of the iac image job triggered the way the poller triggers it, which pushes a fresh iac image that every IaC job then pulls; the test phase asks before triggering it.
- Size: about five phases across three repos — Ansible (the iac image pipeline, plus srviac if the cache goes in), HelmCharts (pins, lock file, init retry) and DockerImages (the poller, if it goes in); four if the poller change and the srviac piece both drop out.
