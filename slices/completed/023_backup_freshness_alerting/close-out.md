# Close-out — slice 023 backup_freshness_alerting

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-18 22:51 → 2026-09-19 00:46 · 7 phases · 0 bail-outs · 1 test round · doc phase
done · $60.06 (planner 22 %, research 6 %, rework 6 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

A dead backup now raises an alert. backup-server (DockerImages) takes an optional `valid_for` on
upload and writes `<object>.metadata.json` beside the landed backup. Pruning counts backups only.
It reads the metadata back from Drive at start, hourly and after each upload, and publishes each
stream's last-backup and valid-until times on its own in-cluster listener, `:8081/metrics`.
The storage chart annotates the Service for scraping. Production Prometheus gains the
`backup-freshness` group: `BackupOverdue` and `BackupWatcherBlind`, both critical. The Postgres
dumps and the OpenBao wrapper declare `52h`. Ansible `docs/runbooks/backup-freshness.md` and
`decisions.md` carry the triage and the contract. All of it is live on prd except the OpenBao
wrapper, which waits on the operator's playbook run (A2).

## Outstanding actions

Focus: A2 first. Until the operator runs the `openbao` playbook, the OpenBao backup is still unwatched, which is R1's silent failure. A1 needs no action: the test phase found no live object to delete.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A2 — Run the openbao playbook so the OpenBao backup declares its 52 h validity (check-mode first) · minor

P6 (Ansible d70be14) adds `&valid_for=52h` to `/usr/local/sbin/openbao-backup`, but the wrapper on srvvault1-3 is still the old one: read live 2026-09-19, 0 `valid_for` lines on each node, so the `openbao` scope has no declaring backup and no `openbao` stream is watched. The Postgres half needs nothing from the operator: its script is live (`VALID_FOR = "52h"`, verified in the live ConfigMap) and its first declared uploads run at 02:00 CEST.

Preflight, changes nothing: `cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook playbooks/site-openbao.yml --tags openbao_backup --limit openbao --check`. Expect `changed=1` per node, the task `Install the backup wrapper script`, its diff the four comment lines and the one URL line. Any other change, or a failure, is a finding: send the output. Apply: the same line with `--check` deleted. Blast radius is srvvault1-3 only (the `openbao` group; `site.yml` excludes it), `serial: 1` on apply, and no service restarts: the wrapper runs from a oneshot timer, and the followers' `not the Raft leader` early exit is untouched. The login-proving task is skipped in this checkout (no staged `openbao-backup-secret-id`), so the run mints no OpenBao token.

One caveat: `--tags` skips Play 0, which re-stages the upload token from `terraform output`, and the staged `tmp/openbao-backup-token` dates from 2026-08-15. If the upload token was rotated since, run the same command without `--tags openbao_backup` so Play 0 re-stages it first.

Timing: the timers next fire tonight at 02:33 (srvvault3), 02:42 (srvvault1) and 02:52 (srvvault2) CEST. Applied before then, tonight's leader upload is the first declared one.

To settle it, once the leader has uploaded (and after 02:00 for Postgres), with the `q` helper from docs/runbooks/backup-freshness.md: `q 'backup_server_stream_valid_until_timestamp_seconds{scope=~"openbao|postgres-pas"}'` lists an `openbao-backup.tgz` stream and one `<db>.dump` per non-excluded database, each 52 h after its `backup_server_stream_last_backup_timestamp_seconds`; and `curl -s http://prometheus.home/api/v1/alerts | jq '[.data.alerts[].labels.alertname]'` names no `Backup*` alert. That settles verification.json V01, V05 and V19.

**Consequence:** Until it is done the OpenBao backup is unwatched: if it stops arriving no alert fires, which is the silent failure R1 named, still open for OpenBao.

**Provenance:** witnessed, test-agent, test phase, r1, read-only ssh to srvvault1-3 and verification.json V01/V05/V19
**Disposition:** Can you do this?

### ~~A1 — Delete the orphaned backup-server-tokens ConfigMap from the dev cluster's storage-prd namespace · nit~~ — closed by the operator, 2026-09-21

<details><summary>struck — body kept for the record</summary>

P3 removed it from HelmCharts configs/dev/storage/prd/manifests.yaml, but the live object stays: manifests.yaml goes through a plain kubectl apply that never prunes (tools/deploy/deploy_cli/helmops.py:202-203), and Jenkins deploys only configs/prd/. srvk8sdev is off by design, so the run did not touch it. While the node is up: `kubectl --kubeconfig ~/.kube/config-dev-write -n storage-prd delete configmap backup-server-tokens`. Nothing mounts it.

test-agent, test phase r1, 2026-09-19 — Live read (2026-09-19, kubectl get with config-dev-write, no writes): srvk8sdev is up but has no storage-prd namespace, no backup-server-tokens ConfigMap in any namespace and no backup-server Deployment, so there is no live object to delete. The dev storage release's manifests.yaml no longer ships it (HelmCharts 3419695, guarded by tests/test_storage_backup_server_metrics.py), so a later dev storage deploy will not recreate it. The operator can close this with no action.

**Consequence:** The dev cluster keeps an unused ConfigMap describing the retired tokens.yaml, so anyone reading live dev state is misled about how backup-server authorizes uploads.

**Provenance:** read, executor, P3, r1, plan.md P3 done-record
**Disposition:** Close — closed

</details>

## Notable events

Focus: A quiet run with no bail-out and no appended phase. N1 is the prd rollout in plan order: the metrics were served before the rules loaded, so `BackupWatcherBlind` never fired during the rollout.

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### ~~N1 — The test phase pushed all four repos in the plan's order; prd now serves backup-server's metrics and both alert rules are live and quiet~~ — closed by the operator, 2026-09-21

<details><summary>struck — body kept for the record</summary>

Under the devlock's pre-authorization, 2026-09-19 (CEST): DockerImages 0af47c9 pushed at 00:18, build #2526 SUCCESS (2m34s), which started IaC/HelmCharts #6542 SUCCESS (1m31s): prd's backup-server rolled to `sha256:0ffa8be8…`, serving metrics on :8081. HelmCharts pushed in two steps, as the plan orders. First 2ada3db (P3, P4), IaC/HelmCharts #6543 SUCCESS (3m04s): Service annotations and containerPort 8081 (a second Recreate roll at 00:25), and the postgres-pas script declaring `VALID_FOR = "52h"`. Then the gate before P5, all read-only: `up{service="backup-server"}` 1 on `http://172.16.128.197:8081/metrics`; `backup_server_refresh_last_success_timestamp_seconds` non-zero, the first full read of the real Drive remote finishing 21 s after start; `https://backup-server.home/metrics` 404 while `/health/healthz` answers 200, port 8081 refused through the hostname, the Service exposing only 8080. Only then 93626fc (P5), #6545 SUCCESS (1m26s): the `backup-freshness` group loaded at 00:29:33, both rules `health: ok, state: inactive` at 00:29:52, and `ALERTS{alertname=~"Backup.*"}` empty over the last 3 h, so the dead-watcher alert did not fire during rollout. Ansible bb4db40 pushed (deploys nothing): IaC/Build-Main #180 SUCCESS, lint and both `terraform validate` green, plan "No changes", protected-VM check passed. IaC/Apply was not touched.

Both Recreate rolls of prd's backup-server ended before the 01:30 uploads. Also read live: NodeMemoryStallCounterWedged is the one alert firing on prd (slice 018's, predicted there).

**Consequence:** none

**Provenance:** witnessed, test-agent, test phase, r1, DockerImages #2526, IaC/HelmCharts #6542 #6543 #6545, IaC/Build-Main #180, prd Prometheus and kubectl reads
**Disposition:** Ok — closed

</details>

## Bugs

Focus: B7 first, witnessed: IaC/HelmCharts build logs expose a live GitHub token. It is a defect of the HelmCharts Jenkinsfile, not of this slice. Next B3 (witnessed) and B4 (read), both in backup-server code this slice shipped: each lets a failure pass without a trace. B1 is already fixed on HelmCharts main. Of the five live bugs, two are witnessed.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### ~~B1 — HelmCharts CLAUDE.md states Prometheus retains ~2 days (retentionSize 2GB); prd values set 7d / 10GB · nit~~ — fixed in HelmCharts 73560d9, before this close-out

<details><summary>struck — body kept for the record</summary>

HelmCharts CLAUDE.md (recommend-resources entry) says 'Prometheus retains ~2 (`retentionSize: 2GB`), so runs measure roughly the last two days'. configs/prd/prometheus/prd/values.yaml:3-4 sets retention: 7d and retentionSize: 10GB. Not touched by this slice.

consult 1, 2026-09-19 — Already fixed on HelmCharts main by 73560d9 (2026-09-18, slice 018 close-out B2): CLAUDE.md now reads 'retention: 7d, retentionSize: 10GB' and a 7-day window. Nothing left to do; the entry stands only because it was filed before that commit.

doc-writer, doc phase, 2026-09-19 — Already fixed on HelmCharts main (73560d9, not this slice): CLAUDE.md:76 now states retention: 7d and retentionSize: 10GB, matching configs/prd/prometheus/prd/values.yaml. Nothing left to do; this entry can be closed.

**Consequence:** A reader sizing recommend-resources runs underestimates the history Prometheus actually holds.

**Provenance:** read — plan-writer, planning, r1, HelmCharts CLAUDE.md vs configs/prd/prometheus/prd/values.yaml
**Disposition:** Fix inline please. — already fixed on HelmCharts main by 73560d9 (CLAUDE.md:76 states retention: 7d, retentionSize: 10GB); nothing left to change

</details>

### ~~B2 — HelmCharts postgres-pas comments say only prd has a backup-server; a dev storage release carrying backup-server exists · nit~~ — closed by the operator, 2026-09-21

<details><summary>struck — body kept for the record</summary>

HelmCharts charts/postgres-pas/values.yaml:93-95 says 'only the prd cluster has a backup-server (the storage release isn't deployed on dev)', and configs/prd/postgres-pas/prd/values.yaml:51 says '(prd has one; dev does not)'. HelmCharts configs/dev/storage/prd/{values.yaml,manifests.yaml} is a dev storage release that carries backup-server's age-key ConfigMap, and the slice's refinement settled that backup-server runs on the dev cluster too. The live dev cluster was not checked (srvk8sdev is off). Not touched by this slice.

test-agent, test phase r1, 2026-09-19 — Live read (2026-09-19, kubectl get ns with config-dev-write): the dev cluster has no storage-prd namespace and no backup-server, so 'the storage release isn't deployed on dev' is true of live dev today; only the configs/dev/storage release definition exists. The entry's consequence narrows to a reader of the chart who later deploys that dev release.

**Consequence:** A reader of the postgres-pas chart believes dev has no backup-server, so they overlook the dev copy when changing backup-server or testing uploads there.

**Provenance:** read — plan-reviewer, planning, r1, HelmCharts charts/postgres-pas/values.yaml vs configs/dev/storage/prd/
**Disposition:** The comment is correct. The dev backup server is not deployed. The dev cluster is not to run development apps. That's what the dev stage is for. The dev cluster is for writing and testing charts. Normal state is that none of my apps is deployed on it. — closed

</details>

### ~~B3 — DockerImages backup-server: a malformed valid_for (e.g. 52h%zz) is silently dropped; the upload is stored undeclared with 201 · minor~~ — closed by the operator, 2026-09-21

<details><summary>struck — body kept for the record</summary>

r.URL.Query() (handler.go:76) discards pairs with a malformed percent-escape, so query.Has("valid_for") (:91) sees no key. A scratch probe gave valid_for=52h%zz and valid_for=%3 each 201 with the backup stored and no .metadata.json. The planned uploaders send a literal 52h, so today this is reachable only through an uploader URL bug.

**Consequence:** An uploader with a URL-building bug gets 201 and believes it declared a validity, but its stream is never watched, so a later outage of that backup raises no alert.

**Provenance:** witnessed — code-reviewer, P1, round 1, phases/P1/code_review_r1.md F2
**Disposition:** Is this really an issue? Feels like I prefer to close this. — not today, by the entry's own body: "The planned uploaders send a literal 52h, so today this is reachable only through an uploader URL bug" — both uploaders (the OpenBao wrapper and the postgres-pas script) send a literal 52h; closed

</details>

### ~~B4 — DockerImages backup-server: RcloneBackend.Delete reports any rclone failure whose stderr says "not found" or "no such" as ErrNotFound · minor~~ — fixed in DockerImages 7bcc242

<details><summary>struck — body kept for the record</summary>

backup-server/src/internal/pipeline/backend.go Delete matches stderr substrings, so a DNS "no such host" or a missing rclone config reads as an already-deleted object. Prune and the upload cleanup skip ErrNotFound without logging. P2 review r1 F1 fixed the same classification in lsjson (rclone exit code 3 only, commit 0af47c9); Delete predates the slice and was left as is. rclone's documented file-not-found exit code is 4.

**Consequence:** A prune or cleanup delete that fails for a network or config reason logs nothing, so the object stays in Drive past its retention and nobody sees why.

**Provenance:** read — code-writer, P2, review-fix round 2, phases/P2/code_review_r1.md F1
**Disposition:** Fix inline if possible. — fixed in DockerImages 7bcc242: Delete takes ErrNotFound only from rclone exit codes 4 and 3, as lsjson does; new TestRcloneDeleteFailures, go test ./... green; committed locally, push pending

</details>

### ~~B5 — Ansible backup-freshness runbook §2 says the 10-minute read timeout logs 'context deadline exceeded'; the call running at the deadline logs 'signal: killed' · nit~~ — resolved in consult 1 (Ansible bb4db40): docs/runbooks/backup-freshness.md §2 now names 'signal: killed' (the call running at the 10-minute limit) beside 'context deadline exceeded' (one started after it), in any of the bullet's log lines; kc project lint re-run green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

docs/runbooks/backup-freshness.md:182. Every rclone call in backup-server runs under exec.CommandContext within the 10-minute refreshTimeout (DockerImages backup-server/src/internal/pipeline/backend.go:104,132; freshness/watcher.go:20). The command running when the deadline hits returns its exit status, 'signal: killed'. Only a command started after the deadline returns 'context deadline exceeded'. Witnessed on go1.26.5.

**Consequence:** An operator reading a timed-out refresh's 'rclone lsjson: signal: killed' log finds no matching bullet, takes a slow Drive read for an unreadable folder or a broken login, and chases the wrong cause.

**Provenance:** witnessed — code-reviewer, P6, r1, phases/P6/code_review_r1.md F1
**Disposition:**

</details>

### ~~B6 — Ansible backup-freshness runbook §2's safe-restart window (outside 02:00–03:00) misses the youtrack-backup upload at 01:30 · nit~~ — resolved in consult 1 (Ansible bb4db40): docs/runbooks/backup-freshness.md §2's safe-restart window is now outside 01:30–03:00, naming YouTrack's 01:30 upload; kc project lint re-run green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

docs/runbooks/backup-freshness.md:185. The youtrack-backup CronJob uploads to backup-server at '30 1 * * *' with a 1 h deadline (HelmCharts charts/youtrack/values.yaml:36,39; live prd CronJob). backup-server is a Recreate Deployment, so a restart at 01:30–02:00 leaves no pod to take that upload.

**Consequence:** A backup-server restart at 01:30–02:00, which the runbook allows, fails that night's YouTrack backup. One missed night pages nobody, but it uses up the one-night margin.

**Provenance:** read — code-reviewer, P6, r1, phases/P6/code_review_r1.md F2
**Disposition:**

</details>

### ~~B7 — HelmCharts Jenkinsfile: IaC/HelmCharts build logs print the GitHub token (--set gitToken=…) in plaintext · minor~~ — closed by the operator, 2026-09-21

<details><summary>struck — body kept for the record</summary>

The `Gate releases` stage's `helm lint` and `helm template` command lines (build #6542, log lines 97 and 105, and the same shape for every gated release) carry `--set gitToken=<value>` with the value expanded, and Jenkins does not mask it: the log API returns a plain `ghp_…` token. Not touched by this slice; found while reading #6542 to confirm the storage deploy. The value is deliberately not repeated here.

**Consequence:** Anyone who can read IaC/HelmCharts build logs or the Jenkins API can read a live GitHub token, and it stays in every stored build log until the token is rotated and the logs are purged.

**Provenance:** witnessed, test-agent, test phase, r1, IaC/HelmCharts #6542, searched with the Jenkins MCP
**Disposition:** Close — closed

</details>

## Open questions and rulings

Focus: Q1 only: does YouTrack's upload opt in with `valid_for=52h`? Until someone decides, YouTrack stays on its CronJob-status rule. The HelmCharts rule comment claiming this slice retires that rule is wrong either way.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — A third uploader to backup-server, the youtrack chart's youtrack-backup CronJob, landed after the plan and declares no validity · minor

HelmCharts fab8483 (2026-09-17, card 1033, ANS-73) added charts/youtrack/files/backup/backup.py, which POSTs to backup-server /upload with filename only (:104-105), and an interim YouTrackBackupStale rule in configs/prd/prometheus/prd/values.yaml:210-236 whose comment says it goes once slice 023 ships and the upload declares its own validity. The plan's grounding (2026-09-15) says no other uploader exists, and no phase opts YouTrack in or retires that rule. Question: does opting YouTrack in (valid_for=52h in its upload, then deleting the youtrack-backup rule group and tests/test_prometheus_youtrack_backup_alert.py) belong in this slice, or in a follow-up card?

executor P5, 2026-09-18 — P5's BackupOverdue selects every scope on backup-server, not a list: were YouTrack to join, its upload would need only valid_for (as P4 did for postgres-pas), and the interim YouTrackBackupStale group would then be deleted. P5 left that group untouched.

consult 1, 2026-09-19 — Not owed by the plan: the rulings opt in OpenBao and the Postgres dumps only, and YouTrack's uploader landed two days after the grounding. Opting it in is a one-line valid_for=52h in charts/youtrack/files/backup/backup.py plus deleting the youtrack-backup rule group and its test; it needs the operator's ruling, not a phase. If ruled in, the runbook's 'Streams watched today' table and decisions.md's §Backup YouTrack entry change with it.

doc-writer, doc phase, 2026-09-19 — decisions.md §Backup's YouTrack entry now states the current state (AnsibleSpecs af566cd): its uploads declare no validity, so BackupOverdue does not watch it, and YouTrackBackupStale covers it. It no longer says slice 023 opts the stream in. The HelmCharts rule comment above the youtrack-backup group (configs/prd/prometheus/prd/values.yaml) still says the group goes once slice 023 ships. Whichever way Q1 is ruled, that comment needs an edit.

**Consequence:** The YouTrack backup is never a watched backup-server stream, and the interim CronJob-status rule stays although its own comment says slice 023 retires it.

**Provenance:** witnessed, code-writer, P4, r1, HelmCharts charts/youtrack/files/backup/backup.py
**Disposition:** Create a card for the YouTrack project please.

## Suggestions

Focus: S2 and S5 (read) are doc work for another slice. backup-server's own api.md and README describe neither the validity nor the metrics, because this doc phase lands only in Ansible. No runbook covers renewing the Drive login that `BackupWatcherBlind` points at. S1, S3 and S4 (all witnessed) are missing gates and tests; S4 needs promtool in the iac image.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — DockerImages declares no kc project components, so the run loop has no deterministic gate for backup-server phases · minor

run_loop.py --dry-run reports P1 and P2 (Target ../DockerImages) as '(no deterministic gate)'; `kc project list` in /work/DockerImages exits 1. backup-server's Go suite (`go test ./...` from backup-server/src, in the `go` tool container) runs only when the executor runs it by hand. The plan names that command in P1; declaring the component would make it the driver's gate.

**Consequence:** A red backup-server suite in a DockerImages phase is not caught by the driver's gate; it rests on the executor and reviewer running it.

**Provenance:** witnessed — plan-writer, planning, r1, run_loop.py --dry-run output
**Disposition:** Raise. — already raised as DI-6 (a .kubecoder/project.yaml for DockerImages, operator-accepted at the Fieldnotes triage 2026-09-20); this entry added to it as evidence

### S4 — HelmCharts suite never parses the prd alerting rules as Prometheus would; no promtool in the iac image · minor

The prd Prometheus release's rules (configs/prd/prometheus/prd/values.yaml, serverFiles.alerting_rules.yml) are held by pytest files that match each expression with a regex; nothing parses the PromQL or the annotation templates. The iac container has no promtool. In P5 the two new expressions were parsed by hand against the live prd Prometheus query API (3.14.0); their annotation templates were not checked. A promtool check rules step over the rendered rules file would close it.

test-agent, test phase r1, 2026-09-19 — Both P5 rules loaded on the live prd Prometheus 3.14.0 without error (2026-09-19 00:29): /api/v1/rules shows BackupOverdue and BackupWatcherBlind health ok, and their expressions evaluate against live series. The gap remains for future rules, but these two are not affected.

**Consequence:** A PromQL or template syntax error in a new rule passes the suite and CI; the prd Prometheus rejects the reloaded rules file and keeps evaluating the old one, so the new alert never fires and nothing says so.

**Provenance:** witnessed — executor, P5, r1
**Disposition:** Raise. — already raised as ANS-74 (promtool in the iac toolchain, from slice 018 S2); this entry added to it as evidence

### ~~S2 — DockerImages backup-server api.md and README describe neither valid_for nor the metrics listener, and the doc plan names no DockerImages surface · minor~~ — fixed in DockerImages b6f596f

<details><summary>struck — body kept for the record</summary>

backup-server/api.md documents POST /upload with only 'filename' and lists three endpoint groups on a single port; README.md's configuration table has no METRICS_LISTEN_ADDR (default :8081, GET /metrics only) and its prune step still counts every name. P1 added valid_for and P2 the metrics listener without touching either (prose docs are the doc phase's), but Ansible docs/slice-doc-plan.md lists only Ansible/AnsibleSpecs surfaces, so the doc phase may not reach these files. README.md also still names the retired backup-server-tokens ConfigMap under Deployment.

doc-writer, doc phase, 2026-09-19 — Still open after the doc phase. The driver lands only the Ansible doc branch, so the DockerImages docs were not edited. What the slice made untrue or incomplete there: api.md's upload section has no valid_for and no /metrics; README.md's prune step (keep the newest retention objects) now counts backups only and deletes each pruned backup's metadata file; its env table lacks METRICS_LISTEN_ADDR (default :8081). README's restore loop decrypts only *.age, so the .metadata.json files are skipped correctly.

**Consequence:** A reader of backup-server's own docs does not learn that uploads can declare a validity or that freshness metrics are served on :8081, so they wire a new uploader or scrape config from an incomplete contract.

**Provenance:** read — code-writer, P2, round 1, DockerImages backup-server/api.md, backup-server/README.md
**Disposition:** Fix inline. — fixed in DockerImages b6f596f: api.md documents valid_for, the .metadata.json file and GET /metrics on :8081; README gains the metadata and prune steps, METRICS_LISTEN_ADDR, and drops the retired backup-server-tokens ConfigMap; committed locally, push pending

</details>

### ~~S3 — DockerImages backup-server: no test pins the post-upload refresh running after the prune, or :8080 not serving /metrics · minor~~ — closed by the operator, 2026-09-21

<details><summary>struck — body kept for the record</summary>

Two behaviours in P2's outcome survive a mutation run. Swapping Handler.afterUpload to refresh before it prunes (internal/handler/handler.go:163-168) leaves the suite green. So does registering GET /metrics on the :8080 mux in Handler.Routes (handler.go:47-58); TestMetrics checks only that the :8081 handler serves nothing but /metrics. The code is correct today on both points.

test-agent, test phase r1, 2026-09-19 — Live state today (2026-09-19): through the ingress hostname, https://backup-server.home/metrics and https://backup-server/metrics answer 404 while /health/healthz answers 200, and port 8081 is refused via the hostname. The property holds on prd now; the entry stands because no test pins it.

**Consequence:** A later change that reorders the post-upload refresh or exposes /metrics on the port nginx proxies passes the suite. The first leaves a pruned-away stream publishing for up to an hour. The second makes stream names and times answerable through backup-server.home.

**Provenance:** witnessed, code-reviewer, P2, r1, phases/P2/code_review_r1.md F2
**Disposition:** Close. — closed

</details>

### ~~S5 — No runbook covers renewing backup-server's Drive login (the gdrive-pieter remote in /data/rclone.conf on rclone-backup-pvc) · minor~~ — closed by the operator, 2026-09-21

<details><summary>struck — body kept for the record</summary>

Writing docs/runbooks/backup-freshness.md (P6), BackupWatcherBlind's most likely total-blindness cause is a Drive login backup-server can no longer use: its full read logs 'freshness refresh: list gdrive-pieter:Homelab Backups: …' and every upload answers 500. The login lives in the gdrive-pieter remote of /data/rclone.conf on the rclone-backup-pvc volume (backup-server image sets RCLONE_CONFIG=/data/rclone.conf). No runbook in Ansible docs/runbooks/ or HelmCharts says how that token is renewed, so the new runbook states it is not covered rather than inventing a procedure.

**Consequence:** When backup-server's Drive login expires or is revoked, BackupWatcherBlind fires and every upload fails, and the operator has no written procedure to renew the login and restore both backups and the watching.

**Provenance:** read, code-writer, P6, r1, docs/runbooks/backup-freshness.md §2
**Disposition:** Close. — closed

</details>
