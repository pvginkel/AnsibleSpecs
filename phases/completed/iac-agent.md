# Phase 1 — IaC agent VM (`srviac`)

**Status**: ✅ Closed 2026-05-12 — `srviac` live (VMID 920, `pve`, vmbr0 dynamic), three Jenkins jobs wired (`iac-on-push`, `iac-scheduled-update`, `iac-scheduled-drift`), workstation-local tfstate retired, in-cluster Prometheus scraping the new node_exporter targets.

## What this phase delivered

Concrete output, by repo:

- **`pvginkel/IaCAgent`** (new repo) — host-side glue for srviac.
  - `bin/iac` host shim — acquires `/var/lock/iac.lock` (`flock -w 60`, fail-fast on contention with the holder PID surfaced) and runs `bin/iac-impl` inside the iac container, bind-mounting the shim, impl, and helper scripts (`send_message.py`, `check-protected-vms.sh`, `check-ansible-drift.sh`) from the host.
  - `bin/iac-impl` — in-container entrypoint. Parses `/etc/iac/secrets.yaml`, clones `pvginkel/Ansible` and `pvginkel/TerraformState`, copies state files in, exec's bash (no args) or `sh -c "$2"` (`-c` form), then copies state out and pushes back to TerraformState on exit. `-v / --verbose` opt-in for setup-progress prints; default is silent. Warns loudly when `/work/Ansible/poetry.lock` differs from the iac image's baked `/app/poetry.lock` (image-rebuild lag window).
    - *Superseded:* the clone-and-sync state dance was replaced by `terraform-backend-git` (an http backend daemon `iac-impl` starts on `127.0.0.1:6061`); state now lives behind the backend, encrypted with sops + age. See `docs/runbooks/iac-agent.md`.
  - `bin/jenkins-agent-launch.sh` + `systemd/jenkins-agent.service` — long-running container for the Jenkins inbound agent. Reads `JENKINS_AGENT_SECRET` from secrets.yaml on the host (root via systemd) and passes it as argv to `jenkins/inbound-agent`. Mounts `iac` + helpers into the agent so pipeline `sh "iac -c '…'"` steps work.
  - `etc/docker/daemon.json` — declares `registry:5000` as an insecure registry (the homelab registry is HTTP-only).
  - `etc/cron.d/iac-prune` — daily `docker image prune -f` (dangling-only).
  - `etc/iac/secrets.example.yaml` — placeholder shape for the operator-curated `/etc/iac/secrets.yaml`. `env:` + `files:` lists; `mode` required on each files entry.
  - `install.sh` — idempotent installer; the `iac_agent` Ansible role runs it on each apply.
  - `jenkins/iac-on-push/Jenkinsfile`, `jenkins/iac-scheduled-update/Jenkinsfile`, `jenkins/iac-scheduled-drift/Jenkinsfile` — the three pipelines, all on the `iac-controller`-labelled agent.

- **`pvginkel/TerraformState`** (new repo) — file-based tfstate, cloned + committed per `iac terraform` run. `prd/` + `scratch/`, `.gitignore` excludes `*.backup`. Private. *(Superseded: state is now served through the `terraform-backend-git` http backend and sops+age-encrypted at rest — see `docs/runbooks/iac-agent.md`.)*

- **`pvginkel/Ansible`**:
  - `terraform/prd/vms.tf` — new `srviac` entry (VMID 920, `pve`, background, 2 vCPU / 3 GiB / 32 GiB, vmbr0 dynamic via `homelab_dns_reservation`, deterministic MAC `02:A7:F3:03:98:00`).
  - `terraform/prd/.terraform.lock.hcl` — extra `h1:` for the in-image build of `pvginkel/homelab`.
  - `terraform/prd/terraform.tfvars.example` — documents the dual flow: workstation uses local `terraform.tfvars`; srviac uses `TF_VAR_*` env vars exported by `iac-impl` from `secrets.yaml`.
  - `ansible/playbooks/site.yml` — first play excludes `k8s_prd:k8s_dev:ceph_prd` at the play level; microk8s play dropped; new `hosts: iac_agent` play applies the new role.
  - `ansible/roles/iac_agent/` — Docker engine + insecure-registry daemon.json, secrets-file placement (`force: no` guard, fails loudly on a fresh host until the operator hand-edits), `pvginkel` → `docker` group, rsync sync of `/work/IaCAgent` to `/opt/IaCAgent`, runs `install.sh` via handler. `meta: flush_handlers` after the daemon.json drop so a first-run secrets-gate failure can't strand the Docker restart.
  - `ansible/roles/baseline/` — installs + enables `prometheus-node-exporter` universally. New `baseline_os_update_class` var (`cluster` default = purge unattended-upgrades; `standalone` = install + auto-reboot at `baseline_unattended_reboot_time`). `srviac` runs the standalone class.
  - `ansible/roles/managed_filesystems/tasks/main.yml` — `delegate_to` defaults to `inventory_hostname` so the role can no-op on hosts without a `pve_node` (PVE hosts themselves).
  - `ansible/ansible.cfg` — `ssh_args` adds `IdentityFile=~/.ssh/id_ed25519_ansible` + `IdentitiesOnly=yes` so the iac container's root user can SSH to managed hosts as `ansible@`.
  - `ansible/inventories/prd/hosts.yml` — new `iac_agent` group with `srviac`; included under `managed` + `pve_vms`. `openbao` placeholder removed pending Phase 2's deployment-shape decision.
  - `ansible/inventories/prd/host_vars/srviac.yml` — `vm_id: 920`, `pve_node: pve`, `workload_class: background`.
  - `ansible/inventories/prd/group_vars/iac_agent.yml` — `baseline_os_update_class: standalone`.
  - `docs/runbooks/iac-agent.md` — operator-facing runbook (cutover sequence, day-to-day, recovery, secret rotation).

- **`pvginkel/DockerImages`** — the modern-app-dev role for iac transitioned to a dedicated, slimmer image at `registry:5000/iac:latest` with `/app/.venv` pre-built from `pyproject.toml` + `poetry.lock` at build-time. iac-impl no longer runs `poetry install` per call; PATH puts the baked venv first via the image's `ENV`.

- **`pvginkel/HelmCharts`** — Prometheus scrape targets added for the fleet (operator-side, separate commit; see the `feedback_prometheus_scrape_on_new_host` memory note).

## Operationally useful afterwards

- **`docs/runbooks/iac-agent.md`** is the live operational doc — cutover sequence, day-to-day operator workflow, recovery paths, secret-rotation steps. Read it before mutating srviac.

- **The iac contract**:
  - `iac` — interactive bash inside the iac container.
  - `iac -c '<shell script>'` — single inline script under one lock.
  - `iac -v -c '<shell script>'` — same, with iac-impl's setup-progress prints.
  - One call = one lock. Compose multi-step pipelines into a single `iac -c '…'`; don't chain.

- **Carve-outs that survive cutover**:
  - The operator workstation is reserved for srviac mutation + break-glass. Routine TF/Ansible goes through `iac`.
  - `iac-on-push` always passes `--limit '!iac_agent'` — the orchestrator must not re-apply itself.
  - For agent-VM mutation: `cd terraform/prd && terraform apply` (workstation) → `cd ansible && poetry run ansible-playbook playbooks/site.yml --diff --limit srviac` (workstation). The workstation's `ansible.cfg` `IdentityFile` resolves the same path under its `$HOME`.

- **Pending iac image rebuild signal**: a `poetry.lock` change in `pvginkel/Ansible` requires a corresponding iac image rebuild. The next `iac` call after a push (and before the rebuild lands in the registry) emits a loud `iac-impl: WARNING — /work/Ansible/poetry.lock differs from /app/poetry.lock` line on stderr. Most calls still succeed — but if you're running a play that touches the changed deps, wait for the rebuild and re-pull.

- **`secrets.yaml` is operator-curated, root-owned, mode 0600.** Plaintext on disk and on the wire to backup-server is the conscious tradeoff documented in `decisions.md` "OpenBao backup / DR". Phase 2 (OpenBao) shrinks this file to just the Bao admin token + AppRole bootstrap.

## What didn't land in this phase

- **`lifecycle.prevent_destroy` on the VM resource.** HCL requires it to be a static literal; per-VM protection means either a sibling `managed-vm-protected` module or making it universal (which breaks the existing `terraform apply -replace=<vm>` k8s rebuild flow). Operator decision was to rely on the on-push job's plan-stage destroy check (`check-protected-vms.sh srviac`) and skip the lifecycle layer. Revisit when Phase 2 lands and the protected-VM count grows.

- **Whitelist refactor of `site.yml`.** Phase 1 added the first exclusion (`!k8s_prd:!k8s_dev:!ceph_prd`); the larger structural question — does `site.yml` still make sense as exclusions accumulate? — is carved into [`slices/site-yml-layout.md`](../../slices/site-yml-layout.md) as an open question for the analyst. No proposed direction.

- **Retirement of "from-workstation" notes in operator runbooks.** `adoption.md`, `disk-resize.md`, `k8s-rebuild.md`, `k8s-upgrade.md`, `vm-rebuild.md`, `scratch-vm.md` still describe their flows as `wrkdev`-driven. Backlog item recorded under `decisions.md` "Production execution model" → "Deferred / revisit".
