# 021 — Build and deploy pipeline reliability

**Minor.** Pipelines that build an image conditionally can skip the rebuild the version poller asked for, and never retry it; and HelmCharts deploys fail outright on a transient Terraform provider checksum fetch.

## What is being requested and why

Two pipelines that fail or skip for reasons unrelated to the change they carry.

- **#581** came out of slice 013: `Jenkinsfile.iac-image` infers a poller-triggered build from an empty changeset, so a poller build that absorbs unrelated commits skips, and the poller reports the image orphaned. The operator's ruling widened it to every pipeline that conditionally builds an image.
- **#567**: HelmCharts deploys re-resolve and re-authenticate every provider on every release, so a transient `SHA256SUMS` fetch failure takes a whole deploy down (`IaC/HelmCharts` 5751, 5752).

## Requirements

Every item is quoted from its source; the tag is its triage category.

1. **(Minor, #581)** "A poller-triggered build that happens to absorb commits touching no image input therefore still skips, and per the poller's bookkeeping that weekly rebuild is never retried — rebuild-at does not advance, and after STALE_GRACE the poller reports the image orphaned."

2. **(Minor, #581 — the operator's ruling, verbatim)** "The issue more general. All pipelines that conditionally build the image likely won't based on the version poller signal. I see two options. Either this is always two stage: detect whether the image needs to be rebuilt, and then schedule a separate pipeline. That second pipeline is then picked up by version poller. The alternative is that we send a signal to the pipeline it can test for, e.g. the trigger field. The first option is cleaner, but more verbose. All pipelines need to be checked."

3. **(Minor, #567)** "Jenkins IaC/HelmCharts 5752 failed in "Deploying prometheus@prd": terraform init could not install cyrilgdn/postgresql v1.27.0 — "failed to retrieve authentication checksums" fetching SHA256SUMS." / "Transient, but it takes a whole deploy down."

## Operator rulings and Q&A

- #581, 2026-08-16: the ruling above. Triage's reading, recorded on the card: "audit every pipeline that conditionally builds an image for the same deafness to the version-poller signal, and pick between the two shapes above." The operator named a preference ("The first option is cleaner, but more verbose") without choosing — the shape is open for refinement.
- #581 also carries a test gap: "verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and slice 013's test phase confirmed the pure-skip path is unobservable from inside that slice."
- #567, 2026-09-14: "Agreed". The card's own list is session-written ("Agreed fix") and includes an open check — "verify what a stale committed homelab entry does under -upgrade" — and a deferral: "Deferred: routing public providers through tfmirror."
- **HelmCharts is open for changes** (operator, 2026-09-14, on the D43 flag): "Don't worry about making changes to HelmCharts. I have not started on moving away from HelmCharts. We'll review what's there when we get to it. There's no change block on it yet." D43 (`argo-cd/decisions.md`) reads "Meanwhile, prefer not to add new things to HelmCharts."
- **Slice sizing** (operator, 2026-09-14): "There's quite some overhead in slices. Seven phases tends to be the sweet spot." This slice was cut to that size at triage.
- Triage record: `handovers/triage_2026-09-14.md` and `handovers/triage_2026-08-16.md`, deleted at close-out — git history in this repo holds both; every ruling that bears on this slice is quoted here and on the cards.

## Source material

Quoted whole; headings inside a source are demoted two levels. Each card's diagnosis, cause and line references are the card's claims, unverified at triage.

### #581 — iac-image: the poller's weekly rebuild can still be skipped and never retried — https://trello.com/c/f1ZHXKa0

- URL: https://trello.com/c/f1ZHXKa0
- List: Inbox
- Labels: Ansible, Minor
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:33:46 AM

##### Description

From slice 013 (PA reviewer r2 + completion consult) — needs an operator ruling.

Jenkinsfile.iac-image infers "the version poller triggered this" from an empty changeset. A poller-triggered build that happens to absorb commits touching no image input therefore still skips, and per the poller's bookkeeping that weekly rebuild is never retried — rebuild-at does not advance, and after STALE_GRACE the poller reports the image orphaned.

Narrower than the r1 blocker PA fixed, same failure mode. Closing it needs a ruling because the "no escape hatch" ruling weighed manual forcing, not the poller — DockerImages solves this with a params-driven force path that 013 deliberately did not adopt.

Also unverified: verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and the test phase confirmed the pure-skip path is unobservable from inside the slice.

Slice: AnsibleSpecs/slices/completed/013_iac_pipeline_restructure/

##### Comments (in the order the tool returned them)

###### Jeeves — 8/17/2026, 7:33:46 AM

Triaged 2026-08-16: Minor. The card asked for a ruling on adopting a params-driven force path; the operator's answer widens the card well past iac-image.

Operator ruling, verbatim: "The issue more general. All pipelines that conditionally build the image likely won't based on the version poller signal. I see two options. Either this is always two stage: detect whether the image needs to be rebuilt, and then schedule a separate pipeline. That second pipeline is then picked up by version poller. The alternative is that we send a signal to the pipeline it can test for, e.g. the trigger field. The first option is cleaner, but more verbose. All pipelines need to be checked."

So the ask is now: audit every pipeline that conditionally builds an image for the same deafness to the version-poller signal, and pick between the two shapes above. That is its own slice rather than a Jenkinsfile.iac-image fix, and it is worth planning before more pipelines copy the pattern.

Also carried forward from the card: verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and slice 013's test phase confirmed the pure-skip path is unobservable from inside that slice.

### #567 — HelmCharts deploys fail on transient terraform provider checksum fetches — https://trello.com/c/IaGwCqOa

- URL: https://trello.com/c/IaGwCqOa
- List: Inbox
- Labels: HelmCharts
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/16/2026, 5:59:08 PM

##### Description

Jenkins IaC/HelmCharts 5752 failed in "Deploying prometheus@prd": terraform init could not install cyrilgdn/postgresql v1.27.0 — "failed to retrieve authentication checksums" fetching SHA256SUMS. 5751 failed the same way on keycloak; 5753 passed on retry. Transient, but it takes a whole deploy down.

Why it recurs: .terraform.lock.hcl is gitignored (.gitignore:11), _providers/providers.tf pins no versions, and _init passes -upgrade (tf.py:129) — so every release and phase re-resolves and re-authenticates every provider. The iac container is `docker run --rm` with no /work mount, so nothing persists between releases.

Measured, not assumed: a plugin cache does not help — warm cache with no lock still fetches checksums. A committed lock does: zero downloads, one registry version-list call. Pinning makes -upgrade a no-op for the public providers while homelab still floats to the newest tfmirror build.

Agreed fix:
- pin kubernetes, keycloak, postgresql, random in _providers/providers.tf
- un-ignore .terraform.lock.hcl, commit per-chart locks
- retry terraform init on transient failure
- verify what a stale committed homelab entry does under -upgrade

Deferred: routing public providers through tfmirror.

https://jenkins.webathome.org/job/IaC/job/HelmCharts/5752/

##### Comments (in the order the tool returned them)

_(no comments)_

## Subsumes

Triage #581, #567.
