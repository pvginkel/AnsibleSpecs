# Slice 013 — the `iac` image stops rebuilding on every Ansible push, and the IaCAgent repo becomes `support/iac-agent/` in this repo

## Requirements / rulings

Numbered requirements are `slice.md`'s, in the source's words. Rulings are the operator's, from
the 2026-08-13 refinement session; a ruling that contradicts a requirement's wording governs.

### Pillar A — scope the `iac-image` rebuild

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
  reads the build's own SCM changeset (the shared library source is not checked out in this
  environment, so its exact semantics are unverified), which means a build that fails on an
  image-input push is not retried by the next unrelated push. The operator accepts that hole.

### Pillar B — merge `IaCAgent` into `Ansible`

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

### Rulings that bound both pillars

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
