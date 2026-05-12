# Phase 1 — IaC agent VM (`srviac`)

**Status**: planned.

## Goal

Stand up `srviac`, the dedicated VM that runs all Terraform and Ansible against the homelab, and cut the operator workstation out of the routine execution path.

After this phase lands:

- TF apply and `ansible-playbook` against prd flow through `srviac` — either as a Jenkins job (scheduled or on-push) or as `iac` subcommands the operator runs over SSH. Both paths run the same container image, hold the same flock-based lock, and read the same `/etc/iac/secrets.yaml`.
- The operator workstation is reserved for the carve-out: changes that mutate `srviac` itself, plus break-glass when CI is down.
- Routine merges to `main` on this repo auto-apply against prd. The on-push site run excludes the k8s and ceph cluster groups (drain-requiring changes go through `update-k8s.yml` / future `update-ceph.yml`, both Jenkins-scheduled).
- TF state moves out of the local checkout into a dedicated Git repo, cloned fresh per run.

Pre-OpenBao secrets live in `/etc/iac/secrets.yaml` on `srviac`. After OpenBao lands, that file shrinks to the OpenBao admin token + AppRole bootstrap and the rest migrates. The shape stays the same.

This phase explicitly does not depend on OpenBao — accepted as sub-optimal because the orchestration win lands sooner. The migration cost when OpenBao does land is mechanical (move N entries out of the YAML file, update consumers to read from Bao).

## Decisions taken with the operator

### VM shape

- **Hostname**: `srviac`. Greenfield, 900-range VMID, deterministic MAC. Single NIC on `vmbr0`, dynamic `homelab_dns_reservation` (not bring-up-tier).
- **Minimal sizing.** Enough for Docker daemon + Jenkins agent container + one concurrent `iac` container + small headroom. Target ~2 GiB RAM, ~32 GiB disk; final numbers picked during TF write.
- **OS update class: standalone.** `unattended-upgrades` + auto-reboot in a quiet window. Must not collide with OpenBao's window once that lands.
- **TF guards**: `lifecycle { prevent_destroy = true }` on the VM resource. The on-push Jenkins job's plan stage fails the pipeline if `terraform plan` proposes `replace` or `destroy` on `srviac` (or, later, `srvvault`).

### Host posture: minimal

- **Operator access: SSH only.** No VSCode Remote, no desktop tools, no dev environment.
- **Nothing on the host that the image already carries.** No Terraform, Ansible, kubectl, helm, python — those live exclusively in `modern-app-dev`. The host carries:
  - Docker (engine + CLI).
  - `flock(1)` (from coreutils).
  - The `iac` shim (~30 lines bash; `/usr/local/bin/iac`).
  - `send_message.py` (push-notification helper for the Jenkins post-stage; vendored from `/work/DesignAssistant/scripts/send_message.py`).
  - A systemd unit running the Jenkins inbound-agent container.
  - A daily cron: `docker image prune -f` (dangling images only — single-tag pulls leave the previous layer untagged).
  - `/etc/iac/secrets.yaml` (operator-curated, `0600`).
  - `/var/lock/iac.lock` (the IaC mutex).
- **Jenkins agent: containerized.** Docker socket mounted in; the agent spawns sibling `iac` containers via the host's docker. The agent container is a long-running pinned image — `docker image prune -f` skips images backing running containers, so it survives daily prune.

### `iac` wrapper

Three subcommands. All hold `/var/lock/iac.lock` via `flock -w 900` (15-minute timeout; the holder PID surfaces on failure).

```
iac shell                          # interactive bash inside the container
iac terraform <scope> <cmd ...>    # scope in {prd, scratch}; requires
                                   # /work/Ansible/terraform/$SCOPE and /work/TerraformState/$SCOPE to exist
iac ansible <play> [args...]       # runs playbooks/<play>.yml
```

Bind mounts on every invocation: `/work/Ansible` (fresh clone of this repo), `/work/TerraformState/<scope>` (fresh clone of the state repo scoped to the requested scope), `/etc/iac/secrets.yaml` (read-only). Edits inside an `iac shell` session are lost on exit unless pushed before exit — same constraint Jenkins jobs already have, and it keeps the VM stateless.

Logic split:

- **`/usr/local/bin/iac`** is a thin host shim. ~30 lines bash: acquire flock, `docker run --rm [-it] -v ... modern-app-dev:latest iac-impl "$@"`.
- **`iac-impl`** lives inside the `modern-app-dev` image. Parses `secrets.yaml`, exports env, writes file entries, clones TerraformState, then exec's terraform / ansible / bash.

Same image for Jenkins jobs and the operator shell — updates to TF/Ansible/kubectl/etc. ride the existing image rebuild pipeline.

### `secrets.yaml` shape

Single file at `/etc/iac/secrets.yaml`. Two top-level lists. `mode` is required on each `files:` entry (no default).

```yaml
env:
  - name: GIT_API_TOKEN
    value: ghp_xxxxxxxxxxxxxxxx
  - name: HA_URL
    value: http://homeassistant.home:8123
  - name: HA_TOKEN
    value: eyJhbGciOiJI...
  - name: JENKINS_AGENT_SECRET
    value: ...

files:
  - path: /root/.ssh/id_ed25519_ansible
    content: |
      -----BEGIN OPENSSH PRIVATE KEY-----
      …
      -----END OPENSSH PRIVATE KEY-----
    mode: "0600"
```

Consumers in this phase: `GIT_API_TOKEN` (`iac-impl` to clone/push TerraformState), `HA_URL` / `HA_TOKEN` (`send_message.py`), `JENKINS_AGENT_SECRET` (Jenkins agent systemd unit), `id_ed25519_ansible` (Ansible SSH login to managed hosts — repo continues to hold the public side under `ansible/files/known_hosts.d/`).

### Two new repos

- **`pvginkel/TerraformState`** — root layout: `prd/`, `scratch/`, plus `README.md` explaining the contract (file-based state, cloned + committed per run, private). Access via the GitHub API token in `secrets.yaml`.
- **`pvginkel/IaCAgent`** — host glue: `bin/iac` (shim), `bin/send_message.py`, `etc/iac/secrets.example.yaml`, `etc/cron.d/iac-prune`, `systemd/jenkins-agent.service`, `install.sh`, `README.md`. `install.sh` is idempotent — the `iac_agent` Ansible role clones and runs it; the operator workstation can do the same manually for parity.

### Playbook + inventory changes

- **`site.yml`** excludes `k8s_prd:k8s_dev:ceph_prd` at the play level. The safety contract lives in the playbook, not in a `--limit` flag. Drain-requiring changes flow only through `update-k8s.yml` / future `update-ceph.yml`. The `iac-on-push` job additionally passes `--limit '!iac_agent'` for self-mutation safety.
- **New group `iac_agent`** with `srviac` as its only member.
- **New role `iac_agent`**: installs Docker, places `/etc/iac/secrets.yaml` (operator-curated; `force: no` so re-runs never overwrite — see "secrets.yaml lifecycle"), clones IaCAgent + runs `install.sh`, enables the Jenkins agent systemd unit.

### Jenkins jobs

Three jobs land in this phase. Pipeline scripts live in IaCAgent.

1. **`iac-on-push`** — trigger: push to `main` on `pvginkel/Ansible`. Sequential, fail-fast:
   - Plan-stage check: `terraform plan -json` against `terraform/prd`, fail if any `replace`/`destroy` proposes on `srviac` or `srvvault`. Belt-and-braces with `prevent_destroy`.
   - `iac terraform prd apply -auto-approve`.
   - `iac ansible site --limit '!iac_agent'`.
   - `iac ansible update-k8s` — idempotent rolling update, no-op if no upgrades pending (per commit `76ab186`).
2. **`iac-scheduled-update`** — trigger: cron, weekly. `iac ansible update-k8s`. Future: `update-ceph` and the `srvvault` reboot window. Reboot stagger is enforced by the play order itself.
3. **`iac-scheduled-drift`** — trigger: cron, daily. `iac terraform prd plan -detailed-exitcode` + `iac ansible site --check --diff --limit '!iac_agent'`. Push-notifies on `changed > 0` or non-zero exit.

All three acquire `/var/lock/iac.lock`; manual `iac` runs acquire the same lock. So a manual run and a scheduled job cannot race. Failure notification: post-stage in each pipeline calls `send_message.py` (running inside the container) with job name + URL.

## Execution sequence

1. **`site.yml` cluster-group exclusion.** One commit, no infra change — site.yml was already not meant to touch those groups; this makes the contract explicit.
2. **IaCAgent repo skeleton.** `bin/iac`, `bin/send_message.py`, `etc/iac/secrets.example.yaml`, `etc/cron.d/iac-prune`, `install.sh`. Tag `v0.1.0`. Add systemd unit + Jenkinsfiles in successive commits.
3. **`iac-impl` in modern-app-dev.** Lands in `/work/DockerImages/modern-app-dev` — the script that parses secrets.yaml, clones TerraformState per `$SCOPE`, runs terraform / ansible / opens a shell. Same image rebuild pipeline rolls it out.
4. **TerraformState repo skeleton.** Empty `prd/`, `scratch/`, `README.md`. State import is deferred to cutover (step 8).
5. **`iac_agent` role.** Installs Docker, places secrets.yaml (`force: no` guard), clones IaCAgent + runs `install.sh`, enables the Jenkins agent unit.
6. **`srviac` in TF + inventory.** New entry in `terraform/prd/vms.tf` with `prevent_destroy = true`. New `iac_agent` group, `host_vars/srviac.yml`. Operator applies TF; operator runs `site.yml --limit srviac`.
7. **Operator populates `/etc/iac/secrets.yaml`.** Hand-edit on srviac. The role's secrets task uses `force: no` so re-runs never clobber operator-curated content; if the file is missing on a fresh srviac, the role places `secrets.example.yaml` (placeholder values) and fails loudly so a rebuild surfaces "you need to populate secrets" before anything else runs against bad credentials.
8. **Bootstrap TerraformState.** From the operator workstation, copy current `terraform/prd/terraform.tfstate` into the new repo's `prd/`, push. Verify from srviac: `iac terraform prd plan` is no-op.
9. **Verify `iac` paths.** `ssh srviac && iac shell` → run a no-op `terraform plan` and `ansible-playbook --check --diff site.yml`. Both clean → green light.
10. **Wire the three Jenkins jobs.** Verify against a no-op change to this repo (comment-only push) before unleashing.
11. **Cutover.** Operator stops running TF/Ansible from the workstation as routine. Delete the workstation's local `terraform.tfstate` files; the state repo is now authoritative.

## Verification

- `iac shell` on srviac opens bash inside `modern-app-dev` with `/work/Ansible`, `/work/TerraformState/prd`, `/etc/iac/secrets.yaml` mounted. All env entries exported. All file entries written with the declared mode.
- `iac terraform prd plan` is no-op against the bootstrapped state.
- `iac ansible site --check --diff --limit '!iac_agent'` reports `changed=0`.
- Push a trivial change to `pvginkel/Ansible` `main` → `iac-on-push` triggers, holds the flock, runs all three sub-steps successfully, releases the flock.
- During the on-push run, attempt `iac shell` from another SSH session → blocks on the flock, then either succeeds (after the job finishes) or fails with the held-PID surfaced.
- `iac-scheduled-drift` runs clean (no diff) on a quiescent prd. Deliberately mutate a managed file on a host → next run flags it.
- Plan-stage check: insert a destroy on srviac in TF → the on-push job fails at plan, not at apply. `prevent_destroy` also rejects the apply if the plan check is bypassed.

## secrets.yaml lifecycle

- Authored by the operator, by hand, on srviac. Never in Git.
- The `iac_agent` role's task that writes the file uses `force: no` — re-runs don't clobber operator-curated content. If the file is missing on a fresh srviac, the role places `secrets.example.yaml` (placeholder values) and fails loudly.
- Backed up by the existing backup-collector (which age-encrypts before leaving the box). Plaintext on the wire to backup-server is accepted per `decisions.md` "OpenBao backup / DR" rationale. No second age wrap on srviac.
- On OpenBao landing: every entry except the OpenBao admin token + AppRole bootstrap migrates out. Consumers re-read from OpenBao. File shape stays the same; row count shrinks.

## Out of scope

- **OpenBao integration.** Accepted as sub-optimal. The migration is mechanical when Phase 3 lands.
- **VSCode Remote / dev environment on srviac.** Operator design rule: minimal RAM, SSH-only.
- **Drift detection beyond `--check --diff` + `terraform plan`.** Backup-flag policy assertion, vmbr1 traffic audit, vzdump-node attribute wiring — `decisions.md` "Deferred / revisit" items, not in this phase.
- **Operator workstation parity.** The workstation can install IaCAgent for parity, but isn't required to — its remaining role is break-glass + srviac-mutation, both of which work without `iac` (you can still run terraform / ansible-playbook directly in those cases).
- **Slack / webhook notifications.** Phone push via `send_message.py` is the bar.

## Caveats

- **Agent VM rebuild is not orchestrator-self-applicable.** The operator workstation handles agent VM mutation. Lose the workstation and recovery is "bootstrap any Ubuntu box, install IaCAgent + pull modern-app-dev, re-clone this repo, apply" — not zero-touch.
- **Auto-apply on merge to main means every merge mutates prd.** No PR-time staging environment. Acceptable at homelab scale; flagged for awareness.
- **`secrets.yaml` plaintext on disk and on the wire to backup-server.** Conscious tradeoff. Threat model: same as the operator workstation today. OpenBao migration shortens the horizon.
- **TerraformState repo is sensitive.** Holds VM host private keys, API tokens, proxmox credentials. Same protection as any secret-bearing repo: private, no public mirror.
- **The `iac` lock is host-wide, not cluster-wide.** A `terraform apply` from the operator workstation (the break-glass path) does not see the flock. The workstation should only be running TF/Ansible against srviac itself or in genuine break-glass; mixing routine work between workstation and srviac defeats the lock.

## Commits

1. This plan, here in `phases/iac-agent.md`. Updated `phases/README.md`.
2. `ansible/playbooks/site.yml`: `hosts:` line excludes `k8s_prd:k8s_dev:ceph_prd`. No infra change yet.
3. New repo `pvginkel/IaCAgent`: initial skeleton — `bin/iac`, `bin/send_message.py`, `etc/iac/secrets.example.yaml`, `etc/cron.d/iac-prune`, `install.sh`, `README.md`. Tag `v0.1.0`.
4. `/work/DockerImages/modern-app-dev`: add `bin/iac-impl`. Cascading rebuild via existing pipeline.
5. `roles/iac_agent` + `inventories/prd/group_vars/iac_agent.yml` + `inventories/prd/host_vars/srviac.yml` + group declaration.
6. `terraform/prd/vms.tf`: new `srviac` entry with `prevent_destroy = true`. (Operator applies.)
7. New repo `pvginkel/TerraformState`: empty `prd/`, `scratch/`, `README.md`. State bootstrap at cutover, not at repo-create.
8. IaCAgent Jenkinsfile additions for the three jobs + plan-stage check helper.
9. Cutover commit in this repo: `docs/runbooks/iac-agent.md` written; retire any "from-workstation" notes in existing runbooks.
