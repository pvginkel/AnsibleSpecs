# Slice 023 — refinement

## D1 — Pull the Postgres dumps into this slice so they declare a validity too, instead of leaving them on their follow-up card

**Context.** The OpenBao backup failed silently on every node for over two months this summer and nothing noticed; nothing checks that any backup is still arriving. When this was split out of the OpenBao backup hardening slice you ruled that freshness is tracked in backup-server — each upload says how long it stays valid, backup-server keeps that in a metadata file next to the backup, and the overdue signal reaches you through Alertmanager. That session proposed leaving the Postgres dumps out and filed a card for them. The S3 mirror slice then ruled, with your agreement, that its freshness alert does not cover the Postgres dumps because this slice owns freshness for everything uploaded through backup-server.

**The ask.** Whether the nightly Postgres dumps on production start declaring a validity in this slice, so the same overdue alert watches them, rather than waiting for their card to be scheduled.

**Background.** The dump job runs nightly at 02:00 on production, one dump per database (nine today), all through backup-server into one scope that keeps the 90 newest files — about ten days per database. No alert watches it. Opting it in is one line in the job's upload script plus a production deploy of the postgres-pas release.

**Why yours.** A scope call: you have asked for fewer, fuller slices, but could equally keep this one to OpenBao.

**Recommendation.** Pull them in: the Postgres dumps send the same 52-hour validity as OpenBao, in this slice. The trade-off is one more small HelmCharts phase and a postgres-pas deploy on production, and a database you drop on purpose alerts critical until pruning removes its last dump — roughly ten days — unless you silence it; acceptable because dropping a production database is rare and deliberate.

**The other way.** Leave them on the card. Taken with the S3 mirror ruling, that leaves the Postgres dumps unwatched — the failure this slice exists to end — until someone schedules the card.

**If this is wrong.** One extra small phase; nothing breaks.

**Operator.** "Agree" (in chat, 2026-09-15 — to D1 and the settled list).

## Open facts — questions only you can answer

None.

## Settled

- The alert-delivery slice (Telegram receivers for production Alertmanager) has not run yet: it is planned and waiting, and production Alertmanager still delivers to nobody. This slice is planned now but runs only after that slice has merged — both edit the production Prometheus release's values, and until delivery exists an overdue alert reaches nobody.
- The doctrine names a retired tokens file for per-scope retention; retention actually lives in backup-server's own credentials store, set through the Terraform backup-credential resource, and an orphaned, unmounted backup-server-tokens ConfigMap still ships in the dev cluster's storage release. The doctrine's OpenBao backup section records the freshness contract in place of "fire-and-forget" and names the real retention mechanism, and the dead ConfigMap is removed in passing.
- backup-server runs on the dev cluster as well as production (only the Postgres dump job is production-only), so the new server reaches dev too; nothing to decide.
- The validity OpenBao sends (and Postgres, if D1) is 52 hours, not an even 48: the timer fires at 02:00 with up to an hour's random delay, so at exactly 48 hours one missed night could page before the next run lands; 52 hours keeps one missed night quiet and alerts on two in a row — the same threshold you agreed for the S3 mirror's alert.
- A stream stays watched while any of its kept backups declares a validity, overdue once its newest backup's landing time plus the newest declared validity has passed; this replaces the earlier proposal that a newest backup without metadata drops the stream from tracking, so an uploader that stops sending the field (a revert) stays watched instead of silently disappearing. A stream with no declaring backup at all is not watched.
- A stream whose backups have all been pruned stops being watched and its alert clears — only possible in a multi-stream scope (the Postgres dumps), days after the alert began.
- The dead-watcher alert (Prometheus cannot scrape backup-server, or backup-server cannot read cloud storage) waits out a grace period, so a redeploy or a cloud-storage hiccup that clears by itself never pages; it fires once the watching has really been blind for hours. Both alerts are critical, delivered loud.
- The metrics are served only inside the cluster, not through backup-server's ingress hostname, and carry scope, file names and times only — no token.
- The alert rules go live on production only after the new backup-server is serving metrics there, so the dead-watcher alert does not fire during rollout.
- The finding that the OpenBao backup wrapper passes its secrets on curl's command line (the minor card you put in Later) is not pulled in, though this slice edits the same upload call.
- Size: about seven phases across four repos — DockerImages (backup-server accepts the validity, writes the metadata, prunes backups only, reads metadata back and publishes freshness metrics), HelmCharts (the storage chart exposes the metrics to Prometheus, the alert rules in the production Prometheus release, the Postgres dump job's validity if D1 is agreed), Ansible (the OpenBao backup wrapper sends its validity), AnsibleSpecs (doctrine).
