# 023 — Backup freshness: each upload declares how long it stays valid, backup-server exposes it, Alertmanager raises an overdue backup

**Major.** The OpenBao backup ran with zero successes on any node from 2026-06-05 to 2026-08-13 and nothing noticed. Nothing anywhere checks that a backup is still arriving.

## What is being requested and why

Split out of slice 019 during its planning session (2026-09-14, refinement decision D4). Slice 019 keeps #573's items 1 and 2 (the staged secret_id check, the wrapper's per-leg errors). This slice carries item 3, reshaped by the operator's rulings into a backup-server feature delivered through Alertmanager.

**Waits for slice 018** (Kanban #209), which gives production Alertmanager its first delivery (Telegram). The operator confirmed 018 is the Alertmanager rollout this slice builds on.

**Related:** slice 019 also edits the OpenBao backup wrapper (`openbao-backup.sh.j2`, per-leg error reporting). This slice's change to it (sending the validity) lands on whatever 019 left.

## Requirements

1. **(Major, #573)** "3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere."

2. **(operator, 2026-09-14, slice 019 refinement D1)** "The better solution would be to track this in the backup service. I feel like the end to end solution would be to add metadata to the upload indicating for how long it's valid (two days in our example). The backup service can then report that it didn't receive (and successfully upload) a backup within that period. For bonus points the check would actually read some JSON file from the backup server containing this metadata. I'm envisioning a .metadata.json file next to the backup, for now containing only this data field."

3. **(operator, 2026-09-14, slice 019 refinement D3)** "I would assume we just integrate it with Alertmanager. I'm also in the process of rolling that out."

## Operator rulings and Q&A

All from slice 019's planning session, 2026-09-14. The full record is `slices/019_role_followups_kubelite_tls_openbao_backup/refinement.md` (D1, D3, D4, F1).

- **D1 — where the freshness signal lives.** The session recommended a node-side marker read by a daily drift-job stage. The operator ruled for tracking in the backup service instead (requirement 2).
- **D3 — how the report reaches the operator.** The session recommended a status route polled by the daily drift job, with the service sending Telegram itself as the alternative. The operator ruled for Alertmanager instead (requirement 3).
- **D4 — the split.** The operator said "Agreed" to splitting backup freshness into its own slice, sequenced after the Alertmanager-delivery slice (018), with slice 019 keeping the Ansible-only items.
- **F1.** Asked whether slice 018 is the Alertmanager rollout meant, or whether anything changing alert labels or routing happens outside it. The operator answered: "I think slice 018 yes, but we don't now have to already plan the slice." This slice was therefore filed to the backlog, not planned in that session.
- **Slice sizing** (operator, 2026-09-14): "There's quite some overhead in slices. Seven phases tends to be the sweet spot."
- **Settled by the 019 session, shown to the operator in the refinement doc, not objected to.** These are proposals, not operator wording; re-ground them at planning.
  - Validity travels with each upload as a duration the uploader sends; OpenBao sends two days. backup-server writes it to `<backup name>.metadata.json` next to the backup, holding `{"valid_for": "48h"}`, and only after the backup has landed in cloud storage. A stream is overdue once its newest backup's landing time plus that validity has passed. With two days, one missed night stays green and two in a row alert.
  - Freshness is tracked per scope and file name, so a scope with several nightly files (the Postgres dumps, one per database) reports each one that stops arriving. A stream whose newest backup carries no metadata is not tracked.
  - The Postgres dumps are not opted in by this slice; they join later by sending the same field, and a Triage card carries that.
  - Retention today counts every file in a scope as a backup. Pruning changes to count backups only and to delete each backup's metadata file with it.
  - The OpenBao followers keep exiting successfully; no node's unit status is the signal.
  - backup-server publishes, per stream, when the newest backup landed and until when it is valid, on a metrics endpoint Prometheus scrapes through the Service annotations other in-house services use. The values come from the metadata files read back from cloud storage, refreshed on a slow timer and after each upload rather than on every scrape. The endpoint takes no token and carries names and times only.
  - The alert rules sit with the other rules in the production Prometheus release. A stream past its valid-until time fires a critical alert, delivered loud. A second critical alert fires when Prometheus cannot scrape backup-server or backup-server cannot read cloud storage, because a dead service would otherwise silence the overdue alert along with itself.
  - backup-server does not push alerts to Alertmanager itself; Prometheus evaluating the rule is the path.
  - Rollout order: the new backup-server runs on production before Prometheus starts scraping it.
  - Doctrine: `decisions.md`'s OpenBao backup section records the freshness contract in place of "fire-and-forget", and its stale mention of the retired `tokens.yaml` is corrected in passing.

## Source material

### #573 — OpenBao backup: harden the credential handoff and failure visibility — https://trello.com/c/UjQumz5e

Quoted in full, with the card's comment, in `slices/019_role_followups_kubelite_tls_openbao_backup/slice.md`. The part this slice carries:

> 3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere.
>
> Severity rests on the history, not the current state: zero successful backups on any node from 2026-06-05 to 2026-08-13, silently.

### Grounding from slice 019's planning session (2026-09-14)

Verified then by read-only sub-agents and a live read-only `kubectl`. Treat it as unverified input at planning, because code moves.

- **The wrapper.** Followers exit 0 at `openbao-backup.sh.j2:28-33` without logging in. The timer defaults to `*-*-* 02:00:00` with `RandomizedDelaySec` 1h. The unit is a plain oneshot with no `OnFailure=`. Doctrine (`decisions.md:100`, :103, :109): leader-only execution, all three nodes skip during an election, the timer is "fire-and-forget", and a missed cycle falls back to the previous dump. No freshness check exists in Ansible, the Jenkinsfiles, `check-ansible-drift.sh` or HelmCharts' Prometheus rules.
- **backup-server** (`/work/DockerImages/backup-server/`, Go).
  - **Upload.** The client sends a raw body plus `?filename=`, and the scope comes from the bearer token. The object is named `<UTC timestamp>_<filename>.age` (`src/internal/pipeline/upload.go:52-54`). The response is synchronous through age encryption and the rclone upload: 201 once it has landed, 500 "upload failed" otherwise (`src/internal/handler/handler.go:57-127`). Prune runs async afterwards (:119).
  - **Backend.** It has only `Upload`, `Delete` and `List` (`src/internal/pipeline/backend.go:17-21`), all rclone subprocesses. `List` returns names only (:92-95); there is no read method.
  - **Prune.** It sorts every name in the scope dir and deletes all but the last `retention`, with no suffix filter (`src/internal/pipeline/prune.go:14-41`).
  - **State and routes.** No plaintext touches disk. The only state is `credentials.json` on a CephFS PVC. The routes are `POST /upload`, `GET /health/{healthz,readyz}` and `/credentials` CRUD behind `MANAGEMENT_TOKEN` (`handler.go:44-55`, :171-185). There is no metrics or notification code; `plan.md:256-258` put `/metrics` out of scope. The contract is in `api.md`. Go tests run with `go test ./...` from `src/`.
- **Uploaders.** OpenBao posts `openbao-backup.tgz` daily (scope `openbao`, retention 14, `/work/Ansible/terraform/prd/openbao.tf:6-9`). postgres-pas runs a per-DB `pg_dump` CronJob at `0 2 * * *` (`/work/HelmCharts/charts/postgres-pas/values.yaml:102-103`; scope `postgres-pas`, retention 90), prd only. Scopes are provisioned by `homelab_backup_credential` (`/work/HomelabTerraformProvider/internal/backupcredential/resource.go:44-84`).
- **Deploy.** `/work/DockerImages/Jenkinsfile:99-102` builds `registry:5000/backup-server` tagged with the build number plus `:latest`. The storage chart defaults to `:latest` (`/work/HelmCharts/charts/storage/values.yaml:35`), and the digest is pinned at deploy (`resolve_helm_args.py:129-157`). Deploys go through the Jenkins `IaC/HelmCharts` job, not Argo CD, effectively prd only. `backup-server.home` is internal-only.
- **Prometheus and Alertmanager (prd).**
  - **Deployment.** The upstream `prometheus-community/prometheus` chart (`/work/HelmCharts/configs/prd/prometheus/prd/release.yaml`, namespace `prometheus-prd`). There is no Prometheus Operator (no `monitoring.coreos.com` CRDs).
  - **Scraping and rules.** Scrape targets are static `extraScrapeConfigs` plus the annotation-driven `kubernetes-pods` job; `charts/electronics-inventory/templates/app-service.yaml:5-7` is the pattern. Alert rules are central, in `serverFiles.alerting_rules.yml` (`configs/prd/prometheus/prd/values.yaml:58-118`).
  - **Alertmanager.** It runs with the stock route to an unconfigured receiver, so nothing is delivered today. Slice 018 P2 adds Telegram (critical loud, warning silent, one receiver per severity) in the same values file.
  - **Go precedent.** No Go service in DockerImages uses `prometheus/client_golang` yet.
- **Doctrine.** `decisions.md:103` still names the retired `tokens.yaml`, and `decisions.md:146` says alerting is deferred and only the Proxmox nodes are scraped.

## Subsumes

Triage #573 item 3, split from slice 019 (Kanban #210) at its planning session.
