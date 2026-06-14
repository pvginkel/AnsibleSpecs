# Helm + TF deploy harness — finalization (Jenkins-on-iac, cleanup, TODO)

> **STATUS (2026-06-14): Phases 0–4 are CLOSED** (Phase 3 bar one manual
> OpenBao step). The deploy harness is live — the HelmCharts pipeline
> runs per-release on the `iac` harness (one `iac -c` per release, stages
> named `Deploying <chart>@<stage>`, nginx/jenkins last), TF state flows
> through `terraform-backend-git` (prd state seeded + sops-encrypted), the
> version-poller works again, and the `tools/` tree is one poetry/uv
> project. **Phase 4** (orphan audit) ran clean and is closed; **Phase 3**
> (Ceph/S3/cephx cleanup) executed against prd — only §5 (retire the
> OpenBao god-leaf `kv/shared/ceph-rgw/s3`) is left, and it is a manual
> operator/`bao` step. **Phase 5 is cancelled; Phase 6 is done.** Phase 5
> (delete `tools/migrate*`) was **cancelled** — the migration tooling is
> retained on purpose as the basis for a possible future bulk resource
> rename. Phase 6 is **done**: 6.1 (the `homelab_zfs_dataset` provider fix)
> is published (`0.1.25`) and `atime=off` declared on the hostPath
> datasets; 6.2 (static-PV stage naming) is resolved as **documentation** —
> the convention + per-chart rework plan live in HelmCharts `CLAUDE.md`
> rather than a mass rename. The only residual is operator runtime: the §5
> `bao` god-leaf delete and applying the 6.1 change (`deploy apply
> prd/media`; `deploy import` + `apply prd/storage`). See the per-phase
> notes below for exactly what landed and the few follow-ups. Notable
> deltas from the plan as written below:
>
> - **uv, not poetry, in the pipeline.** Per-release `iac -c` calls
>   reinstall the deploy project per container, so the Jenkinsfiles use
>   `uv venv` + `uv pip install -e .` (sub-second) and call the console
>   scripts by path; poetry stays in the iac image for manual use. uv was
>   added to the iac image (Ansible) and used in the k8s arch container.
> - **`chart_tools.deploy_cmd()`** resolves the `deploy` console script
>   next to the running interpreter (uv / poetry / system), replacing the
>   hardcoded `poetry run deploy` shell-outs in resolve-helm-args /
>   gen-architecture.
> - **version-poller (Phase 2 open decision): kept the no-install shim**,
>   made self-sufficient — `deploy_cmd` falls back to
>   `python -m deploy_cli.main` and the shim puts `tools/deploy` on
>   `PYTHONPATH`, so the poller (bare interpreter) runs untouched.
> - **secrets.yaml sets `KUBECONFIG`** (not just `KUBE_CONFIG_PATH`) —
>   helm/kubectl and the standalone `resolve-helm-args` read KUBECONFIG.
> - **srviac egress**: routed to the Ceph public network
>   `192.168.188.0/24` (mons **and** OSDs; only the RGW VIP is on 10.1) —
>   the homelab provider's RBD/S3 ops hung silently without it.
> - **Jenkinsfile.architecture**: uv + single k8s container (dropped the
>   python sidecar — arch-validate.py is stdlib-only).
> - **disabled releases** uninstall when the disable lands (a change),
>   then their stage stays skipped — not a per-run no-op uninstall.
> - **Resolved open decisions**: Jenkinsfile stays in HelmCharts; `repos:`
>   list in secrets.yaml; Phase 2 = option B; poller keeps a no-install
>   entry path.
> - **Drive-by fixes**: headlamp's malformed values-comment (broke both
>   render + deploy); the `design-assistant` Architecture view's release
>   label (`design-assistant@prd` → `design-assistant`, matching the
>   bare-prd convention; committed in `pvginkel/Architecture`).
> - **storage chart — Samba shares now on a managed dataset** (HelmCharts
>   `84f3989`). The `[Software]`/`[Backups]` shares served
>   `/zpool2/share/{software,backups}` off the `zpool2/share` dataset,
>   which no TF declared (the one ZFS dataset the storage release used
>   that wasn't a managed resource — surfaced by the Phase-4 audit).
>   Declared `homelab_zfs_dataset.share` (prevent_destroy, like
>   `rclone_backup`) and made every `smb.conf` path render from
>   `storage.zfs.{pool,dataset,shareDataset}` via `tpl`. **PENDING operator
>   step before this deploys** (the dataset already exists, so apply would
>   try to create it): `poetry run deploy import prd/storage
>   homelab_zfs_dataset.share zpool2/share`.

## Goal

Close out [helm-tf-deploy-harness](helm-tf-deploy-harness.md) +
[helm-tf-deploy-harness-ceph-changes](helm-tf-deploy-harness-ceph-changes.md).
The repo-side restructure is done and the prd live cutover is complete
(`tools/migrate-release.py prd` reports **all 45 releases migrated**;
`tools/migrate/prd-done.txt` is full). What remains is everything the
migration script *didn't* do, plus the operational change the operator
decided on after the fact: **the deploy runs through the `iac` harness,
not an in-cluster Jenkins agent.**

After this slice lands:

- `restructure` is merged to `main` (operator).
- `poetry run deploy` runs inside the `iac` container the same way
  Ansible's Terraform does — host `flock` serialization, the
  `terraform-backend-git` HTTP state backend, no repo-side TerraformState
  bookkeeping. The HelmCharts pipeline is re-enabled.
- The leftover old-world Ceph/S3/cephx objects are deleted (the manual
  checklist `migrate-release.py` prints when the plan is exhausted), the
  prd cluster is swept for anything else the migration missed, and
  `tools/migrate-release.py` + `tools/migrate/` are removed.
- The two `TODO.md` follow-ups are resolved.

## Where we are (2026-06-13) — pre-execution snapshot, superseded by STATUS above

- Branch `restructure` in `HelmCharts-2`, clean; head
  `5f94522 Migration cutover fixes (prd live-migration complete, 45/45)`.
  Not yet merged to `main`; nothing pushed.
- Live prd cutover **done**: every release deployed on the harness
  layout into its `<chart>-prd` namespace, RBD images live-migrated to
  pool `k8s`, fresh CephFS subvolumes / S3 buckets populated, ZFS
  datasets imported/created. The dev cluster has been on the harness
  since earlier.
- The HelmCharts Jenkins pipeline is **disabled** (intentionally — the
  current `Jenkinsfile` still assumes the old in-cluster agent +
  self-managed TerraformState clone, which is being replaced here).
- prd TF state currently lives **only** in the operator's local
  `../TerraformState` working copy under
  `helm-charts/<cluster>/<chart>/<stage>/<phase>.tfstate` (committed by
  the CLI during the migration, **unpushed**). The remote
  `pvginkel/TerraformState` is now owned by `terraform-backend-git` and
  already holds Ansible's encrypted `prd/` + `scratch/` state. Seeding
  the helm-charts state into that backend is an explicit step below — do
  not skip it or prd re-imports/recreates everything.

## Phase 0 — merge to main (operator) — ✅ DONE

Operator merges `restructure` → `main` in `HelmCharts`, pushes Ansible +
IaCAgent + this AnsibleSpecs commit. Sequenced **before** re-enabling the
pipeline; the pipeline stays disabled until Phase 1 lands so a push to
main can't fire the old Jenkinsfile.

## Phase 1 — deploy on the iac harness + HTTP state backend — ✅ DONE

The crux. Today the deploy CLI clones `TerraformState`, writes
`backend "local" {}` state files under it, and `git add`/`commit`s each
mutation (Jenkins pushes at the end). The `iac` model deletes all of
that: a `backend "http"` block points at `terraform-backend-git` on
`127.0.0.1:6061`, and the daemon does the pull/push + sops+age encryption
against `pvginkel/TerraformState` itself. This is exactly the cutover
Ansible already did (`Ansible/terraform/{prd,scratch}/backend.tf`,
`IaCAgent/bin/iac-impl`, `Ansible/scripts/tf-backend.sh`); we mirror it.

Cross-repo: **HelmCharts** (CLI + Jenkinsfile + scripts), **IaCAgent**
(`iac-impl` multi-repo), **Ansible** (iac image, `secrets.example.yaml`,
OpenBao AppRole policy).

### 1a. HelmCharts deploy CLI — switch to the HTTP backend

`tools/deploy/deploy_cli/tf.py` + `_providers/providers.tf`:

- `_providers/providers.tf`: `backend "local" {}` → `backend "http" {}`.
- `tf.py`: delete `_state_repo()`, `_state_file()`, `_commit_state()` and
  every call to it (the `finally: _commit_state(...)` in `apply` /
  `import_resource` / `destroy`). The backend owns push/pull now.
- `_init()`: replace `-backend-config=path=<file>` with the HTTP backend
  config, built per `(release, stage, phase)`. The state path keeps
  today's shape so the seeded files line up:

  ```
  state = f"helm-charts/{cluster}/{chart_dir}/{stage}/{phase}.tfstate"
  url   = ("http://127.0.0.1:6061/?type=git"
           "&repository=https://github.com/pvginkel/TerraformState"
           "&ref=main&state=" + urlencode(state))
  terraform -chdir=<work> init -input=false -reconfigure \
      -backend-config=address=<url> \
      -backend-config=lock_address=<url> \
      -backend-config=unlock_address=<url>
  ```

  Repository + ref are constants (or env overrides
  `DEPLOY_STATE_REPO_URL` / `_REF`); `DEPLOY_STATE_REPO` (the old
  checkout path) is removed.
- The CLI no longer needs `git` or a TerraformState checkout to exist —
  drop the "checkout not found" guard. It **does** now need the backend
  daemon reachable on `127.0.0.1:6061`; add a fast preflight (socket
  probe) that fails with a clear "start terraform-backend-git first"
  message, the same UX as Ansible.
- Update `tools/deploy/README.md` and the `_providers/providers.tf`
  header comment (both currently describe the TerraformState-checkout
  mechanism).

### 1b. Seed existing prd state into the backend (one-time, operator)

The good news: the migration already wrote every state file into the
operator's `../TerraformState` checkout at exactly the paths the new
backend will request — `helm-charts/<cluster>/<chart>/<stage>/<phase>.tfstate`
(55 files, locally committed, **~129 commits ahead of `origin/main`**,
plaintext). The CLI's `state=` query param mirrors that layout verbatim,
so nothing needs moving. **The same `pvginkel/TerraformState` repo is
used** — `helm-charts/` lives alongside Ansible's `prd/`+`scratch/`.

What's left is the encryption + push the operator does by hand, the same
way the Ansible `prd/`+`scratch/` state was seeded:

1. **sops-encrypt each `helm-charts/**/*.tfstate` in place**, to the same
   age recipient the backend uses (`TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS`),
   matching the per-value `ENC[AES256_GCM,...]` shape Ansible's files
   already have — so the daemon (holding `SOPS_AGE_KEY`) can decrypt them.
2. Reconcile with `origin/main` (the backend has been pushing Ansible
   state there, so the local checkout has diverged) and push.
3. Verify: with the backend daemon up, `poetry run deploy plan
   prd/<chart>` reads the encrypted state and plans a **no-op** (or only
   expected drift) for several sampled releases — proving the state
   path + decrypt path line up before the pipeline touches prod.

### 1c. IaCAgent — make `iac-impl` clone HelmCharts too

`IaCAgent/bin/iac-impl` hardcodes `ANSIBLE_REPO_PATH` and clones only
`pvginkel/Ansible` into `/work/Ansible`. Generalize to clone a
**configurable set of repos** into `/work/<name>` (e.g. a `repos:` list
in `secrets.yaml`, defaulting to Ansible so nothing breaks). Add
`pvginkel/HelmCharts` so the deploy script can `cd /work/HelmCharts`.
`install.sh` re-materializes `iac-impl` on `srviac`.

### 1d. Ansible iac image — poetry at runtime for the deploy CLI

The iac image (`Ansible/support/iac-image/Dockerfile`) already carries
helm 4, kubectl, terraform, `librados2`/`librbd1`, and the baked homelab
provider — everything the HelmCharts TF + helm steps need. Two gaps:

- **poetry on PATH in the final stage.** The deploy CLI is its own poetry
  project; the established pattern (today's Jenkinsfile) is a runtime
  `poetry install` in the repo. The build stage installs poetry but the
  final stage only copies Ansible's `/app/.venv`. Add poetry to the final
  image (pipx/pip `--break-system-packages`) so
  `cd /work/HelmCharts && poetry install` works.
- Confirm `srviac` has network reach to: prd k8s apiserver VIP, prod Ceph
  mons (192.168.188.24-26), RGW (`ceph:7480`), the `iac-provisioner`
  hostPort 9655 on srvk8s1, and `registry:5000` (digest resolution).
  These are new egress paths for `srviac`; verify before the first run.

### 1e. Ansible `secrets.yaml` — kubeconfig + HOMELAB_* for prd

The deploy needs cluster + storage credentials into the iac container's
environment, exactly the way `scripts/setup-env.sh` exports them for a
manual run — and `secrets.yaml` is precisely the mechanism that loads
env from OpenBao at container startup. Check
`IaCAgent/etc/iac/secrets.example.yaml`: the
`terraform-backend-git` plumbing the HTTP backend needs (`GIT_USERNAME`,
`GIT_API_TOKEN`→`GITHUB_TOKEN`, `TF_BACKEND_HTTP_ENCRYPTION_PROVIDER`,
`TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS`, `SOPS_AGE_KEY`) is **already
there**, shared with Ansible — nothing to add for state. What's net-new
is only the deploy's own credentials. Add to `secrets.example.yaml` (and
the operator's real `srviac:/etc/iac/secrets.yaml`):

- The three `setup-env.sh` leaves, as `env:` `!bao` entries — the same
  `kv/shared/prd/...` / `kv/eso/prd/...` paths `setup-env.sh` reads:
  - `HOMELAB_CEPH_USER` ← `!bao kv/shared/prd/ceph-csi#user_id`
  - `HOMELAB_CEPH_KEY` ← `!bao kv/shared/prd/ceph-csi#user_key`
  - `HOMELAB_S3_ADMIN_ACCESS_KEY` ← `!bao kv/shared/prd/ceph-rgw/s3#access_key_id`
  - `HOMELAB_S3_ADMIN_SECRET_KEY` ← `!bao kv/shared/prd/ceph-rgw/s3#secret_access_key`
  - `HOMELAB_ZFS_PROVISIONER_TOKEN` ← `!bao kv/eso/prd/iac-provisioner/api/token#token`

  (iac is prd-only, so the bare `HOMELAB_*` names are correct — no need
  for the CLI's `HOMELAB_<CLUSTER>_*` re-export.) The non-secret
  per-cluster config (`HOMELAB_CEPH_MON_HOST`, `_POOL`, `_S3_ENDPOINT`)
  still comes from `_providers/clusters.yaml` via the CLI, not here.
- A **prd kubeconfig** as a `files:` entry (`!bao` content, `mode
  "0600"`) granting what the deploy does today: helm install, `kubectl
  apply`, `rollout status`, Released-PV `claimRef` clearing (cluster-scoped
  PV edits ⇒ effectively cluster-admin). The deploy script exports
  `KUBE_CONFIG_PATH` at that path (the CLI already honors it).
- Extend the iac-agent OpenBao AppRole policy
  (`openbao_iac_agent_kv_paths` in
  `Ansible/inventories/prd/group_vars/openbao.yml`) to grant read on the
  three leaves + the kubeconfig leaf; re-apply the policy. (Today the
  iac-agent role can read `kv/iac/*` but not `kv/shared/prd/*` /
  `kv/eso/prd/*`, so the refs would hard-fail at startup without this.)

### 1f. HelmCharts `Jenkinsfile` — rewrite on the iac pattern

**Not the whole pipeline runs through iac** — only the collection step
and the deploy commands do. Everything else (the stage scaffolding, the
target-state diff gate) stays in the pipeline on the `iac-controller`
agent, exactly as today's `Jenkinsfile` already structures it. So the
`utils.hasChanges()` change-detection keeps working unchanged: it reads
the **build's SCM changeset** in groovy on the agent, which has nothing
to do with the fresh clone iac makes in `/work`. (That removes the
earlier worry about "no changeset inside iac" — change detection never
moves into iac.)

Replace the in-cluster `podTemplate` + self-pushed TerraformState with the
`Jenkinsfile.iac-on-push` shape:

- `agent { label 'iac-controller' }`, `disableConcurrentBuilds()`.
- **Collection in iac:** the `resolve-helm-args.py` discovery (full list)
  and the per-release digest `--set` args run via `iac -c 'cd
  /work/HelmCharts && poetry install … && poetry run resolve-helm-args …'`,
  captured back with `returnStdout` (iac logs go to stderr, so stdout is
  clean JSON / args). iac is where the repo clone + poetry env live.
- **Change detection on the agent:** the existing `changed(entry)` /
  `disabled` groovy logic (`utils.hasChanges("charts/…", "configs/prd/…",
  …)`) runs in the pipeline, unchanged — the per-release diff gate is
  preserved.
- **Deploy in iac:** `poetry run deploy <release> … <args> && poetry run
  deploy wait …` run via `iac -c`. Group the changed releases into one
  `iac -c` so the IaC mutex is held across the TF-touching work (the
  user's stated reason for iac — serialize TF activity against Ansible's);
  the un-touched releases were already filtered out on the agent.
- Drop the "Pushing TF state" stage entirely (the backend owns it) and
  the `DEPLOY_STATE_REPO` / TerraformState clone stage.
- Failure notification via `send_message.py` like the Ansible pipeline.
- Open: does this Jenkinsfile stay in the HelmCharts repo (job SCM =
  HelmCharts, triggered by GitHub push) or move under
  `IaCAgent/jenkins/` like the Ansible one? Operator's call at job-config
  time.

### 1g. Operator / manual-run ergonomics

Manual `poetry run deploy` now needs the backend daemon up locally.
Add a HelmCharts equivalent of `Ansible/scripts/tf-backend.sh` (start
`terraform-backend-git` on `127.0.0.1:6061` with the sops+age + GitHub
creds from OpenBao), and update `scripts/setup-env.sh` / the CLI README so
the documented manual flow is: start the backend → `. setup-env.sh prd` →
`poetry run deploy …`. The `CLAUDE.md` "deploy CLI" + "Storage" sections
that reference the TerraformState checkout need the same correction.

### 1h. Re-enable the pipeline

After 1b's no-op plan is green and a manual `poetry run deploy
prd/<small-release>` through the daemon succeeds, the operator re-enables
the HelmCharts Jenkins job and confirms a clean target-state run.

## Phase 2 — `tools/` folder rework (poetry-native) — ✅ DONE (option B)

`tools/` is half-mature: the deploy CLI is a proper poetry package
(`tools/deploy/deploy_cli`, console scripts in the root `pyproject.toml`,
invoked `poetry run deploy`), but everything else is loose scripts run as
`python tools/<x>.py` against a second, separate dependency set
(`tools/requirements.txt`, which even lists `requests` twice). The result
is the wart the operator called out — two install paths and two
invocation styles (`poetry run …` vs `python tools/…py`) for one repo.
Now that the iac image does `poetry install` anyway, unify on poetry.

Current inventory:

- **Poetry already:** `deploy_cli` (deploy/template/stop/uninstall/destroy).
- **Loose scripts, our code:** `resolve-helm-args.py` (Jenkinsfile),
  `gen-architecture.py` (Jenkinsfile.architecture),
  `recommend-resources.py` (operator; needs numpy + kubernetes +
  prometheus), `collect-version-dependencies.py` (run **by the
  version-poller container**, see below), `edit-base64.py` (operator).
- **Shared modules:** `utils.py` (`ImageName`), `k8s.py`, `prometheus.py`.
- **External-contract script:** `resolve-image-tag.py` — its `_get_digest`
  is deliberately **kept in sync** with
  `DockerImages/version-poller/app/registry_checker.py`; it's imported by
  `resolve-helm-args.py` and runnable standalone.

### Proposals (operator picks one)

**A — one package, console scripts for everything (recommended).** Fold
the loose scripts into the existing poetry project as modules of one
package (e.g. promote `deploy_cli` to a broader `helmtools` package, or
add a sibling `chart_tools`), each exposed as a `[project.scripts]` entry:
`resolve-helm-args`, `gen-architecture`, `recommend-resources`,
`collect-versions`, `edit-base64`. Shared `utils`/`k8s`/`prometheus`
become normal package imports (no more `sys.path` sibling tricks). Delete
`tools/requirements.txt`; all deps move into `pyproject.toml`. Replace
every `python tools/<x>.py` with `poetry run <name>` (Jenkinsfile,
Jenkinsfile.architecture, CLAUDE.md, the version-poller config). One
install (`poetry install`), one invocation style.

**B — A, but with dependency groups so the deploy stays lean.** The
deploy CLI ships in the iac image and only needs `pyyaml`;
`recommend-resources` drags in numpy + kubernetes + prometheus. Split
deps into a default group (deploy/resolve/architecture) and an optional
`analysis` group (recommend-resources), so the iac image runs
`poetry install --only main` and the heavyweight analysis deps install
only where that tool actually runs. Same console-script unification as A.

**C — minimal.** Keep files roughly in place; just add `[project.scripts]`
wrappers + fold `requirements.txt` into pyproject so `python tools/…py`
disappears, without the module reorganization. Lowest effort, least
"pretty."

Recommendation: **B** — it's A's cleanliness plus the lean deploy image
the iac move (Phase 1d) makes us care about.

### Cross-repo contracts to honor (any option)

- **`resolve-image-tag.py` keep-in-sync** with the DockerImages
  `registry_checker.py` `_get_digest`: moving/renaming the module is fine,
  but the "Keep in sync" marker + the logic must survive, and the
  CLAUDE.md note that documents the contract gets updated to the new path.
- **`collect-version-dependencies.py` is invoked by the version-poller**
  (DockerImages `charts/version-poller/files/config.yaml`,
  `helm_charts.script`), which clones this repo and runs the configured
  command. If invocation moves to `poetry run collect-versions`, the
  poller's clone step needs poetry + a `poetry install` (its container is
  lightweight today). **Decision:** either (a) update the poller config +
  poller image to `poetry install && poetry run collect-versions`, or
  (b) keep a no-poetry entry path (`python -m …` runnable without an
  install) for that one tool. Resolve before changing the invocation;
  the poller breaking silently stops drift detection.
- `gen-architecture.py` renders releases **through** `poetry run deploy
  template`; it must remain in the same project so that call resolves.

Land this **before** the Jenkinsfile rewrite (1f) so the pipeline is
written once against the final invocation style. Also drop the stray
`tools/.venv` + `__pycache__` from the working tree and confirm
`tools/.gitignore` covers them.

## Phase 3 — old-world Ceph / S3 / cephx cleanup — ✅ DONE (bar §5 OpenBao)

> **DONE (2026-06-14)**, except the manual OpenBao god-leaf retirement
> (last bullet). Executed via `tools/migrate/phase3-cleanup.sh` (HelmCharts
> commits `d7fa4c3`, `141f91e`) — a dry-run-by-default, idempotent runbook
> pinned to the Phase-4 audit that drives srvceph1 + srvk8s1 over SSH. What
> landed against prd, all verified afterwards (k8s storage intact: 24 RBD,
> 26 CephFS, 95 workloads; keepers `client.k8s` / RGW `k8s`+`dashboard` /
> 6 canonical buckets all present):
>
> - Deleted the empty `ceph-csi-rbd` + `ceph-csi-cephfs` namespaces.
> - Deleted the 4 old cephx users `client.csi-{rbd,cephfs}-{dev,prd}`.
> - Deleted the `csi-prd` + `csi-dev` CephFS subvolume groups **and** RBD
>   pools wholesale (`mon_allow_pool_delete` was operator-enabled).
> - Deleted the 19 stale S3 buckets + the legacy owner user
>   `electronics-inventory-dev`.
>
> **Legacy-subvolume gotcha (worth knowing):** many old csi-prd/csi-dev
> subvolumes store their data in the legacy PARENT dir
> (`/volumes/<group>/<name>`) while their `.meta` points at a UUID subdir
> that never existed. `ceph fs subvolume rm` then returns `ENOENT: mount
> path missing` and `--force` silently no-ops. The script falls back to
> `rm -rf` via a scoped `/volumes/<group>` admin cephfs mount on srvk8s1
> (so `/volumes/k8s` is unreachable through it). Spot-checked `jenkins`
> before bulk delete: the old copy was the frozen pre-migration source;
> the live `jenkins-prd-home` had diverged forward — confirmed safe.
>
> **Still TODO — Phase 3 §5 (manual, operator):** delete the live OpenBao
> secret `kv/shared/ceph-rgw/s3` (the cluster-agnostic god leaf). No
> Ansible policy edit needed (`group_vars/openbao.yml` already grants only
> the per-cluster `shared/prd/...` leaves). Just `bao kv metadata delete
> kv/shared/ceph-rgw/s3`. Not done here — no `bao` access from the work box.

The checklist `migrate-release.py` prints once the plan is exhausted.
Operator-run on the prod Ceph admin host; gate every deletion on the
orphan audit in Phase 4 first.

- Delete the kept old ceph-csi namespaces `ceph-csi-rbd` and
  `ceph-csi-cephfs` (kept through the migration because not-yet-migrated
  PVs referenced their driver secret via `nodeStageSecretRef`; now nothing
  does).
- Delete the old area-specific cephx users: the prod `csi-rbd-*` /
  `csi-cephfs-*` and the dev `csi-rbd-dev` / `csi-cephfs-dev` — the
  combined `client.k8s` replaced them on both clusters.
- **`csi-prd` and `csi-dev` are fully deletable** (operator confirmed).
  After the audit shows nothing references them: delete the `csi-prd` RBD
  pool + its CephFS subvolume group + contents, and the `csi-dev` pool +
  subvolume group + contents. Everything live now lives under pool/group
  `k8s`.
- **S3 (operator unsure — audit decides):** the migration copied prod
  buckets into fresh canonical buckets owned by per-release scoped users.
  The **old source buckets** and the **god RGW user** are now orphaned.
  After the audit lists `radosgw-admin bucket list` / `user list` and the
  operator confirms which buckets are the stale originals (and the six
  dev/validation buckets on prod RGW named in the parent slice), delete
  them and `radosgw-admin user rm` the god user.
- Retire OpenBao `kv/shared/ceph-rgw/s3` (the cluster-agnostic god leaf)
  and its `eso`/`jenkins`/`iac` consumer grants
  (Ansible `group_vars/openbao.yml`); re-apply the policy. The
  per-cluster `kv/shared/<env>/ceph-rgw/s3` leaves stay.

## Phase 4 — full prd cluster scan / orphan audit — ✅ DONE

> **DONE (2026-06-14).** Built `poetry run audit-prd-orphans` (HelmCharts
> `chart_tools/audit_prd_orphans.py`, commit `4418fd1`): derives desired
> state from `configs/prd` and diffs it against live cluster/Ceph
> enumerations (`desired` / `collect` / `diff` verbs). Ran it against prd
> (SSH to srvceph1 = Ceph admin, srvk8s1 = microk8s + zpool2). **Desired
> state is 100% realized**: RBD pool `k8s` 24/24, CephFS group `k8s`
> 26/26, helm releases 43/43, all 52 PV claimRefs clean, the 6 canonical
> S3 buckets present and correctly owned by their scoped users. Orphans
> found were exactly the old-world objects → handed to Phase 3. Operator
> dispositions confirmed during the audit: **keep** RGW user `k8s` (the TF
> bucket-creating admin), RGW user `dashboard` (Ceph Dashboard), and the
> `development` namespace (holds only a `claude-code-token` SA). The S3
> "god user" that owned the 19 stale buckets is `electronics-inventory-dev`
> (not `k8s`). `zpool2/share` first looked like an orphan but is the data
> the storage chart's Samba serves — fixed by the storage delta above
> (now a managed dataset), so it is no longer an orphan.

A deliberate sweep for anything the per-release migration missed. The
desired-state inventory is the parent slice's "Storage inventory" lists +
the 45 `configs/prd` releases. Anything on the cluster **not** in desired
state is an orphan candidate the operator reviews.

Ceph / storage (prod Ceph admin host + the zpool2 node):

```sh
rbd ls k8s; rbd ls csi-prd; rbd ls csi-dev
ceph fs subvolume ls cephfs k8s
ceph fs subvolume ls cephfs csi-prd; ceph fs subvolume ls cephfs csi-dev
radosgw-admin bucket list; radosgw-admin user list
zfs list -r -o name,quota,mountpoint zpool2
```

Kubernetes (prd context) — look for old-world leftovers:

- Released / orphaned PVs whose `claimRef` points at a now-deleted old
  namespace (the migration created fresh PVs; the old ones were deleted
  per release, but confirm none lingered).
- Any namespace **not** of the form `<chart>-prd` / `<chart>-<stage>`
  (i.e. a surviving old flat namespace) — there should be none.
- Helm releases in unexpected namespaces (`helm ls -A`); every release
  should be `<chart>-<stage>` and present in `configs/prd`.
- Stale ESO `ClusterSecretStore`/`ExternalSecret` or finalizer-stuck
  resources from the ESO migration window.
- Cross-check `kubectl get deploy,sts,ds -A` against the 45 releases:
  every workload healthy, none missing, none extra.

Diff each enumeration against desired state; the operator deletes
confirmed orphans. Retain + the completed imports mean nothing in the
desired set is at risk. The csi-prd/csi-dev pool deletions in Phase 3
happen **after** this audit is clean.

## Phase 5 — delete the migration software — ❌ CANCELLED

> **CANCELLED (2026-06-14).** The migration tooling is **kept**, not
> deleted. The operator decided to retain `tools/migrate-release.py` +
> `tools/migrate/` — especially the old→new name mapping in the
> `*-plan.yaml` files — as the starting point for a possible future bulk
> rename of all durable resources to the `<namespace>-<short>` convention
> (the deferred per-chart rework in HelmCharts `CLAUDE.md`). The folder's
> intermediate per-run state (`*-done.txt`) was removed and its `README.md`
> now documents the completed status + retention rationale. The original
> removal plan is left below for the record.

Once Phases 3–4 confirm the cutover is fully settled, remove the
forward-only migration machinery (operator confirmed it can go entirely):

- `tools/migrate-release.py`
- `tools/migrate/` (`prd-plan.yaml`, `dev-plan.yaml`, `*-done.txt`,
  `README.md`)
- The `CLAUDE.md` references to `tools/migrate-release.py` /
  `tools/migrate/` (repo-layout + tools sections).
- Any now-dead operator scripts the migration leaned on that nothing else
  uses — keep `scripts/setup-env.sh`, `make-ceph-csi-user.sh`, and the
  `mount-*`/`rm-*` inspection helpers (still useful); only drop
  migration-only code.

## Phase 6 — TODO.md follow-ups — ✅ DONE

> **DONE (2026-06-14).** (1) The provider fix shipped: the static
> `recordsize`/`compression` defaults were dropped (`pvginkel/homelab`
> `0.1.25`, published + deployed), so imported datasets stop diffing;
> `atime=off` is now declared explicitly on the three hostPath datasets
> (storage `rclone-backup` + `share`, media `downloads`). (2) The static-PV
> stage-suffix sweep is **not** done as a mass rename — instead the naming
> convention and a per-chart rework plan (with effort + blast radius) are
> documented in HelmCharts `CLAUDE.md` (Storage section); single-stage
> charts get converted to `<namespace>-<short>` only when they first need a
> second stage. `TODO.md` is closed. Residual operator runtime: apply the
> 6.1 change (`deploy apply prd/media`; `deploy import` + `apply
> prd/storage`); optionally `zfs inherit recordsize zpool2/rclone-backup`.

Both items in `HelmCharts-2/TODO.md`, neither blocking but both deferred
through the migration:

1. **`homelab_zfs_dataset` recordsize/compression defaults break imports.**
   Cross-repo provider fix in
   `HomelabTerraformProvider/internal/zfsdataset/resource.go`: drop the
   static `Default("128K")` / `Default("lz4")` so the attributes are
   `Optional + Computed` only, matching the agent's "unset reads back
   empty" contract. Build + publish the provider, rebuild the iac image to
   pick up the new binary, then drop the `zfs set recordsize=128K`
   workaround applied during the migration (and decide whether
   `atime=off` should be re-added under the dataset `properties` in
   `configs/prd/storage/_shared/infrastructure.tf`).
2. **Static-PV base names aren't stage-suffixed on single-stage charts.**
   One sweep across every single-stage chart: fold `var.namespace` into
   the static-PV module `name` (the way design-assistant does) so PV/PVC
   become `<namespace>-<short>-pv`/`-pvc`, updating the chart-side
   `ceph.rbd-pvc`/`ceph.cephfs-pvc` base, `claim_name` overrides, and
   hardcoded PV names in `post-render.sh` (e.g. grafana's
   `VOLUME_NAME=grafana-pv`). Re-check `fullnameOverride` interactions
   (grafana). Pure rename ⇒ destroy+recreate of PV/PVC, so it rides a
   per-chart deploy window like any storage rename; sequence it as a
   normal pipeline change, not a flag day.

## Open decisions

> **All resolved.** Jenkinsfile stays in HelmCharts; `repos:` list in
> secrets.yaml; tools = option B; version-poller keeps a no-install entry
> path. **S3 orphan scope (was the last open one) is now resolved**: the
> Phase-4 audit showed all 19 stale buckets owned by the legacy user
> `electronics-inventory-dev` (deleted in Phase 3); the canonical 6
> buckets + their scoped users and the RGW admin `k8s` are the keepers.

- **Jenkinsfile home (1f).** Keep in HelmCharts (SCM-triggered) or move
  under `IaCAgent/jenkins/` like Ansible's. Recommendation: keep in
  HelmCharts — it's HelmCharts' deploy, and the job already exists there.
- **iac-impl multi-repo shape (1c).** `repos:` list in `secrets.yaml` vs.
  a fixed two-repo clone vs. a per-invocation repo arg. Recommendation:
  `repos:` list, default `[Ansible]`, so the mechanism is general and
  Ansible's behavior is unchanged.
- **S3 orphan scope (Phase 3).** ✅ Resolved by the Phase-4 audit: 19
  stale buckets owned by `electronics-inventory-dev` (deleted); canonical
  6 + scoped users + RGW admin `k8s` kept.
- **`tools/` rework option (Phase 2).** A / B / C above; recommendation B.
- **version-poller invocation (Phase 2).** Poller switches to `poetry
  run`, or `collect-versions` keeps a no-install entry path.

## Verification

1. **Backend cutover:** with the daemon up, `poetry run deploy plan
   prd/<chart>` against seeded state is a no-op for several sampled
   releases (proves 1a + 1b).
2. **Manual deploy via daemon:** `. setup-env.sh prd` + start backend +
   `poetry run deploy prd/<small-release>` succeeds, state round-trips
   through `pvginkel/TerraformState` (encrypted), reattaches PVs.
3. **iac end-to-end:** `iac -c 'cd /work/HelmCharts && poetry install &&
   poetry run deploy prd/<release>'` succeeds on `srviac` — kubeconfig +
   HOMELAB_* resolved from `secrets.yaml`, backend serving state, helm +
   TF both green.
4. **Pipeline:** the re-enabled job runs a clean target-state sweep; a
   no-op push deploys nothing; a one-line values change deploys exactly
   that release; a `disabled: true` flip uninstalls and never destroys.
5. **tools rework:** one `poetry install` provides every tool; no
   `python tools/<x>.py` remains in Jenkinsfile / Jenkinsfile.architecture
   / CLAUDE.md / the version-poller config; `resolve-helm-args` discovery
   and a `gen-architecture` run both work via `poetry run`.
6. **Cleanup audited:** Phase-4 enumerations diff cleanly against desired
   state; Phase-3 deletions leave every live release healthy (re-run the
   `kubectl get deploy,sts,ds -A` cross-check after).
7. **Migration software gone:** `tools/migrate*` removed, `CLAUDE.md`
   clean, full release discovery + a template render of all 45 releases
   still green.
8. **TODO fixes:** an imported ZFS dataset plans no-op without the
   `recordsize` workaround (after the provider publish); a second stage of
   a formerly-single-stage chart templates without PV/PVC name collisions.

## Access / prerequisites

- **srviac**: the new egress paths in 1d; `secrets.yaml` edits + OpenBao
  AppRole grant (1e); `install.sh` re-run after the IaCAgent change (1c).
- **prod Ceph admin** (srvceph1-3): the Phase-4 audit enumeration and the
  Phase-3 pool/group/user/bucket deletions.
- **prd kube context**: the Phase-4 k8s sweep.
- **OpenBao** (operator-mediated): the new iac-agent grants (1e), and the
  god-leaf retirement (Phase 3).
- **Repos (write)**: HelmCharts (CLI, Jenkinsfile, tools, scripts, TODO),
  IaCAgent (iac-impl), Ansible (iac image, secrets example, openbao.yml),
  DockerImages (version-poller config, Phase 2),
  HomelabTerraformProvider (Phase 6.1), `pvginkel/TerraformState` (1b
  seed).
