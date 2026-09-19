# internal_tls leaf certs have no scheduled renewal

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Major

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Nothing renews the internal_tls step-ca leaf certificates on a schedule. iac-scheduled-certs only runs playbooks/renew-host-certs.yml — SSH host certs. The internal_tls leaves are converged only by site.yml under the manual iac-apply.

Consumers: proxmox_host (/etc/pve/local/pveproxy-ssl.pem on pve, pve1, pve2), microk8s (apiserver homelab cert), openbao.

Surfaced 2026-08-30. The PVE leaves (notAfter Sep 10 2026) crossed the 14-day renewal threshold on 27 Aug, and the daily drift job failed on a latent check-mode bug instead of reporting it. That bug is fixed in 2ec9d0f, so drift now reports a due renewal as changed — visible, but drift is --check-only and structurally cannot sign, so the renewal itself still needs a hand.

Likely shape: a playbook plus a stage in Jenkinsfile.iac-scheduled-certs, mirroring the weekly-run / 14-day-window logic already used for the SSH host certs. Needs a call on which hosts and groups it covers.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 8/30/2026, 7:30:41 AM
Triaged 2026-08-30 — Major, ruled `agreed`. Absorbed into slice 016 (`AnsibleSpecs/slices/backlog/016_internal_tls_scheduled_renewal/`); tracked on Kanban as [016]. Archiving.

Carried forward as open questions for refinement, not decided at triage: which hosts and groups the renewal covers, and whether a weekly job may bounce the prd control plane (the microk8s leaf notifies `Restart microk8s kubelite`).

### Jeeves (@jeevesginbov) - 8/30/2026, 7:29:16 AM
Triage research — 2026-08-30

Concretely this is **10 leaves on 10 hosts across three convergence paths**, not the one site.yml path the card describes:

- pveproxy `/etc/pve/local/pveproxy-ssl.pem` — pve, pve1, pve2 — `site.yml` Play 2 (`hosts: proxmox`)
- kube-apiserver homelab SNI `homelab-api.crt` — srvk8s1, srvk8s2, srvk8s3 — `site-k8s.yml --limit k8s_prd`
- same, dev — srvk8sdev — `site-k8s.yml --limit k8s_dev`
- OpenBao listener `/etc/openbao/tls/tls.crt` — srvvault1, srvvault2, srvvault3 — `site-openbao.yml`

srvk8s4 is `microk8s_worker_only: true` (inventories/prd/host_vars/srvk8s4.yml:11) — no kube-apiserver, so no SNI leaf. It is the one host in the k8s groups that drops out.

Two facts for the planner:

1. internal_tls is `include_role`'d from **inside** consumer roles, with the per-inclusion vars (SANs, paths, owner/mode, handler) at the call site — roles/microk8s/tasks/internal_tls.yml:11-23, roles/openbao/tasks/internal_tls.yml:2-15, roles/proxmox_host/tasks/main.yml:28-40 (inline, no separate task file unlike the other two). A renewal playbook cannot reach a leaf without re-declaring those vars, sharing the per-consumer task file, or driving site*.yml by tag.
2. Blast radius differs from the SSH-cert job it would mirror. ssh_host_cert notifies nothing; these notify `Restart microk8s kubelite` (the handler's own comment says roll one node at a time, serial: 1), `Reload pveproxy`, `Reload openbao`.

Also corrected while surveying, and not part of this card's remaining ask: roles/internal_tls/README.md and AnsibleSpecs decisions.md (two bullets) both claimed threshold-gated re-issue "runs on every iac-scheduled-drift cycle". Drift runs through check-ansible-drift.sh, which hard-codes --check, and issue.yml skips issuance under check mode. Fixed in Ansible d5d4a32 and AnsibleSpecs a9fc414.

Out of scope, named so it is not swept in: root CA and intermediate (manual ceremony by design), microk8s's own internal PKI (snap-managed), Proxmox's own pve-ssl.*, in-cluster cert-manager/ACME leaves (HelmCharts).

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/ZPwdycpy/737-internaltls-leaf-certs-have-no-scheduled-renewal
- **Short URL**: https://trello.com/c/ZPwdycpy

---
*Last Activity: 8/30/2026, 7:30:43 AM*
*Card ID: 6a93d84406c6d522da3fbf56*
