# Slice 019 — refinement

## D1 — Where the "is the OpenBao backup fresh?" signal lives, and after how many missed nights it goes red

**Context.** The OpenBao nightly backup ran with a dead credential from 2026-06-05 to 2026-08-13 — zero successful backups on any of the three nodes — and nothing noticed. The credential has been re-minted and the orphan destroyed; you trimmed the card to what is still outstanding. Today all three nodes run the same script from a nightly timer at 02:00 (plus up to an hour's random delay); only the Raft leader backs up and the two followers exit successfully within milliseconds. That is doctrine, as is "the next cycle picks it up" after an election. A failed leader run leaves a failed unit on that node that nobody looks at, and nothing anywhere checks freshness — not a Jenkins job, not Prometheus (it does not scrape these nodes, and alerting is deferred by doctrine), not the drift script. The estate's red is a scheduled Jenkins build, which reaches you as a Telegram message; the daily drift job runs late morning.

**The ask.** The card's third item, in your trimmed version: "Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere." Something has to notice a backup that has stopped landing, and say so.

**Background.** The backup-server — the in-cluster service the script uploads to, which encrypts and ships to cloud storage — answers an upload with success only once the object has finished streaming to cloud storage, so a confirmed upload is a backup that landed. It has no route that lists uploads or their times, so checking the storage end directly means changing its image and its chart. And the run that retries a missed night is the timer itself, the next night — your rule on the drift job (2026-09-03) is that a check going red for a state another scheduled run will fix by itself is noise, and the threshold belongs past that run's slot.

**Why yours.** Which signal you trust (the nodes' own record or the storage end), whether to spend two more repos on it, and how early you want the red.

**Recommendation.** The script records, on its node, the time of the last upload the backup-server confirmed. A new stage in the daily drift job reads that record from all three nodes and goes red when the newest one predates the last two nightly slots: one missed night (an election, a short Kubernetes blip) stays green because the next night is its retry; two in a row go red, naming the stage. Followers keep exiting successfully — the fleet-wide signal is the drift stage, not any node's unit status. Trade-off: a dead backup is noticed on the second morning rather than the first (about two days, against three months), and the check trusts the nodes' own record of a confirmed upload rather than looking at cloud storage itself.

**The other way.** Have the backup-server report each scope's last accepted upload and check that instead — it sees the storage end directly and does not depend on reaching the OpenBao nodes, but costs a backup-server image change and a chart change: two more repos and one or two more phases, past your seven-phase mark.

**If this is wrong.** A stale backup is noticed a day later than you wanted — or goes red after one missed night that you consider noise. No data is lost either way.

**Operator.** The better solution would be to track this in the backup service. I feel like the end to end solution would be to add metadata to the upload indicating for how long it's valid (two days in our example). The backup service can then report that it didn't receive (and successfully upload) a backup within that period. For bonus points the check would actually read some JSON file from the backup server containing this metadata. I'm envisioning a .metadata.json file next to the backup, for now containing only this data field.

## D2 — Whether the kubelite restart's wait becomes a real readiness wait, or its comment and doctrine are corrected to say what it actually checks

**Context.** The microk8s role restarts kubelite — the Kubernetes control-plane process — one node at a time. After each restart it waits until the API server's liveness check answers on that node (on a worker, until the kubelet's own health check answers) before the next node may go. The handler's comment says the next node goes down "only once this one is serving", and doctrine, in two passages, credits "the readiness wait" with covering each gap while the cluster's virtual IP serves from the other members. This is not a by-hand path only: the weekly Friday certs job triggers the restart whenever it re-issues a control-plane node's API-name certificate — roughly every 33 days, the three prd control-plane nodes one after another. The finding came out of the internal-TLS slice's code review as a suggestion with no consequence observed; you agreed at triage to carry it.

**The ask.** The wait should check what its comment and doctrine say it checks — or the comment and doctrine should say what the wait checks.

**Background.** Liveness does not run the datastore-readiness and cache-sync checks that readiness does (probed live against prd). A worker's health check says its health server is up, not that the node has re-registered — the same gap that, in the scheduled OS-update reboot flow on 2026-07-27, let a worker be uncordoned while not ready; that flow was fixed then with a wait on the node's Ready state. No incident from this restart's wait has ever been recorded. With three control-plane members, the virtual IP still has a healthy peer if one is alive-but-not-ready while the next restarts.

**Why yours.** It changes behaviour on a path that runs unattended and could turn a passing Friday job red, against accepting a weaker guarantee than doctrine states.

**Recommendation.** Wait for readiness — the API server's readiness check on control-plane nodes, the node's Ready state on workers — within the existing timeout setting. Trade-off: a node that comes back alive but not ready now stops the roll and turns the run red, a Friday certs build included, where today the roll moves on to the next node. Not verified: how the worker branch reads its node's Ready state from inside the single throttled restart step; if that proves impractical, workers keep the health check and the comment says so honestly.

**The other way.** Keep the behaviour and correct the handler comment and the two doctrine passages to say the wait checks that the API server answers again — no new failure mode and no new red, but the one-node-at-a-time guarantee then rests on the virtual IP alone.

**If this is wrong.** With readiness, an occasional red certs build on a node that is slow to become ready — a hand look, no outage. With liveness, in a bad case two control-plane API servers not serving at once, the API served through the virtual IP by one member.

**Operator.** Agree

## D3 — How the backup service's "no backup within its validity" report reaches you

**Context.** On D1 you did not take the node-side record and drift stage; your ruling moves the freshness question to the backup service, with the validity travelling as metadata on each upload and, for bonus points, the check reading a JSON file next to the backup: "The backup service can then report that it didn't receive (and successfully upload) a backup within that period." That leaves one thing open — how "report" reaches you. Today the backup-server has three kinds of route: upload, credential management behind one management token, and health checks. It has no notification code of any kind (no Telegram, email or metrics), no scheduler, and no state beyond its credential store, and it is reachable only on its internal home hostname. Prometheus does not scrape it, and doctrine defers alerting.

**The ask.** A backup stream whose newest backup has outlived its validity has to turn into a red you see, and the backup-server is where that is known.

**Background.** Every scheduled red in the estate reaches you as a Telegram message from the Jenkins bot when a scheduled build fails. The daily drift job already fetches a file from another internal service — the certificate authority's root bundle — and goes red on a mismatch, so a stage that asks an internal service a question and reds on the answer is an existing pattern. The backup-server answers an upload only after the backup has finished landing in cloud storage, so a metadata file written after that is proof the backup landed. Two uploaders exist today: OpenBao's nightly backup and the nightly Postgres dumps, one file per database.

**Why yours.** It decides where the red appears — through the Jenkins-to-Telegram channel every other scheduled check uses, or straight from the service — and whether the service grows a scheduler and a Telegram credential.

**Recommendation.** The backup-server gains a read-only status route listing each backup stream — scope and file name — with when its newest backup landed, how long it is valid, and whether it is overdue, worked out on each request by reading the metadata files back from cloud storage (your bonus: the check reads the JSON next to the backup, not something the service remembers, so it survives restarts and sees what storage actually holds). A new stage in the daily drift job asks it and goes red naming each overdue stream — and goes red if the service does not answer. Trade-off: the red arrives at the drift job's late-morning slot, up to a day after the validity actually lapsed, and the backup-server itself raises nothing — it only answers when asked.

**The other way.** The backup-server checks on its own timer and sends a Telegram message itself when a stream goes overdue — hours earlier and no dependence on Jenkins, but it needs a scheduler inside the service, a Telegram bot credential in its chart, and a second alert channel beside the Jenkins one to keep working.

**If this is wrong.** An overdue backup is reported up to a day later than a push from the service would manage — or there is an extra alert path to maintain. Nothing is lost either way.

**Operator.** (in chat) "I would assume we just integrate it with Alertmanager. I'm also in the process of rolling that out." — neither the status route polled by the drift job nor a message sent by the service itself.

## D4 — Whether the backup-freshness work splits into its own slice, sequenced after the Alertmanager-delivery slice

**Context.** Where the plan now stands: on D1 you moved freshness into the backup service, with validity travelling as metadata on each upload; on D3 you sent its report through Alertmanager rather than the daily drift job. Verified 2026-09-14: production runs the plain Prometheus chart, scraping services by an annotation on their Service as three in-house services already are, with alert rules in one central rules file in the production Prometheus release; Alertmanager runs there but has no receiver, so alerts fire and go nowhere. The Alertmanager-delivery slice now in plan review gives it its first — Telegram, critical alerts delivered loud, warnings silent — and edits that same release file. backup-server has no metrics endpoint today; it would be the estate's first Go service to expose one.

**The ask.** The slice as filed is one card and its close-out; after D1 and D3 its freshness item has grown into a cross-repo feature.

**Background.** The freshness work is now: in backup-server, the validity metadata on upload, the pruning change, reading metadata back from storage and a metrics endpoint; in HelmCharts, the scrape annotations on backup-server's Service and the alert rules in the production Prometheus release; in Ansible, the OpenBao backup script sending its validity; in the specs repo, the doctrine — about four to five phases across four repos, and its alert is only delivered once the Alertmanager-delivery slice lands. The rest of the slice — the staged-credential check, the backup script's per-call errors, the two kubelite items and the expired-certificate runbook — is about four to five phases, all in the Ansible repo, depending on nothing. Together: about eight to nine phases across four repos.

**Why yours.** You set the size rule yourself — slices carry overhead and seven phases is the sweet spot — so trading a second slice's overhead against size and an ordering dependency is your call.

**Recommendation.** Split. This slice keeps the credential check, the per-call errors, the two kubelite items and the runbook — Ansible only, runnable whenever. A new slice carries backup freshness end to end (backup-server, the scrape and alert rules, the script's validity field, doctrine) and runs after the Alertmanager-delivery slice, so its alert is built on top of that slice's edits to the same file and against an Alertmanager that actually delivers. Trade-off: one more slice's fixed overhead — a planning session, a test phase, a doc phase, a close-out.

**The other way.** One slice of eight to nine phases, run after the Alertmanager-delivery slice — one overhead instead of two, but past the seven-phase mark, and the unrelated role fixes and runbook wait behind alert delivery.

**If this is wrong.** One slice's overhead spent that did not need spending — or the role fixes held back behind the Alertmanager-delivery slice for no reason of their own.

**Operator.** Agreed

## Open facts — questions only you can answer

**F1.** Is the Alertmanager-delivery slice now in plan review (018) the Alertmanager rollout you mean, or is part of it happening outside that slice — in particular anything that changes how alerts are labelled or routed? The answer settles which slice the backup-freshness work waits for, and which labels its alerts carry.

**Operator.** I think slice 018 yes, but we don't now have to already plan the slice.

## Settled

- The expired-certificate runbook was left unwritten in the internal-TLS slice because nobody could say whether a plain renewal run recovers a certificate that has already lapsed; that is now answered — verified 2026-09-14 by running the step tool hosts get (installed unpinned from Smallstep) against a throwaway, already-expired certificate: it reads as needing renewal at every threshold, and the role fetches a fresh certificate with a one-off provisioner token rather than renewing the old one, so nothing in the path needs the lapsed certificate and nothing in it calls OpenBao — a plain renewal run recovers a lapsed certificate, and the runbook says so (not reproduced against a real host).
- The one exception the runbook spells out: an expired OpenBao listener certificate stops the usual path, because every Jenkins infrastructure run fetches its secrets from OpenBao when it starts, so the weekly certs job cannot run — the runbook covers renewing that certificate by hand in that state, and the OpenBao runbook's "listener cert expired" entry points to it (not verified: exactly how a hand run obtains its credentials while OpenBao is unreachable — the runbook phase works it out from the existing cold-boot runbook).
- Before a staged backup credential is installed on the OpenBao nodes, the run checks it against the live OpenBao role, and a dead one fails the run with a message naming the rotation flag to use — no silent skip and no automatic re-mint, rotating stays your opt-in; only a hand run from a persistent checkout can carry a leftover staged file, since Jenkins clones fresh each run.
- Every call the backup script makes names itself on failure, with the HTTP status and OpenBao's error text — never a token or a response body.
- In a check-mode dry run the kubelite restart announces itself as a change on each node it would restart, the same way the role already announces a would-be cluster join; check mode still never restarts anything.
- Four older restart steps share the same dry-run blind spot — microk8s's full restart and its CoreDNS rollout restart, and Ceph's OSD and MDS daemon restarts — and get the same announcement in the same phase, at no extra phase.
- Doctrine's OpenBao backup section records the freshness check (today it calls the timer fire-and-forget); if D2 goes the other way, its two readiness passages are corrected in the same phase.
- The daily drift job is also being reshaped by a slice already in flight (every stage runs whatever an earlier one did); the freshness stage is built on whichever shape is on main when this slice runs.
- Size: about six to seven phases, all in the Ansible repo plus one doctrine touch in the specs repo; D1's other way would add two repos (the backup-server image and its chart) and one or two phases, past the seven-phase sweet spot.

## Settled — after the backup-service ruling

These replace the first round's items on doctrine, on the drift job and on size, which rested on the node-side recommendation D1 did not take.

- Validity travels with each upload as a duration the uploader sends — OpenBao's nightly backup sends two days — and the backup-server writes it into a metadata file next to the backup, only after the backup has landed in cloud storage; the file is named `<backup name>.metadata.json` and for now holds one field, the shape you envisioned: `{"valid_for": "48h"}`. A stream is overdue once its newest backup's landing time plus that validity has passed — with two days, one missed night stays green and two in a row go red.
- Freshness is tracked per scope and file name, so a scope with several nightly files reports each one that stops arriving; a stream whose newest backup carries no metadata is not tracked.
- The Postgres dumps are not opted in by this slice; they join later by sending the same field, and a Triage card carries that so it is not lost.
- Retention today treats every file in a scope as a backup, so metadata files would eat into "keep the N newest"; pruning changes to count backups only and to delete each backup's metadata file with it.
- The status route answers without a token, like the health checks: it returns scope names, file names and times — no secrets — on the internal hostname only.
- The OpenBao followers keep exiting successfully; no node's unit status is the signal.
- If D3 goes as recommended, rollout order matters: the new backup-server must be on prd — your run of the HelmCharts job once the image has built — before the drift stage reaches main, or the daily drift job goes red on a route that does not exist yet; the plan orders it and names that deploy as your step.
- Doctrine: the OpenBao backup section records the freshness contract in place of "fire-and-forget", and its stale mention of the retired tokens file is corrected in passing.
- The daily drift job is also being reshaped by another planned slice (every stage runs whatever an earlier one did); the new stage is built on whichever shape is on main when this slice runs.
- Size: about seven to eight phases across the Ansible repo, the DockerImages repo (the backup-server image) and a doctrine touch in the specs repo. No HelmCharts change — the first round counted a chart change against this path, but the storage chart already follows the newest backup-server image and a deploy run picks it up. It stays one slice; if the plan comes out larger, a split comes back to you.

## Settled — after the Alertmanager ruling

These replace four items of the section above — the status route, the rollout order, the drift job's reshaping and the size — which rested on the drift stage D3's ruling removed; the rest of that section (validity metadata and its shape, tracking per scope and file name, Postgres not opted in with its Triage card, pruning counting backups only, followers exiting successfully, doctrine) still stands.

- backup-server publishes, for each backup stream (scope and file name), when its newest backup landed and until when it is valid, on a metrics endpoint that Prometheus scrapes through the same Service annotations the other in-house services use; the values come from the metadata files read back from cloud storage — your bonus — refreshed on a slow timer and after each upload rather than on every scrape, so a scrape every minute does not read cloud storage every minute; the endpoint needs no token and carries names and times only.
- The alert rules sit with the other rules in the production Prometheus release: a stream past its valid-until time fires a critical alert, delivered loud — a silent warning is the kind of signal that let the backup stay dead for three months — and a second critical alert fires when Prometheus cannot scrape backup-server or backup-server cannot read cloud storage, because a dead service would otherwise take the overdue alert down with it.
- backup-server does not push alerts to Alertmanager itself — that would need its own resend loop and could not report its own death; Prometheus evaluating the rule is the standard path.
- Until the Alertmanager-delivery slice lands, Alertmanager holds these alerts without sending them.
- Rollout order: the new backup-server must be running on production before Prometheus starts scraping it, or the scrape alert fires against the old image; the plan orders the two deploys.
- Size: see D4.
