# Close-out — slice 023 backup_freshness_alerting

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Delete the orphaned backup-server-tokens ConfigMap from the dev cluster's storage-prd namespace · nit

P3 removed it from HelmCharts configs/dev/storage/prd/manifests.yaml, but the live object stays: manifests.yaml goes through a plain kubectl apply that never prunes (tools/deploy/deploy_cli/helmops.py:202-203), and Jenkins deploys only configs/prd/. srvk8sdev is off by design, so the run did not touch it. While the node is up: `kubectl --kubeconfig ~/.kube/config-dev-write -n storage-prd delete configmap backup-server-tokens`. Nothing mounts it.

**Consequence:** The dev cluster keeps an unused ConfigMap describing the retired tokens.yaml, so anyone reading live dev state is misled about how backup-server authorizes uploads.

**Provenance:** read, executor, P3, r1, plan.md P3 done-record
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — HelmCharts CLAUDE.md states Prometheus retains ~2 days (retentionSize 2GB); prd values set 7d / 10GB · nit

HelmCharts CLAUDE.md (recommend-resources entry) says 'Prometheus retains ~2 (`retentionSize: 2GB`), so runs measure roughly the last two days'. configs/prd/prometheus/prd/values.yaml:3-4 sets retention: 7d and retentionSize: 10GB. Not touched by this slice.

**Consequence:** A reader sizing recommend-resources runs underestimates the history Prometheus actually holds.

**Provenance:** read — plan-writer, planning, r1, HelmCharts CLAUDE.md vs configs/prd/prometheus/prd/values.yaml
**Disposition:**

### B2 — HelmCharts postgres-pas comments say only prd has a backup-server; a dev storage release carrying backup-server exists · nit

HelmCharts charts/postgres-pas/values.yaml:93-95 says 'only the prd cluster has a backup-server (the storage release isn't deployed on dev)', and configs/prd/postgres-pas/prd/values.yaml:51 says '(prd has one; dev does not)'. HelmCharts configs/dev/storage/prd/{values.yaml,manifests.yaml} is a dev storage release that carries backup-server's age-key ConfigMap, and the slice's refinement settled that backup-server runs on the dev cluster too. The live dev cluster was not checked (srvk8sdev is off). Not touched by this slice.

**Consequence:** A reader of the postgres-pas chart believes dev has no backup-server, so they overlook the dev copy when changing backup-server or testing uploads there.

**Provenance:** read — plan-reviewer, planning, r1, HelmCharts charts/postgres-pas/values.yaml vs configs/dev/storage/prd/
**Disposition:**

### B3 — DockerImages backup-server: a malformed valid_for (e.g. 52h%zz) is silently dropped; the upload is stored undeclared with 201 · minor

r.URL.Query() (handler.go:76) discards pairs with a malformed percent-escape, so query.Has("valid_for") (:91) sees no key. A scratch probe gave valid_for=52h%zz and valid_for=%3 each 201 with the backup stored and no .metadata.json. The planned uploaders send a literal 52h, so today this is reachable only through an uploader URL bug.

**Consequence:** An uploader with a URL-building bug gets 201 and believes it declared a validity, but its stream is never watched, so a later outage of that backup raises no alert.

**Provenance:** witnessed — code-reviewer, P1, round 1, phases/P1/code_review_r1.md F2
**Disposition:**

### B4 — DockerImages backup-server: RcloneBackend.Delete reports any rclone failure whose stderr says "not found" or "no such" as ErrNotFound · minor

backup-server/src/internal/pipeline/backend.go Delete matches stderr substrings, so a DNS "no such host" or a missing rclone config reads as an already-deleted object. Prune and the upload cleanup skip ErrNotFound without logging. P2 review r1 F1 fixed the same classification in lsjson (rclone exit code 3 only, commit 0af47c9); Delete predates the slice and was left as is. rclone's documented file-not-found exit code is 4.

**Consequence:** A prune or cleanup delete that fails for a network or config reason logs nothing, so the object stays in Drive past its retention and nobody sees why.

**Provenance:** read — code-writer, P2, review-fix round 2, phases/P2/code_review_r1.md F1
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — A third uploader to backup-server, the youtrack chart's youtrack-backup CronJob, landed after the plan and declares no validity · minor

HelmCharts fab8483 (2026-09-17, card 1033, ANS-73) added charts/youtrack/files/backup/backup.py, which POSTs to backup-server /upload with filename only (:104-105), and an interim YouTrackBackupStale rule in configs/prd/prometheus/prd/values.yaml:210-236 whose comment says it goes once slice 023 ships and the upload declares its own validity. The plan's grounding (2026-09-15) says no other uploader exists, and no phase opts YouTrack in or retires that rule. Question: does opting YouTrack in (valid_for=52h in its upload, then deleting the youtrack-backup rule group and tests/test_prometheus_youtrack_backup_alert.py) belong in this slice, or in a follow-up card?

**Consequence:** The YouTrack backup is never a watched backup-server stream, and the interim CronJob-status rule stays although its own comment says slice 023 retires it.

**Provenance:** witnessed, code-writer, P4, r1, HelmCharts charts/youtrack/files/backup/backup.py
**Disposition:**

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — DockerImages declares no kc project components, so the run loop has no deterministic gate for backup-server phases · minor

run_loop.py --dry-run reports P1 and P2 (Target ../DockerImages) as '(no deterministic gate)'; `kc project list` in /work/DockerImages exits 1. backup-server's Go suite (`go test ./...` from backup-server/src, in the `go` tool container) runs only when the executor runs it by hand. The plan names that command in P1; declaring the component would make it the driver's gate.

**Consequence:** A red backup-server suite in a DockerImages phase is not caught by the driver's gate; it rests on the executor and reviewer running it.

**Provenance:** witnessed — plan-writer, planning, r1, run_loop.py --dry-run output
**Disposition:**

### S2 — DockerImages backup-server api.md and README describe neither valid_for nor the metrics listener, and the doc plan names no DockerImages surface · minor

backup-server/api.md documents POST /upload with only 'filename' and lists three endpoint groups on a single port; README.md's configuration table has no METRICS_LISTEN_ADDR (default :8081, GET /metrics only) and its prune step still counts every name. P1 added valid_for and P2 the metrics listener without touching either (prose docs are the doc phase's), but Ansible docs/slice-doc-plan.md lists only Ansible/AnsibleSpecs surfaces, so the doc phase may not reach these files. README.md also still names the retired backup-server-tokens ConfigMap under Deployment.

**Consequence:** A reader of backup-server's own docs does not learn that uploads can declare a validity or that freshness metrics are served on :8081, so they wire a new uploader or scrape config from an incomplete contract.

**Provenance:** read — code-writer, P2, round 1, DockerImages backup-server/api.md, backup-server/README.md
**Disposition:**

### S3 — DockerImages backup-server: no test pins the post-upload refresh running after the prune, or :8080 not serving /metrics · minor

Two behaviours in P2's outcome survive a mutation run. Swapping Handler.afterUpload to refresh before it prunes (internal/handler/handler.go:163-168) leaves the suite green. So does registering GET /metrics on the :8080 mux in Handler.Routes (handler.go:47-58); TestMetrics checks only that the :8081 handler serves nothing but /metrics. The code is correct today on both points.

**Consequence:** A later change that reorders the post-upload refresh or exposes /metrics on the port nginx proxies passes the suite. The first leaves a pruned-away stream publishing for up to an hour. The second makes stream names and times answerable through backup-server.home.

**Provenance:** witnessed, code-reviewer, P2, r1, phases/P2/code_review_r1.md F2
**Disposition:**
