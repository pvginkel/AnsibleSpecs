# Slice 013 — the `iac` image stops rebuilding on every Ansible push, and the IaCAgent repo becomes `support/iac-agent/` in this repo

## Requirements / rulings

Numbered requirements are `slice.md`'s, in the source's words. Rulings are the operator's, from
the 2026-08-13 refinement session; a ruling that contradicts a requirement's wording governs.

#### Pillar A — scope the `iac-image` rebuild

- **R1.** Stop `iac-image` rebuilding on pushes that cannot change the image.

  > **P2 — the rebuild flood.** `iac-image` rebuilds on *every* Ansible push, but its real inputs
  > change on a tiny fraction of them: `support/iac-image/**`, the root
  > `pyproject.toml`/`poetry.lock` baked into the image,
  > `ansible/roles/baseline/files/homelab-root.crt`, `ansible/files/known_hosts.d/homelab`, and
  > the provider binary. Everything else (roles, playbooks, host_vars, Terraform `.tf`) rebuilds
  > the image for nothing.

- **R2.** Gate inside the pipeline rather than changing the job's trigger.

  > Add the `hasChanges` gate; leave the push trigger but make the build a no-op when no image
  > input changed. Verify an unrelated Ansible push skips the image build.

  The pattern to follow is the one HelmCharts and DockerImages already use — `utils.hasChanges(...)`
  guarding the build, `Utils.markStageSkippedForConditional(<stage name>)` in the else branch.

- **Ruling (2026-08-13) — the provider is no longer an input.** R1's list was written before
  `tf-provider-registry` landed and the slice flagged it as unverified. Verified this session: the
  provider bake is gone from the image, so the provider drops off the input list. The rest of R1's
  list is still accurate. Establishing the authoritative input set from the Dockerfile as it stands
  is the plan's work, not R1's list taken on faith.

- **Ruling (2026-08-13) — gate only, no escape hatch.**

  > Simplest change, matches HelmCharts exactly. To force a rebuild you replay the job from a
  > commit that touched an input, or push a trivial change to `support/iac-image/`.

  Raised and declined: a `FORCE` build parameter on the DockerImages precedent. `utils.hasChanges`
  reads the build's own SCM changeset, which means a build that fails on an image-input push is not
  retried by the next unrelated push. The operator accepts that hole.

- **Ruling (2026-08-13) — the `hasChanges` contract is verified, and patterns must full-match.**
  The shared library is not checked out in this environment but is readable through the gitblit
  mirror; `pvginkel/JenkinsPipelineUtils.git`, `vars/utils.groovy:33-41`:

  ```groovy
  def hasChanges(pattern) {
      return currentBuild.changeSets.any { changeSet ->
          changeSet.items.any { item ->
              item.affectedFiles.any { it.path ==~ pattern }
          }
      }
  }
  ```

  Two consequences the plan must carry rather than infer. The source is `currentBuild.changeSets`
  — the build's own changeset — which is what makes the accepted retry hole above real. And `==~`
  is Groovy's **full-match** operator, not a find: a pattern must match the entire repo-relative
  path. That is why `HelmCharts/Jenkinsfile:95-98` and `DockerImages/Jenkinsfile:46` both carry a
  trailing `/.*`. A glob-shaped pattern (`support/iac-image/**`) or a bare prefix
  (`support/iac-image`) full-matches nothing, which would make `iac-image` skip *every* build
  including real image-input pushes.

#### Pillar B — merge `IaCAgent` into `Ansible`

- **R3.** Fold the IaCAgent tree into the Ansible repo and make the `iac_agent` role read it in
  place.

  > What remains (`bin/`, `systemd/`, `install.sh`) is srviac host-glue that the `iac_agent` role
  > **already rsyncs from a sibling checkout** (`ansible/roles/iac_agent/defaults/main.yml`:
  > `iac_agent_local_checkout: {{ playbook_dir }}/../../../IaCAgent`). The split costs: a separate
  > repo + push for any helper edit; a sibling-checkout requirement a CI `iac` clone doesn't
  > satisfy; and doc drift (README still says `iac` runs `modern-app-dev`, but `bin/iac` runs
  > `registry:5000/iac:latest`). […] repoint `iac_agent_local_checkout` at the in-repo path, and
  > the role becomes CI-applyable and single-source.

- **Ruling (2026-08-13) — the tree lands at `support/iac-agent/`.** Sibling of the existing
  `support/iac-image/`.

  > `support/` is already the repo's home for host/build assets that aren't roles or Terraform, so
  > this needs no new convention and keeps the tree visible as its own deliverable.

  Considered and not taken: `ansible/roles/iac_agent/files/` and a top-level `iac/`, both offered
  by the change request.

- **R4.** Do the surrounding edits the move implies.

  > Move the tree […]; repoint `iac_agent_local_checkout`; fix the README drift; update
  > install/sync paths.

- **Ruling (2026-08-13) — R4's README fix ships in this slice, and reads "the drift" broadly.**
  R4 is a numbered requirement; a phase must own it. It is **not** the doc phase's — that phase's
  charter (`docs/slice-doc-plan.md`) reaches `decisions.md`, `docs/runbooks/`, the specs README,
  role/module interface docs and `CLAUDE.md`, none of which is a tree README under `support/`.

  > FIX: `modern-app-dev` → `registry:5000/iac:latest` and the "separate repo" framing → lives in
  > Ansible at `support/iac-agent/`; the stale Jenkinsfile list (drop
  > `Jenkinsfile.iac-dqlite-watchdog`, which does not exist; add `iac-apply`,
  > `iac-scheduled-calico`, `iac-scheduled-certs`); the bind-mount list (names 2, `bin/iac` mounts
  > 5); plus the stale `modern-app-dev` mentions in `etc/cron.d/iac-prune:3-4` and
  > `bin/send_message.py:8`.
  >
  > → `grep modern-app-dev support/iac-agent/` returns nothing.

  This supersedes any reading of the move's byte-identical property as forbidding the edits: the
  tree moves byte-identical **first**, so the history-preserving move stays a reviewable pure
  rename, and the drift fixes land as a separate, separately-reviewable change on top. A criterion
  asserting byte-identity must be scoped to the move, not to slice end.

- **R5.** Preserve the IaCAgent commit history in the move.

- **R6.** Prove parity, then retire the repo.

  > Apply `iac_agent` once from the operator workstation to prove parity, then archive
  > `pvginkel/IaCAgent`.

- **Ruling (2026-08-13) — the slice stops before `.kubecoder/config.yaml`.** R6's two steps are
  the operator's keystroke, not the run loop's, and the slice must not remove the fallback before
  parity is proven.

  > IN SLICE: move tree (history preserved); repoint `iac_agent_local_checkout`; fix README drift
  > + runbook paths; prepare the parity-apply command.
  >
  > OPERATOR-OWED, recorded in the slice: the parity apply; remove the repo from
  > `.kubecoder/config.yaml`; archive `pvginkel/IaCAgent` on GitHub.

  So: `.kubecoder/config.yaml` keeps declaring IaCAgent and `/work/IaCAgent` stays on disk when
  the slice finishes. What the slice owes the operator is the exact parity-apply command, recorded
  where they will find it.

- **R7.** Follow the removed repo boundary through the docs and the model.

  > **Update decisions.md** if the IaCAgent location becomes doctrine, and nudge the
  > `update-architecture` agent (removed repo boundary).

#### Rulings that bound both pillars

- **Ruling (2026-08-13) — no criterion may assert a doc-truth universal.** An acceptance criterion
  of the form "no doc still says X" is unbounded and, here, wrong: because the slice deliberately
  leaves `.kubecoder/config.yaml` declaring IaCAgent and `/work/IaCAgent` on disk (the R6 ruling),
  `CLAUDE.md`'s "Related repos on this machine … `IaCAgent`" is **still accurate** at slice end.
  The specs repo also holds historical records naming IaCAgent — completed slices, the 2026-07
  review findings — which are provenance and must not be rewritten. Criteria about prose are
  bounded to the files the slice's own diff touches, and say which.

- **Ruling (2026-08-13) — both `--limit "!iac_agent"` exclusions stay untouched.** The slice's N1
  named only `Jenkinsfile.iac-apply`; the exclusion is in fact in two files.

  > Reads N1 as being about the role, not the specific job: CI neither applies nor drift-checks
  > `iac_agent`. Slice touches neither line.

  Both `Jenkinsfile.iac-apply` (the `site.yml` stage) and `Jenkinsfile.iac-scheduled-drift` (the
  daily drift check) keep theirs.

- **Ruling (2026-08-13) — the existing duplicates are out of scope.** The merge puts two
  pre-existing duplicate pairs in one repo: `tools/ai_workflow/send_message.py` against the tree's
  `bin/send_message.py`, and the `iac_agent` role's inline `/etc/docker/daemon.json` content
  against the tree's `etc/docker/daemon.json`.

  > Neither duplicate is a requirement in `slice.md`. The merge makes them visible; fixing them is
  > separate work. Keeps this slice a move plus a repoint, which is what makes the diff reviewable.

  Move only — all four files keep their current content and location.

## Ordering constraints

- **The two pillars are independent** — the change request says so ("the two pillars are
  independent; do either first") and nothing found this session contradicts it. They share no
  file: Pillar A is `Jenkinsfile.iac-image`, Pillar B is the tree, the role and the docs.

- **Ruling (2026-08-13) — 013 does not wait for `tf_safety_rails` (#127).** The change request said
  "the safety rails land first". #127 is still an untriaged intake card, and it edits
  `bin/check-protected-vms.sh` — a file this slice relocates but does not otherwise touch.

  > Same treatment you already gave #327 and #506: leave it queued, rebase onto the new path
  > afterwards. The rebase is mechanical — one file moves, its content is untouched by this slice.
  > Nothing blocks 013.

  Also considered and not taken: waiting for #127, and splitting Pillar A out to ship ahead of the
  merge (which would have reversed triage Q1's single-bundle decision).

### PA — `iac-image` builds only when an image input changed

Target: root

An Ansible push whose changeset touches nothing the image is built from leaves
`registry:5000/iac` alone: the build stage reports *skipped for conditional*, and no tag is
pushed. A push that does touch an image input builds and pushes exactly as it does today — same
Dockerfile, same context, same two tags (`Jenkinsfile.iac-image:8-15`). The job's push trigger is
not touched; the gate lives inside the pipeline (R2).

**The image's inputs, established from the Dockerfile as it stands this pass** — the ruling asks
for this set to be verified rather than inherited from R1's wording:

- `support/iac-image/**` — the Dockerfile itself (`Jenkinsfile.iac-image:11`),
  `smallstep.sources` (`support/iac-image/Dockerfile:85`), `terraform.rc` (`:121`)
- the root `pyproject.toml` and `poetry.lock` (`support/iac-image/Dockerfile:11`)
- `ansible/roles/baseline/files/homelab-root.crt` (`:72`)
- `ansible/files/known_hosts.d/homelab` (`:142`)

Nothing else in the repo reaches the image: the only other `COPY`s come from the build stage
(`:25`) and from a pinned external image (`:129`). The provider is not an input —
`support/iac-image/terraform.rc:1-9` resolves `registry.terraform.io/pvginkel/*` from the
`tfmirror.home` network mirror, so there is no filesystem-mirror bake and no `copyArtifacts` left
to watch. That confirms the ruling. The set matters beyond build time: `iac-impl` warns at runtime
when the cloned `Ansible/poetry.lock` differs from the one baked into the image
(`/work/IaCAgent/bin/iac-impl:388-409`, `support/iac-agent/bin/iac-impl` once PB lands), so a lock
change that skipped the rebuild would surface as a live warning on every `iac` call.

Constraints:

- The pattern is the one both sibling repos already use: `utils.hasChanges(...)` guarding the
  build, `Utils.markStageSkippedForConditional(<stage name>)` in the else branch, and the
  `org.jenkinsci.plugins.pipeline.modeldefinition.Utils` import that `Jenkinsfile.iac-image` does
  not yet carry — `HelmCharts/Jenkinsfile:1,84,93-99`, `DockerImages/Jenkinsfile:1,46,111`.
- **The gate's patterns must full-match** (ruling, with the library source quoted there):
  `utils.hasChanges` tests its argument against each changed file's whole repo-relative path with
  Groovy's `==~`, so a watched path has to be written as a regex that matches that path end to
  end. A directory prefix therefore needs an explicit trailing `/.*` — which is exactly why both
  sibling call sites carry one (`HelmCharts/Jenkinsfile:95-98`, `DockerImages/Jenkinsfile:46`) —
  while a glob (`support/iac-image/**`) or a bare prefix (`support/iac-image`) matches nothing and
  would make *every* build skip, including the image-input pushes that must not.
- `utils.hasChanges` reads the build's own SCM changeset, so the `Cloning repo` stage's
  `checkout scm` has to stay (`Jenkinsfile.iac-image:5-7`; the same dependency is spelled out at
  `HelmCharts/Jenkinsfile:48-50`). The ruling records that the operator accepts the retry hole
  this implies.
- No escape hatch: no build parameter, no force flag (ruling).
- PB's `support/iac-agent/` is **not** an image input. Whichever pillar lands first, the gate must
  not sweep the whole of `support/`.

### PB — the IaCAgent tree becomes `support/iac-agent/`, and the role installs from it

Target: ansible

Everything now in `pvginkel/IaCAgent` lives at `support/iac-agent/<same relative path>` with its
content untouched by this phase and its commit history part of this repo's; and the `iac_agent`
role syncs and installs from there, so applying it needs the Ansible checkout and nothing beside
it. The bulk of the diff is a tree landing at the repo root, but the change that can actually
break is the role's, which is what the target's gate covers.

- **History (R5).** A plain copy that starts the tree's history at this slice does not satisfy R5:
  every IaCAgent commit must be present in this repo with its original author, date and message,
  reachable from `main`. Three facts the executor would otherwise have to discover: the driver
  merges each phase branch `--ff-only` (`run_loop.py:1949`), so a merge commit created on the
  phase branch survives into `main` intact; `/work/IaCAgent` holds the whole history locally
  (`main` at `973d330`, in sync with `origin/main`), so no network fetch is needed; and
  `git-filter-repo` is **not** installed in this environment (git is 2.51).
- **The tree lands prefixed, not at the root.** IaCAgent's root files (`README.md`, `.gitignore`,
  `install.sh`) must arrive under `support/iac-agent/` — landing them unprefixed would clobber
  this repo's own `README.md`.
- **Move only (ruling, N4).** All four files of the two duplicate pairs survive as separate files;
  nothing is deduplicated, here or later. Nothing inside the tree needs a path edit: `install.sh` resolves every source from its
  own directory (`/work/IaCAgent/install.sh:24`), and the tree's only `/work/...` strings are
  comments about the clone `iac-impl` makes inside the container, not about the controller's
  checkout.
- **The repoint** is `iac_agent_local_checkout` (`ansible/roles/iac_agent/defaults/main.yml:7`),
  which feeds both the `secrets.example.yaml` source and the rsync src
  (`ansible/roles/iac_agent/tasks/main.yml:68,89`). It has to resolve from the repo root for both
  controllers that matter: the operator's `/work/Ansible`, and the fresh clone `iac-impl` makes in
  the container. A `defaults/` variable is the role's interface — its comment must stop describing
  a sibling checkout.
- **The host-side layout does not move.** `iac_agent_install_dir` stays `/opt/IaCAgent`, and
  `install.sh` keeps materializing `/usr/local/bin/*`, `/etc/docker/daemon.json`,
  `/etc/cron.d/iac-prune` and the systemd unit (`/work/IaCAgent/install.sh:47-65`). That is what
  makes R6's parity apply a proof rather than a migration: the operator's run should converge with
  the host's materialized files untouched, and the shim's bind-mounts (`/work/IaCAgent/bin/iac:63-69`)
  keep resolving.
- **The fallback stays declared (N5).** `.kubecoder/config.yaml:12` and `Ansible.code-workspace:16`
  keep their `IaCAgent` entries and `/work/IaCAgent` stays on disk — those go once the operator has
  proven parity and archived the repo.
- **Both `--limit "!iac_agent"` lines stay untouched** — `Jenkinsfile.iac-apply:94` and
  `Jenkinsfile.iac-scheduled-drift:86`.
- **The move is a pure rename.** Nothing inside the tree changes content in this phase; the drift
  R4 names is real and ships in PC, on top. Keeping the two apart is what makes this diff — a
  history-carrying merge of 28 foreign commits — reviewable at all.

### PC — the moved tree stops describing itself as a separate repo running `modern-app-dev`

Target: root

`support/iac-agent/` describes what it now is and what actually runs it. The ruling's own test is
the bar: `grep modern-app-dev support/iac-agent/` returns nothing, and nothing in the tree still
tells a reader it lives in its own repo beside Ansible.

The drift the ruling names — all of it inside the moved tree, all verified this pass, paths below
relative to `support/iac-agent/`:

- **The container.** `README.md:9,10,12` say the shim runs `iac-impl` inside `modern-app-dev`;
  `bin/iac:15` runs `registry:5000/iac:latest`. The same stale name is in
  `etc/cron.d/iac-prune:3-4` and `bin/send_message.py:8`.
- **The repo framing.** `README.md:21-33` presents the Jenkins pipelines as having moved *out of
  this repo* into Ansible — after PB that is one repo, and `README.md:1-3` still frames the tree
  as a standalone project.
- **The Jenkinsfile list.** `README.md:28-31` names `Jenkinsfile.iac-dqlite-watchdog`, which no
  longer exists, and misses `Jenkinsfile.iac-apply`, `Jenkinsfile.iac-scheduled-calico` and
  `Jenkinsfile.iac-scheduled-certs` (the repo root's `Jenkinsfile.*` set is authoritative).
- **The bind-mount list.** `README.md:9` names two mounts; `bin/iac:63-69` mounts five —
  `iac-impl`, the secrets file, `send_message.py`, `check-protected-vms.sh`,
  `check-ansible-drift.sh`.

Constraints:

- **Prose and comments only, inside `support/iac-agent/`.** No behaviour changes: the shim, the
  installer and the cron schedule keep working exactly as they do after PB. Prose outside the tree
  is not this phase's.
- **This is not the dedup N4 forbids.** `bin/send_message.py` is one of N4's four held-out files;
  the R4 ruling names its `modern-app-dev` docstring line specifically. Fixing that line is a
  drift fix — the two `send_message.py` copies both stay, as separate files in their current
  locations.

## Not in scope

- **N1. Removing `--limit "!iac_agent"` from anywhere.** The merge makes CI application of the role
  *possible*; the operator does not want it done. Operator, 2026-08-13:

  > I don't want to remove the --limit argument. I appreciate it makes it possible, but I don't
  > like it.

- **N2. Merging `HomelabTerraformProvider` or `HelmCharts` into Ansible.** Settled in the change
  request, not to be reopened — a TF provider is its own Go module with its own release cadence,
  and HelmCharts is a different deployment unit that only shares the `iac` harness as a runtime.

- **N3. The change request's own out-of-scope list:** the `site*.yml` playbook layout
  (`site-yml-layout`, Triage #69); provider version resolution, owned by the completed
  `tf-provider-registry`; and the destroy-guard / `prevent_destroy` / apply-the-checked-plan fixes
  in the same Jenkinsfiles, split out to `tf_safety_rails` (Triage #127).

- **N4. Deduplicating `send_message.py` or the `daemon.json` content** — see the ruling above.

- **N5. Editing `.kubecoder/config.yaml`, archiving `pvginkel/IaCAgent`, or running the parity
  apply** — operator-owed, see the R6 ruling above.

- **N6. Triage cards #327 (`bin/iac` `--pull=always`) and #506 (drop the `/var/lock/iac.lock`
  flock).** Both edit files inside the tree this slice relocates. The operator's decision is to
  leave them queued and rebase them onto the new paths afterwards; they are not requirements here.

- **N7. Removing the `../IaCAgent` folder entry from `Ansible.code-workspace`** — the same
  fallback as N5, and it goes the same way: when the operator archives the repo, not before.
