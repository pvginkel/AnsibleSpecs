# 016 — Scheduled renewal for the internal_tls leaf certificates (Major)

Nothing renews the `internal_tls` step-ca leaf certificates on a schedule. The weekly
`iac-scheduled-certs` job covers SSH host certs only; the X.509 leaves are converged for
real only by a hand-started `iac-apply`, and the daily drift job is `--check`-only so it
can report a due renewal but never sign one. Close that gap.

Subsumes Trello card **#737**.

## Requirements

1. **[Major] Give the internal_tls leaves a scheduled renewal path.** From the card,
   verbatim:

   > Nothing renews the internal_tls step-ca leaf certificates on a schedule.
   > iac-scheduled-certs only runs playbooks/renew-host-certs.yml — SSH host certs. The
   > internal_tls leaves are converged only by site.yml under the manual iac-apply.
   >
   > Consumers: proxmox_host (/etc/pve/local/pveproxy-ssl.pem on pve, pve1, pve2),
   > microk8s (apiserver homelab cert), openbao.
   >
   > Surfaced 2026-08-30. The PVE leaves (notAfter Sep 10 2026) crossed the 14-day
   > renewal threshold on 27 Aug, and the daily drift job failed on a latent check-mode
   > bug instead of reporting it. That bug is fixed in 2ec9d0f, so drift now reports a due
   > renewal as changed — visible, but drift is --check-only and structurally cannot sign,
   > so the renewal itself still needs a hand.
   >
   > Likely shape: a playbook plus a stage in Jenkinsfile.iac-scheduled-certs, mirroring
   > the weekly-run / 14-day-window logic already used for the SSH host certs. Needs a
   > call on which hosts and groups it covers.

   The "likely shape" sentence is the card's own suggestion, not a ruling — the planner is
   free to land a different shape.

## Open questions for refinement

These were put to the operator at triage and are **not** settled. Bottom them out in
`/dev:plan-slice`.

1. **Which hosts and groups does the renewal cover?** The card asks for this call
   explicitly ("Needs a call on which hosts and groups it covers"). Triage narrowed it to
   a concrete set — 10 leaves on 10 hosts, three convergence paths (table below) — and
   asked the operator whether the answer is "all ten" or whether the k8s leaves should be
   held back. **The operator did not answer.** Do not read the triage table as the
   decision; it is the menu, not the choice.
2. **Is a scheduled kubelite bounce on the prd control plane acceptable?** Unlike the SSH
   host-cert job this would mirror, renewal here notifies service restarts (see
   "Blast radius" below). Whether a weekly job may bounce the prd control plane at all is
   an operator call and was flagged as such at triage; the operator did not rule on it.

## Source material

### Triage research comment on card #737, 2026-08-30 (session-authored, attributed)

Concretely this is **10 leaves on 10 hosts across three convergence paths**, not the one
`site.yml` path the card describes:

| Leaf | Cert path | Hosts | Converged by |
|---|---|---|---|
| pveproxy | `/etc/pve/local/pveproxy-ssl.pem` / `.key` | `pve`, `pve1`, `pve2` | `site.yml` Play 2 (`hosts: proxmox`) |
| kube-apiserver homelab SNI (prd) | `/var/snap/microk8s/current/certs/homelab-api.crt` / `.key` | `srvk8s1`, `srvk8s2`, `srvk8s3` | `site-k8s.yml --limit k8s_prd` |
| kube-apiserver homelab SNI (dev) | same path | `srvk8sdev` | `site-k8s.yml --limit k8s_dev` |
| OpenBao listener | `/etc/openbao/tls/tls.crt` / `tls.key` | `srvvault1`, `srvvault2`, `srvvault3` | `site-openbao.yml` |

`srvk8s4` is `microk8s_worker_only: true` (`inventories/prd/host_vars/srvk8s4.yml:11`) —
no kube-apiserver, so no SNI leaf. It is the one host in the k8s groups that drops out.

**Call sites.** `internal_tls` is `include_role`'d from *inside* consumer roles, with the
per-inclusion vars (SANs, paths, owner/group/mode, reload handler) at the call site:

- `ansible/roles/microk8s/tasks/internal_tls.yml:11-23`
- `ansible/roles/openbao/tasks/internal_tls.yml:2-15`
- `ansible/roles/proxmox_host/tasks/main.yml:28-40` — inline, with no separate task file,
  unlike the other two

A renewal playbook cannot reach a leaf without re-declaring those vars, sharing the
per-consumer task file, or driving `site*.yml` by tag.

**Blast radius.** `ssh_host_cert` notifies nothing. These three notify service
restarts/reloads: `Restart microk8s kubelite` (the handler's own comment at
`roles/microk8s/handlers/main.yml:40-49` says "Roll one node at a time (serial: 1); on prd
the apiserver VIP and the peer nodes cover the gap"), `Reload pveproxy` (graceful),
`Reload openbao` (SIGHUP).

**Out of scope, named so it is not swept in:** the root CA and intermediate (manual
ceremony by design), microk8s's own internal PKI (snap-managed), Proxmox's own
`pve-ssl.*`, and in-cluster cert-manager/ACME leaves (HelmCharts' domain). SSH host certs
are already renewed weekly by `iac-scheduled-certs`.

### Prior art the card points at

`playbooks/renew-host-certs.yml` and `Jenkinsfile.iac-scheduled-certs` — the weekly-run /
14-day-window arrangement built for SSH host certs after the July 2026 lapse. Both carry
long header comments explaining why the job is separate from `iac-scheduled-update` and
why drift cannot substitute for it. The card proposes mirroring this; the planner should
read those comments as design context, including the deliberate decision *not* to fold
certificate renewal into the OS-update roll.

### Already done, not part of this slice's ask

Two docs claimed threshold-gated re-issue "runs on every iac-scheduled-drift cycle" —
false, since drift hard-codes `--check` via `check-ansible-drift.sh` and
`internal_tls/tasks/issue.yml` skips issuance under check mode. Corrected before this
slice was filed: Ansible `d5d4a32` (`roles/internal_tls/README.md`) and AnsibleSpecs
`a9fc414` (`decisions.md`, two bullets).

## Q&A and operator rulings

- **Triage, 2026-08-30 — category.** Adjudicated **Major**, ruled `agreed` by the
  operator: *"Yes, this is fine. I'll start the slice today so there's no need to rotate
  the certs now."*
- **Triage, 2026-08-30 — the live deadline.** The PVE leaves expire **Sep 10 2026**.
  Triage offered to prepare a hand-run `iac-apply` to rotate them before then; the
  operator declined on the grounds that this slice starts today. **If the slice slips past
  ~Sep 8, that decision needs revisiting** — the leaves lapse regardless of the slice's
  state, and `internal_tls` cannot help a host whose cert has already expired.
- **Triage, 2026-08-30 — hosts and groups.** Asked, not answered. See "Open questions".
- **Triage, 2026-08-30 — scheduled kubelite bounce.** Flagged, not ruled. See "Open
  questions".
