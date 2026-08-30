# Slice 016 — the internal_tls step-ca leaf certificates renew on a schedule, with no hand-started `iac-apply`

## Requirements / rulings

- **R1. Give the internal_tls leaves a scheduled renewal path.** From Trello card #737,
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

  The "likely shape" sentence is the card's own suggestion, **not a ruling** — a different
  shape is open, provided the outcome holds: the leaves get renewed on a schedule, with no
  hand-started `iac-apply` in the loop.

- **Ruling (2026-08-30) — which hosts and groups the renewal covers.** The operator, asked
  whether it is all ten leaves or whether the k8s leaves should be held back:

  > All. Note that dev will be down. That is not an error. Mark the build as unstable as
  > per convention. It'll mean I'll have to run the apply manually to get it back again.
  > That's acceptable.

  So all **ten leaves on ten hosts**: pveproxy on `pve`, `pve1`, `pve2`; the kube-apiserver
  homelab SNI leaf on `srvk8s1`, `srvk8s2`, `srvk8s3` and on `srvk8sdev`; the OpenBao
  listener leaf on `srvvault1`, `srvvault2`, `srvvault3`.

  "As per convention" is the arrangement `Jenkinsfile.iac-scheduled-certs` already uses for
  the SSH host certs on dev: a bounded `devUp()` reachability probe, and when `srvk8sdev` is
  unreachable the stage is skipped and the build goes **unstable**, not red. A powered-off
  dev box must not fail the build. The operator picks up the missed dev renewal by hand
  afterwards — the job is not expected to chase it.

- **Ruling (2026-08-30) — a scheduled kubelite bounce on the prd control plane.** Acceptable,
  **with `serial: 1`**: at most once per ~33 days per node, one node at a time; the apiserver
  VIP and the peer nodes cover the few-second gap and workload pods keep running.

  Load-bearing detail: `serial: 1` is **not** inherited from the role or the handler. It is
  expressed on the play in `ansible/playbooks/site-k8s.yml:52`; the `Restart microk8s
  kubelite` handler only names it as a precondition in its comment. Whatever drives the k8s
  renewal has to carry the one-node-at-a-time guarantee itself.

- **Ruling (2026-08-30) — the Sep 10 PVE expiry does not constrain phase order.** Asked
  whether the plan should sequence the proxmox_host path first so it is shippable before the
  PVE leaves lapse, the operator chose **natural ordering**: plan the phases in whatever order
  the design wants; the operator will rotate the PVE leaves by hand, out of band, if the slice
  looks like slipping past ~Sep 8. That hand-rotation is the operator's own action, not slice
  work.

## Ordering constraints

None beyond producers-before-consumers. The Sep 10 PVE expiry was considered as an ordering
constraint and deliberately ruled out (see the ruling above).

## Not in scope

- The step-ca **root CA and intermediate** — rotated by a manual ceremony, by design.
- **microk8s's own internal PKI** — snap-managed.
- **Proxmox's own `pve-ssl.*`** certificates.
- **In-cluster cert-manager / ACME leaves** — HelmCharts' domain.
- **SSH host certificates** — already renewed weekly by `iac-scheduled-certs`; this slice
  adds to that arrangement rather than changing it.
- **`srvk8s4`** — `microk8s_worker_only: true` (`inventories/prd/host_vars/srvk8s4.yml:11`),
  so it runs no kube-apiserver and has no SNI leaf. It is the one host in the k8s groups that
  drops out of the set.
- **Rotating the PVE leaves ahead of their Sep 10 expiry** — the operator's own out-of-band
  action if the slice slips.
