# Slice 022 — refinement

## D1 — Archive expiry: the mirror job itself keeps the 30 newest archive folders per bucket and prunes the rest

**Context.** Every production-stage bucket on the production object store gets a daily, encrypted, incremental rclone sync to the existing Google Drive remote — the design you accepted on the 14th ("A sync sounds perfect"). Objects a sync would overwrite or delete are not lost: each run moves them into a folder named for that run, so only a run that changed something leaves a folder behind. backup-server, which holds the Postgres dumps, keeps the N newest uploads per scope and prunes the rest after each upload.

**The ask.** At triage the expiry question ("how many days?") got "Use the same mechanism we use to delete old backups?" — a count rather than an age, with the count unset. Something has to decide how long a replaced or deleted object stays recoverable from Drive.

**Background.** backup-server's pruner runs only inside its own upload handler, over its own flat, timestamp-prefixed file names in one folder per scope; there is no way to point it at another folder, and a folder-per-run archive would be skipped, or pruned in the wrong order, by it. Space is not the constraint: 1.7 GB live against about 80 GB free, and the archive holds only replaced or deleted objects. The buckets are attachment and document stores that should be mostly add-only — not measured.

**Why yours.** Your triage answer was itself a question, the count is a preference only you can set, and you may have meant literal reuse of backup-server rather than its rule.

**Recommendation.** The same rule, written into the mirror script: after each successful sync, per bucket, keep the 30 newest archive folders and delete the rest. Because only a run that changed something leaves a folder, a quiet bucket keeps history far longer than 30 days and a busy one about a month. The trade-off: the keep-N rule then lives in two places — backup-server and the mirror script — and history is counted in changes, not days.

**The other way.** Give backup-server a prune entry point the mirror job calls, with the archive laid out in backup-server's flat timestamped naming — one pruner in the estate, at the cost of a Go change, a new API and credential for the job, and the per-run folders flattened away.

**If this is wrong.** An object deleted by mistake is gone sooner, or kept longer, than you wanted; changing the count later is a one-value edit.

**Operator.** Agreed

## D2 — Freshness alert: a Prometheus rule on the mirror job's last successful run ships in this slice; the Postgres dumps are left to the backup-freshness slice

**Context.** No backup freshness check exists anywhere today; the OpenBao backup failed silently for two months earlier this year, which is why the accepted design carries an alert. kube-state-metrics on production already exposes each CronJob's last successful run, and alert rules live centrally in the production Prometheus release; Alertmanager delivers nothing yet — the Telegram-delivery slice, already planned, adds that (critical alerts loud, warnings silent). A backlog slice, not yet planned, designs freshness inside backup-server: each upload carries a validity — two days for OpenBao, so one missed night stays green and two in a row alert — backup-server publishes per-stream metrics, and the Postgres dumps join later. In another slice's refinement you ruled freshness belongs "in the backup service" rather than in a node-side check.

**The ask.** The accepted design says a rule on kube-state-metrics fires when no successful mirror job exists in 26 hours, the same rule covers the Postgres dumps, and delivery rides the Telegram slice.

**Background.** The mirror uploads with rclone directly and never passes through backup-server, so the backup-server freshness mechanism cannot see it as designed. The data the rule needs is already scraped.

**Why yours.** You ruled for freshness "in the backup service" once; this job sits outside it, and you could want one mechanism estate-wide rather than a second.

**Recommendation.** A rule covering the mirror job only, in the production Prometheus release beside the others, firing critical once the mirror has gone two days without a successful run — the tolerance the backup-freshness slice set, rather than the proposal's 26 hours, so a single Drive hiccup does not page loudly. The Postgres dumps are left out of this rule so they are not watched twice once that slice lands. Delivery arrives with the Telegram slice either way. The trade-off: two freshness mechanisms in the estate — kube-state-metrics for this job, backup-server metadata for everything uploaded through it.

**The other way.** The mirror posts a small heartbeat through backup-server carrying the validity that slice defines, and that slice's alert covers the mirror — one mechanism, but this slice ships no alert of its own and the mirror stays unwatched until the backup-freshness slice is planned and delivered, after the Telegram one.

**If this is wrong.** A second mechanism to maintain — or, the other way, a mirror that can fail silently for longer.

**Operator.** Agreed

## Open facts — questions only you can answer

None — nothing in this slice turns on something only you know.

## Settled

- The decision record calls the shared production object-store credential current; it is already retired and every bucket has its own app user, so the record's section is rewritten in the present tense with the backup reader as its one recorded exception, instead of appending an exception to stale text.
- The record's S3 endpoint convention — HTTPS on the Ceph VIP — was never built: the object gateway has no TLS listener on the VIP and every app and the provider use plain HTTP to it; the mirror uses the endpoint the apps use, and the record's convention sentence is corrected to what is real.
- The dev Ceph the accepted drill restores into runs on a VM that is currently off to save memory, so the drill needs you to start it for its duration.
- The shared Terraform module does not know a release's stage, so the read grant is decided from the release's stage suffix — production only, nothing to set per app, so no new production bucket can be forgotten — and the mirror treats a production bucket it cannot read as a failure, never a skip.
- Encryption key: you generate the rclone encryption password and salt before the run and store them in OpenBao (the job reads them through the storage chart's existing External Secrets pattern) and in Roboform next to the age key; the record's failure-domain list gains the key in the Roboform domain — a keystroke before the run starts, as the Telegram slice's OpenBao secrets were.
- Push order, run by the run's test phase: the provider goes first and must be published before any HelmCharts push uses it (nothing pins the provider; every deploy floats to the newest); HelmCharts then goes out in two pushes — the storage release (reader, secret, job) first, then the shared-module grant, which redeploys every production release in one build as any shared-module change does today; the order exists because the object gateway is documented to reject a policy naming a user that does not exist yet — not verified live.
- A bucket that disappears from the object store keeps its mirror copy untouched; the job never deletes a whole bucket's mirror.
- Inventory: the record's Backup section gains a short coverage list — each off-cluster mechanism, what it covers, how much history, which key — plus one line naming what is knowingly not covered under your rulings (block volumes, CephFS, non-production buckets), replacing "Offsite for production is a later item"; no survey of volumes.
- Restore drill: restore the iot attachments bucket from Drive into a scratch bucket on dev Ceph and compare it against the live bucket with rclone's check, written as a runbook beside the OpenBao one in the Ansible runbooks; you run it after the first successful mirror, and the acceptance item closes only on its output, never on a green gate.
- Size: about six phases across four repos — the Terraform provider (reader user resource, bucket-policy grant), HelmCharts (storage chart: reader, encryption secret, mirror job with its pruning; shared-module grant; Prometheus rule), the spec repo's decision record, and the Ansible runbooks.
