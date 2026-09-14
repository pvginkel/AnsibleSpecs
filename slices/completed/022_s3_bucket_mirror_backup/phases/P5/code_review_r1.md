# P5 code review — round 1

Range `bf11aa5..3f44ad8` (Ansible `phase/022-P5`), one file: `docs/runbooks/s3-mirror.md`.

**Readiness.** The phase is ready to merge. The runbook delivers everything P5 asks for:
- whole-bucket restores, single objects and earlier versions, writing with the app's own key (§2, §3);
- a no-cluster read from the Drive login and the Roboform crypt key (§4);
- the dev-Ceph drill: scratch user and bucket, restore, `rclone check --download` against the live bucket read with `backup-reader`'s key, then cleanup (§5);
- a pending drill log;
- the B2 credential table.

Its facts match HelmCharts `main` (P2–P4 landed):
- the crypt env matches `charts/storage/templates/s3-mirror-cronjob.yaml:60-69`, and `driveRemote` matches `configs/prd/storage/prd/values.yaml:23`;
- the app Secret is the module default `s3-credentials` (`terraform-modules/s3-storage/main.tf:43-47`), and no prd call site overrides it;
- `backup-reader-credentials` is written in `configs/prd/storage/_shared/infrastructure.tf`;
- the OpenBao path and fields match `configs/prd/storage/prd/values.yaml:71-79`;
- VM 919 is on node `pve` (`terraform/prd/vms.tf:96-97`);
- `microceph.radosgw-admin` is the role's own invocation (`ansible/roles/microceph/tasks/users.yml:68`).

I ran the runbook's commands with rclone v1.75.1 against local directories. The mirror data was written the job's way, three `sync --backup-dir` nights through a loss:
- the runbook's `read` + `printf | rclone obscure -` remote decrypts data written with the job's Python-obscured key;
- §2 steps 4–5 (current, then archives newest-first) end every lost or overwritten key at its pre-loss version;
- step 6's `--one-way --download` check reports only the keys put back from the archive, as the text says;
- §3's `lsl` on a single file and `--include '/*/<key>'` (nested key too) print what the text describes;
- a wrong password gives the `Skipping undecryptable` notices §1 names.

Gate: green; the root project has no test statements. Nothing in the runbook has run against live infrastructure; V03 closes on the operator's drill output in the test phase. There are two Minor, advisory findings and nothing blocking.

## Findings

### F1 — Minor · advisory · anchor: failing-test · confidence: high

**The no-browser Drive login in §1 step 1 saves a remote without a token and prints no `rclone authorize` command.**

- **What the runbook says.** `s3-mirror.md:65-66`: on a host without a browser, "add `config_is_local=false` and run the `rclone authorize` command it prints on a host that has one."
- **What happened.** I ran `rclone config create gdrive-pieter drive scope=drive config_is_local=false` with rclone v1.75.1 under a pseudo-terminal. It exited 0 at once and printed nothing but the saved section: `[gdrive-pieter] type = drive, scope = drive, client_id =, client_secret =, team_drive =`. There was no token and no authorize command. `rclone config create` takes each question's default, and the `config_token` question's default is empty (see `rclone config create --help`).
- **The browser path works.** The same command without `config_is_local=false` did enter the OAuth wait.
- **Consequence.** An operator on a browserless host has nothing to act on. The saved `gdrive-pieter` remote fails at the first `rclone lsf mirror:` in step 2.
- **Why it matters.** This hits §4, the whole-site case, where the rclone host is whatever machine survives. The Conventions requirement of a browser (`:20-21`) limits the exposure, which is why this is advisory.

### F2 — Minor · advisory · anchor: none · confidence: medium

**§2's rule "every folder stamped after the loss" skips a run that was still in progress when the loss happened.**

- **The rule.** `s3-mirror.md:139-140` and `:153-155` pick the archive folders to replay by comparing each stamp with the loss time.
- **How the stamp is set.** The stamp is taken once, when the run starts (HelmCharts `charts/storage/files/s3-mirror/s3_mirror.py:103`). Buckets are then synced one after another (`:105-109`), within a Job bounded at 2 h (`charts/storage/values.yaml:44`).
- **The miss.** Take a loss at time L inside a run stamped S, with S < L, and before that run's sync reaches the bucket. The pre-loss versions are moved into `archive/<bucket>/<S>/`, which the rule excludes.
- **Why nothing catches it.** Step 6's one-way check compares only against `current/` (`:164`). The restore finishes with those keys still missing or still at their damaged version, and the check does not show it.
- **Likelihood.** The window is short in a normal incremental night, so this is an unlikely edge rather than a routine failure.
