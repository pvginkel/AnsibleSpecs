# Triage raw material — 2026-08-30

Scope: **card 737 only**, at the operator's request. The rest of the Ansible-tagged
intake queue is untouched by this run.

---

## Source 1 — Trello Triage card #737 (verbatim)

- URL: https://trello.com/c/ZPwdycpy/737-internaltls-leaf-certs-have-no-scheduled-renewal
- Card ID: `6a93d84406c6d522da3fbf56`
- Reporter: Jeeves (@jeevesginbov)
- Labels: `red` Ansible
- Due date: unset
- Members: none
- Checklists: none
- Attachments: none
- Comments: none (at fetch time)
- Last activity: 8/30/2026, 7:14:12 AM

### Title

> internal_tls leaf certs have no scheduled renewal

### Description

> Nothing renews the internal_tls step-ca leaf certificates on a schedule. iac-scheduled-certs only runs playbooks/renew-host-certs.yml — SSH host certs. The internal_tls leaves are converged only by site.yml under the manual iac-apply.
>
> Consumers: proxmox_host (/etc/pve/local/pveproxy-ssl.pem on pve, pve1, pve2), microk8s (apiserver homelab cert), openbao.
>
> Surfaced 2026-08-30. The PVE leaves (notAfter Sep 10 2026) crossed the 14-day renewal threshold on 27 Aug, and the daily drift job failed on a latent check-mode bug instead of reporting it. That bug is fixed in 2ec9d0f, so drift now reports a due renewal as changed — visible, but drift is --check-only and structurally cannot sign, so the renewal itself still needs a hand.
>
> Likely shape: a playbook plus a stage in Jenkinsfile.iac-scheduled-certs, mirroring the weekly-run / 14-day-window logic already used for the SSH host certs. Needs a call on which hosts and groups it covers.

---

## Source 2 — session discussion, 2026-08-30

The operator asked whether the card could be actioned inline and whether it is clear
from the card which certs are not being auto-renewed ("I saw more then I initially
thought would be there"). The session surveyed the repo. Findings below are **session
research**, not operator asks — they are recorded here as source material and were
posted to the card as a dated triage-research comment.

### Concrete leaf inventory — 10 leaves across 10 hosts

| Leaf | Cert path | Hosts | Converged by |
|---|---|---|---|
| pveproxy | `/etc/pve/local/pveproxy-ssl.pem` / `.key` | `pve`, `pve1`, `pve2` | `site.yml` Play 2 (`hosts: proxmox`) |
| kube-apiserver homelab SNI (prd) | `/var/snap/microk8s/current/certs/homelab-api.crt` / `.key` | `srvk8s1`, `srvk8s2`, `srvk8s3` | `site-k8s.yml --limit k8s_prd` |
| kube-apiserver homelab SNI (dev) | same path | `srvk8sdev` | `site-k8s.yml --limit k8s_dev` |
| OpenBao listener | `/etc/openbao/tls/tls.crt` / `tls.key` | `srvvault1`, `srvvault2`, `srvvault3` | `site-openbao.yml` |

`srvk8s4` is `microk8s_worker_only: true` (`inventories/prd/host_vars/srvk8s4.yml:11`) —
no kube-apiserver, so no SNI leaf. It is the one host in the k8s groups that drops out.

### The card's "converged only by site.yml" is true for 3 of 10 leaves

`site.yml` covers only the pveproxy leaves. The kube-apiserver leaves come through
`site-k8s.yml` (two separate `--limit`s, prd and dev) and the OpenBao leaves through
`site-openbao.yml`. All three run under the hand-started `iac-apply`. So the fix is
three convergence paths, not one.

### Call sites — internal_tls is `include_role`'d from inside consumer roles

Three call sites in the whole repo:

- `ansible/roles/microk8s/tasks/internal_tls.yml:11-23` — handler `Restart microk8s kubelite`
- `ansible/roles/openbao/tasks/internal_tls.yml:2-15` — handler `Reload openbao`
- `ansible/roles/proxmox_host/tasks/main.yml:28-40` — handler `Reload pveproxy` (inline, no
  separate task file, unlike the other two)

The per-inclusion vars (SAN list, paths, owner/group/mode, handler) live at the call
site. A renewal playbook cannot reach a leaf without either re-declaring those vars,
sharing the per-consumer task file, or driving `site*.yml` by tag.

### Blast radius differs from the SSH-cert job

`ssh_host_cert` notifies nothing. These three notify service restarts/reloads:
`Restart microk8s kubelite` (bounces the node's control plane and kubelet for a few
seconds; the role's handler comment says "Roll one node at a time (serial: 1)"),
`Reload pveproxy` (graceful), `Reload openbao` (SIGHUP).

### Doc drift found and fixed this session

`ansible/roles/internal_tls/README.md` and `/work/AnsibleSpecs/decisions.md` (two
bullets) both claimed threshold-gated re-issue "runs on every iac-scheduled-drift
cycle". `iac-scheduled-drift` runs through `check-ansible-drift.sh`, which hard-codes
`--check`, and `internal_tls/tasks/issue.yml` explicitly skips issuance under check
mode. Corrected in Ansible `d5d4a32` and AnsibleSpecs `a9fc414`. Not part of the
card's remaining ask.

### Out of scope, named so it is not swept in

Root CA and intermediate (manual ceremony by design), microk8s's own internal PKI
(snap-managed), Proxmox's own `pve-ssl.*`, and in-cluster cert-manager/ACME leaves
(HelmCharts). SSH host certs are already renewed weekly by `iac-scheduled-certs`.
