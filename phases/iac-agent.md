# Phase 1 — IaC agent VM (`srviac`)

**Status**: planned.

## Goal

Stand up `srviac`, the dedicated VM that runs all Terraform and Ansible against the homelab, and cut the operator workstation out of the routine execution path.

After this phase lands:

- TF apply and `ansible-playbook` against prd flow through `srviac` — either as a Jenkins job (scheduled or on-push) or as `iac` invocations the operator runs over SSH. Both paths run the same container image, hold the same flock-based lock, and read the same `/etc/iac/secrets.yaml`.
- The operator workstation is reserved for the carve-out: changes that mutate `srviac` itself, plus break-glass when CI is down.
- Routine merges to `main` on this repo auto-apply against prd. The on-push site run excludes the k8s and ceph cluster groups (drain-requiring changes go through `update-k8s.yml` / future `update-ceph.yml`, both Jenkins-scheduled).
- TF state moves out of the local checkout into a dedicated Git repo, cloned fresh per run.

Pre-OpenBao secrets live in `/etc/iac/secrets.yaml` on `srviac`. After OpenBao lands, that file shrinks to the OpenBao admin token + AppRole bootstrap and the rest migrates. The shape stays the same.

This phase explicitly does not depend on OpenBao — accepted as sub-optimal because the orchestration win lands sooner. The migration cost when OpenBao does land is mechanical (move N entries out of the YAML file, update consumers to read from Bao).

## Decisions taken with the operator

### VM shape

- **Hostname / VMID**: `srviac`, VMID `920`, deterministic MAC (`02:A7:F3:03:98:00`). Single NIC on `vmbr0`, dynamic `homelab_dns_reservation` (not bring-up-tier).
- **`pve_node = pve`** so the daily vzdump picks it up (only `pve` carries `local-backup`).
- **`workload_class = background`** for CPU affinity.
- **Sizing**: 3 GiB RAM, 32 GiB disk. Start low; observe via Prometheus and raise if it bites. The `modern-app-dev` image carries JDKs / Node / Go / Terraform / kubectl / Helm — one concurrent `iac` container running a full `site.yml` is the load to watch.
- **OS update class: standalone.** `unattended-upgrades` + auto-reboot in a quiet window. Must not collide with OpenBao's window once that lands.
- **TF guards**: `lifecycle { prevent_destroy = true }` on the VM resource. The on-push Jenkins job's plan stage fails the pipeline if `terraform plan` proposes `replace` or `destroy` on `srviac` (or, later, `srvvault`).

### Host posture: minimal

- **Operator access: SSH only.** No VSCode Remote, no desktop tools, no dev environment.
- **Nothing on the host that the image already carries.** No Terraform, Ansible, kubectl, helm, python — those live exclusively in `modern-app-dev`. The host carries:
  - Docker (engine + CLI) with `/etc/docker/daemon.json` declaring `registry:5000` as an insecure registry.
  - `prometheus-node-exporter` (installed by `baseline` — see "Playbook + inventory changes"). Scraped by the in-cluster Prometheus.
  - `flock(1)` (from coreutils).
  - The `iac` shim (~30 lines bash; `/usr/local/bin/iac`).
  - `send_message.py` (push-notification helper for the Jenkins post-stage; vendored from `/work/DesignAssistant/scripts/send_message.py`).
  - A systemd unit running the Jenkins inbound-agent container.
  - A daily cron: `docker image prune -f` (dangling images only — single-tag pulls leave the previous layer untagged).
  - `/etc/iac/secrets.yaml` (operator-curated, `0600`).
  - `/var/lock/iac.lock` (the IaC mutex).
- **Jenkins agent: containerized.** Docker socket mounted in; the agent spawns sibling `iac` containers via the host's docker. The agent container is a long-running pinned image — `docker image prune -f` skips images backing running containers, so it survives daily prune. Registered on the controller as `IaC Agent` with label `iac-controller`, remote root `/work`.

### `iac` wrapper

Two forms, one lock:

```
iac                              # interactive bash inside the container
iac -c '<shell script>'          # run the script inside the container
```

Both acquire `/var/lock/iac.lock` via `flock -w 60` (1-minute timeout; on failure, the holder PID surfaces and the call exits non-zero). One call = one lock — multi-step jobs compose their work into a single `iac -c '...'` rather than chaining calls.

Logic split:

- **`/usr/local/bin/iac`** is a thin host shim. ~30 lines bash: acquire flock, then `docker run --rm [-it] -v /etc/iac/secrets.yaml:/etc/iac/secrets.yaml:ro registry:5000/modern-app-dev:latest iac-impl "$@"`. The shim adds `-it` only when stdin is a tty.
- **`iac-impl`** lives inside the `modern-app-dev` image. Each run:
  1. Parses `/etc/iac/secrets.yaml`. Exports `env:` entries; writes `files:` entries at their declared mode.
  2. Clones `pvginkel/Ansible` and `pvginkel/TerraformState` (both `prd/` and `scratch/` subtrees) into `/work/`. Both, always — avoids a scope flag, and the clones are small.
  3. Symlinks `/work/Ansible/terraform/{prd,scratch}/terraform.tfstate` → `/work/TerraformState/{prd,scratch}/terraform.tfstate` so terraform reads and writes through into the state-repo clone.
  4. Runs `poetry install --no-root` in `/work/Ansible/ansible/` so `ansible-playbook` is on `$PATH`.
  5. Exec's `bash` (interactive) or `sh -c "$SCRIPT"` (the `-c` form).
  6. On exit, if `/work/TerraformState` has uncommitted state changes, commits and pushes with `GIT_API_TOKEN`.

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
  - name: TF_VAR_proxmox_endpoint
    value: https://pve.home:8006/
  - name: TF_VAR_proxmox_username
    value: root@pam
  - name: TF_VAR_proxmox_password
    value: ...
  - name: TF_VAR_proxmox_insecure
    value: "true"
  - name: TF_VAR_dns_reservation_url
    value: https://dns-reservation.home/
  - name: TF_VAR_dns_reservation_token
    value: ...

files:
  - path: /root/.ssh/id_ed25519_ansible
    content: |
      -----BEGIN OPENSSH PRIVATE KEY-----
      …
      -----END OPENSSH PRIVATE KEY-----
    mode: "0600"
```

Consumers in this phase: `GIT_API_TOKEN` (`iac-impl` clones + pushes `TerraformState`), `HA_URL` / `HA_TOKEN` (`send_message.py`), `JENKINS_AGENT_SECRET` (Jenkins agent systemd unit), `TF_VAR_*` (terraform, replacing the tracked `terraform.tfvars`), `id_ed25519_ansible` (Ansible SSH login to managed hosts — repo continues to hold the public side under `ansible/files/known_hosts.d/`).

### Two new repos

- **`pvginkel/TerraformState`** — root layout: `prd/`, `scratch/`, plus `README.md` explaining the contract (file-based state, cloned + committed per run, private). `.gitignore` excludes `*.backup` (Terraform's local backup files; the git history is the backup). Access via the GitHub API token in `secrets.yaml`.
- **`pvginkel/IaCAgent`** — host glue: `bin/iac` (shim), `bin/send_message.py`, `etc/iac/secrets.example.yaml`, `etc/docker/daemon.json`, `etc/cron.d/iac-prune`, `systemd/jenkins-agent.service`, `install.sh`, `README.md`. `install.sh` is idempotent — the `iac_agent` Ansible role clones and runs it; the operator workstation can do the same manually for parity.

### Playbook + inventory changes

- **`site.yml`** excludes `k8s_prd:k8s_dev:ceph_prd` at the play level (blacklist form for this phase). The microk8s play is dropped from `site.yml`; drain-requiring microk8s role applies flow only through `update-k8s.yml` / `rebuild-k8s.yml`. The `iac-on-push` job additionally passes `--limit '!iac_agent'` for self-mutation safety. See [slice: site-yml-layout](../slices/site-yml-layout.md) for the larger structural question this opens.
- **New group `iac_agent`** with `srviac` as its only member.
- **New role `iac_agent`**: installs Docker, drops `/etc/docker/daemon.json` with the insecure-registry entry, places `/etc/iac/secrets.yaml` (operator-curated; `force: no` so re-runs never overwrite — see "secrets.yaml lifecycle"), clones IaCAgent + runs `install.sh`, enables the Jenkins agent systemd unit.
- **`baseline` picks up `prometheus-node-exporter`.** Universal across every managed host so the in-cluster Prometheus has uniform visibility. Lands in this phase because srviac's low-RAM start specifically wants metrics; k8s/ceph nodes inherit it the next time they're rolled.

### Jenkins jobs

Three jobs land in this phase. Pipeline scripts live in IaCAgent. Each job composes its work into one `iac -c '...'` per stage so the lock is held across the steps that must be atomic.

1. **`iac-on-push`** — trigger: push to `main` on `pvginkel/Ansible`. Sequential, fail-fast:
   - Plan-stage check: `iac -c 'cd /work/Ansible/terraform/prd && terraform plan -json -out=/tmp/plan.tfplan && terraform show -json /tmp/plan.tfplan | <destroy-check>'`, fail if any `replace`/`destroy` proposes on `srviac` or `srvvault`. Belt-and-braces with `prevent_destroy`.
   - `iac -c 'cd /work/Ansible/terraform/prd && terraform apply -auto-approve'`.
   - `iac -c 'cd /work/Ansible/ansible && ansible-playbook playbooks/site.yml --limit "!iac_agent"'`.
   - `iac -c 'cd /work/Ansible/ansible && ansible-playbook playbooks/update-k8s.yml'` — idempotent rolling update, no-op if no upgrades pending (per commit `76ab186`).
2. **`iac-scheduled-update`** — trigger: cron, weekly. `iac -c 'cd /work/Ansible/ansible && ansible-playbook playbooks/update-k8s.yml'`. Future: `update-ceph` and the `srvvault` reboot window. Reboot stagger is enforced by the play order itself.
3. **`iac-scheduled-drift`** — trigger: cron, daily. `iac -c 'cd /work/Ansible/terraform/prd && terraform plan -detailed-exitcode'` and `iac -c 'cd /work/Ansible/ansible && ansible-playbook playbooks/site.yml --check --diff --limit "!iac_agent"'`. Push-notifies on `changed > 0` or non-zero exit.

All three acquire `/var/lock/iac.lock`; manual `iac` runs acquire the same lock. A manual run and a scheduled job cannot race — but with the 60-second timeout one of them fails fast rather than waiting. Failure notification: post-stage in each pipeline calls `send_message.py` (running inside the container) with job name + URL.

## Execution sequence

1. **Phase doc + slice.** This file updated to the agreed shape; new slice `slices/site-yml-layout.md` opens the structural question for the analyst.
2. **`site.yml` exclusion.** First play's `hosts:` line becomes `managed:!k8s_prd:!k8s_dev:!ceph_prd`; the microk8s play is removed. No infra change yet; the new `iac_agent` play is added later in the sequence (it would target an empty group until step 6).
3. **IaCAgent repo skeleton.** `bin/iac`, `bin/send_message.py`, `etc/iac/secrets.example.yaml`, `etc/docker/daemon.json`, `etc/cron.d/iac-prune`, `systemd/jenkins-agent.service`, `install.sh`. Tag `v0.1.0`. Jenkinsfiles land in a follow-up commit (step 9).
4. **`iac-impl` in modern-app-dev.** Lands in `/work/DockerImages/modern-app-dev/bin/iac-impl` — the script that parses secrets.yaml, clones Ansible + TerraformState, symlinks state, runs `poetry install`, exec's terraform / ansible / bash, and pushes any state changes on exit. Same image rebuild pipeline rolls it out.
5. **TerraformState repo skeleton.** Empty `prd/`, `scratch/`, `README.md`, `.gitignore`. State import is deferred to cutover (step 10).
6. **`iac_agent` role + baseline change.** `iac_agent` installs Docker + insecure-registry daemon.json, places secrets.yaml (`force: no` guard), clones IaCAgent + runs `install.sh`, enables the Jenkins agent unit. `baseline` picks up `prometheus-node-exporter`. Add the fourth `hosts: iac_agent` play to `site.yml`.
7. **`srviac` in TF + inventory.** New entry in `terraform/prd/vms.tf` with `prevent_destroy = true`. New `iac_agent` group, `host_vars/srviac.yml`. Delete the tracked `terraform/prd/terraform.tfvars` (the values now live in `secrets.yaml` as `TF_VAR_*`); the existing `*.tfvars` gitignore stops accidental recommits. Operator applies TF; operator runs `site.yml --limit srviac` from the workstation.
8. **Operator populates `/etc/iac/secrets.yaml`.** Hand-edit on srviac. The role's secrets task uses `force: no` so re-runs never clobber operator-curated content; if the file is missing on a fresh srviac, the role places `secrets.example.yaml` (placeholder values) and fails loudly so a rebuild surfaces "you need to populate secrets" before anything else runs against bad credentials.
9. **IaCAgent Jenkinsfiles.** Three pipeline scripts + the plan-stage destroy-check helper. Commit, tag.
10. **Bootstrap TerraformState.** From the operator workstation, copy current `terraform/prd/terraform.tfstate` and `terraform/scratch/terraform.tfstate` into the new repo's `prd/` and `scratch/`, push. Verify from srviac: `iac -c 'cd /work/Ansible/terraform/prd && terraform plan'` is no-op.
11. **Verify `iac` paths.** `ssh srviac && iac` → run a no-op `terraform plan` and `ansible-playbook --check --diff site.yml` inside the shell. Both clean → green light.
12. **Wire the three Jenkins jobs.** Verify against a no-op change to this repo (comment-only push) before unleashing.
13. **Cutover.** Operator stops running TF/Ansible from the workstation as routine. Delete the workstation's local `terraform.tfstate` + `.backup` files; the state repo is now authoritative.

## Verification

- `iac` on srviac opens bash inside `modern-app-dev` with `/work/Ansible` and `/work/TerraformState/{prd,scratch}` populated as fresh clones, `terraform.tfstate` symlinks in place, `/etc/iac/secrets.yaml` mounted. All env entries exported. All file entries written with the declared mode.
- `iac -c 'cd /work/Ansible/terraform/prd && terraform plan'` is no-op against the bootstrapped state.
- `iac -c 'cd /work/Ansible/ansible && ansible-playbook playbooks/site.yml --check --diff --limit "!iac_agent"'` reports `changed=0`.
- Push a trivial change to `pvginkel/Ansible` `main` → `iac-on-push` triggers, holds the flock, runs all sub-steps successfully, releases the flock.
- During the on-push run, attempt `iac` from another SSH session → fails within 60 seconds with the held-PID surfaced (no waiting).
- `iac-scheduled-drift` runs clean (no diff) on a quiescent prd. Deliberately mutate a managed file on a host → next run flags it.
- Plan-stage check: insert a destroy on srviac in TF → the on-push job fails at plan, not at apply. `prevent_destroy` also rejects the apply if the plan check is bypassed.
- `prometheus-node-exporter` exposes `:9100/metrics` on srviac; the in-cluster Prometheus scrape config (landed via HelmCharts, outside this repo) picks it up.

## secrets.yaml lifecycle

- Authored by the operator, by hand, on srviac. Never in Git.
- The `iac_agent` role's task that writes the file uses `force: no` — re-runs don't clobber operator-curated content. If the file is missing on a fresh srviac, the role places `secrets.example.yaml` (placeholder values) and fails loudly.
- Backed up by the existing backup-collector (which age-encrypts before leaving the box). Plaintext on the wire to backup-server is accepted per `decisions.md` "OpenBao backup / DR" rationale. No second age wrap on srviac.
- On OpenBao landing: every entry except the OpenBao admin token + AppRole bootstrap migrates out. Consumers re-read from OpenBao. File shape stays the same; row count shrinks.

## Out of scope

- **OpenBao integration.** Accepted as sub-optimal. The migration is mechanical when Phase 3 lands.
- **VSCode Remote / dev environment on srviac.** Operator design rule: minimal RAM, SSH-only.
- **Drift detection beyond `--check --diff` + `terraform plan`.** Backup-flag policy assertion, vmbr1 traffic audit, vzdump-node attribute wiring — `decisions.md` "Deferred / revisit" items, not in this phase.
- **Whitelist refactor of `site.yml`.** Carved into [slice: site-yml-layout](../slices/site-yml-layout.md) — this phase keeps the blacklist form.
- **Prometheus scrape config in HelmCharts.** The node_exporter install on managed hosts lands here; pointing the in-cluster Prometheus at the new targets is a HelmCharts change the operator commits separately.
- **Operator workstation parity.** The workstation can install IaCAgent for parity, but isn't required to — its remaining role is break-glass + srviac-mutation, both of which work without `iac` (you can still run terraform / ansible-playbook directly in those cases).
- **Slack / webhook notifications.** Phone push via `send_message.py` is the bar.

## Caveats

- **Agent VM rebuild is not orchestrator-self-applicable.** The operator workstation handles agent VM mutation. Lose the workstation and recovery is "bootstrap any Ubuntu box, install IaCAgent + pull modern-app-dev, re-clone this repo, apply" — not zero-touch.
- **Auto-apply on merge to main means every merge mutates prd.** No PR-time staging environment. Acceptable at homelab scale; flagged for awareness.
- **`secrets.yaml` plaintext on disk and on the wire to backup-server.** Conscious tradeoff. Threat model: same as the operator workstation today. OpenBao migration shortens the horizon.
- **TerraformState repo is sensitive.** Holds VM host private keys, API tokens, proxmox credentials. Same protection as any secret-bearing repo: private, no public mirror.
- **The `iac` lock is host-wide, not cluster-wide.** A `terraform apply` from the operator workstation (the break-glass path) does not see the flock. The workstation should only be running TF/Ansible against srviac itself or in genuine break-glass; mixing routine work between workstation and srviac defeats the lock.
- **60-second flock = fail-fast.** A scheduled job firing during a manual `iac` session fails rather than waiting. The push notification on a failed scheduled job is the operator-visible signal.

## Commits

1. This plan, updated in `phases/iac-agent.md`. New slice `slices/site-yml-layout.md`. Updated `phases/README.md` / `slices/README.md` as needed.
2. `ansible/playbooks/site.yml`: first play excludes `k8s_prd:k8s_dev:ceph_prd`; microk8s play removed. No infra change yet.
3. New repo `pvginkel/IaCAgent`: initial skeleton — `bin/iac`, `bin/send_message.py`, `etc/iac/secrets.example.yaml`, `etc/docker/daemon.json`, `etc/cron.d/iac-prune`, `systemd/jenkins-agent.service`, `install.sh`, `README.md`. Tag `v0.1.0`.
4. `/work/DockerImages/modern-app-dev`: add `bin/iac-impl`. Cascading rebuild via existing pipeline.
5. New repo `pvginkel/TerraformState`: empty `prd/`, `scratch/`, `README.md`, `.gitignore`. State bootstrap at cutover.
6. `roles/iac_agent` + `roles/baseline` (node_exporter) + `inventories/prd/group_vars/iac_agent.yml` + `inventories/prd/host_vars/srviac.yml` + group declaration + the new `hosts: iac_agent` play in `site.yml`.
7. `terraform/prd/vms.tf`: new `srviac` entry with `prevent_destroy = true`. Delete tracked `terraform.tfvars`. (Operator applies.)
8. IaCAgent Jenkinsfile additions for the three jobs + plan-stage check helper.
9. Cutover commit in this repo: `docs/runbooks/iac-agent.md` written; retire any "from-workstation" notes in existing runbooks.
