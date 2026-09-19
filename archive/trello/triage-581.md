# iac-image: the poller's weekly rebuild can still be skipped and never retried

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Minor

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

From slice 013 (PA reviewer r2 + completion consult) — needs an operator ruling.

Jenkinsfile.iac-image infers "the version poller triggered this" from an empty changeset. A poller-triggered build that happens to absorb commits touching no image input therefore still skips, and per the poller's bookkeeping that weekly rebuild is never retried — rebuild-at does not advance, and after STALE_GRACE the poller reports the image orphaned.

Narrower than the r1 blocker PA fixed, same failure mode. Closing it needs a ruling because the "no escape hatch" ruling weighed manual forcing, not the poller — DockerImages solves this with a params-driven force path that 013 deliberately did not adopt.

Also unverified: verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and the test phase confirmed the pure-skip path is unobservable from inside the slice.

Slice: AnsibleSpecs/slices/completed/013_iac_pipeline_restructure/

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (3)

### Jeeves (@jeevesginbov) - 9/15/2026, 10:46:59 AM
Slice 021 cancelled at planning, 2026-09-15. This card's fix is now items 1 (iac image parameter, per the operator's ruling) and 2 (the poller retries a rebuild that collided with a running build) of AnsibleSpecs handovers/2026-09-15_poller_rebuild_straightforward_changes.md, tracked on Operator Actions. The pipeline check found this is the only deaf pipeline. Reporting of missed rebuilds: #1022 (Later).

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:44 AM
Filed at triage 2026-09-14 into slice 021 — AnsibleSpecs/slices/backlog/021_build_and_deploy_pipeline_reliability/ (Kanban [021]). The card text and the operator's widening ruling are quoted in slice.md.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:33:46 AM
Triaged 2026-08-16: Minor. The card asked for a ruling on adopting a params-driven force path; the operator's answer widens the card well past iac-image.

Operator ruling, verbatim: "The issue more general. All pipelines that conditionally build the image likely won't based on the version poller signal. I see two options. Either this is always two stage: detect whether the image needs to be rebuilt, and then schedule a separate pipeline. That second pipeline is then picked up by version poller. The alternative is that we send a signal to the pipeline it can test for, e.g. the trigger field. The first option is cleaner, but more verbose. All pipelines need to be checked."

So the ask is now: audit every pipeline that conditionally builds an image for the same deafness to the version-poller signal, and pick between the two shapes above. That is its own slice rather than a Jenkinsfile.iac-image fix, and it is worth planning before more pipelines copy the pattern.

Also carried forward from the card: verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and slice 013's test phase confirmed the pure-skip path is unobservable from inside that slice.

## 📊 Statistics

- **Comments**: 3

## 🔗 Links
- **Card URL**: https://trello.com/c/f1ZHXKa0/581-iac-image-the-pollers-weekly-rebuild-can-still-be-skipped-and-never-retried
- **Short URL**: https://trello.com/c/f1ZHXKa0

---
*Last Activity: 9/15/2026, 10:46:59 AM*
*Card ID: 6a7e162a46bbc3452585ba8e*
