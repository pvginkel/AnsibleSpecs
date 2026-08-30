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

- **Ruling (2026-08-30) — a scheduled kubelite bounce on the prd control plane, and what
  serializing must not cost.** The bounce is acceptable **with `serial: 1`**: at most once per
  ~33 days per node, one node at a time; the apiserver VIP and the peer nodes cover the
  few-second gap and workload pods keep running.

  Serializing **must not cost fleet-wide coverage**. Asked whether it is acceptable that a
  wedged node stops the remaining nodes being renewed, the operator ruled *no — keep both
  properties*: one node at a time, **and** a wedged or unreachable host must not stop the other
  hosts' renewals, **and** the run must still fail the build so it pages. The mechanism is the
  planner's call.

  Load-bearing details, both of which the naive reading gets wrong:

  - `serial: 1` is **not** inherited from the role or the handler. It is expressed on the play
    in `ansible/playbooks/site-k8s.yml:52`; the `Restart microk8s kubelite` handler only names
    it as a precondition in its comment. Whatever drives the k8s renewal has to carry the
    one-node-at-a-time guarantee itself.
  - `serial: 1` on its own gives the *opposite* of the coverage property above: Ansible
    defaults `max_fail_percentage` to 0 whenever `serial` is set, so every batch is one host
    and the first failed or unreachable host ends the play — the later hosts are never
    attempted. That is the silent partial coverage `playbooks/renew-host-certs.yml:43-47`
    deliberately avoids by carrying no `serial:` at all.

- **Ruling (2026-08-30) — how the renewal reaches a leaf without a second copy of its
  declaration.** **Refactor to share.** Extract a `roles/proxmox_host/tasks/internal_tls.yml`
  from the inline include at `roles/proxmox_host/tasks/main.yml:28-40`, and hoist the microk8s
  host-eligibility guard — `_microk8s_installed.stat.exists`,
  `microk8s_apiserver_homelab_sans | length > 0`, `not microk8s_worker_only`
  (`roles/microk8s/tasks/main.yml:122-126`) — into `roles/microk8s/tasks/internal_tls.yml`, so
  the renewal path *imports* that guard instead of restating it. The renewal then reaches each
  leaf through the three per-consumer task files.

  The point of the refactor is that the invariant actually holds: no SAN list, install path,
  owner/group/mode, reload handler **or host-eligibility condition** exists in two places that
  can drift apart. The two rejected alternatives were restating the microk8s guard with a
  cross-referencing comment, and tagging the three include sites to drive `site*.yml --tags`.
  This touches all three consumer roles, and the phase may need splitting to stay PR-sized.

- **Ruling (2026-08-30) — the OpenBao renewal serializes across the Raft peers.** The
  `srvvault1`, `srvvault2`, `srvvault3` renewal carries the same serial-on-apply idiom as the
  converge path at `playbooks/site-openbao.yml:171`, so the three Raft peers never take the
  `Reload openbao` SIGHUP at once. What the converge path guarantees today, the renewal path
  keeps. (Fanning out on the grounds that a listener reload never touches Raft config was
  offered and rejected.)

- **Ruling (2026-08-30) — what detects a stalled renewer.** The operator:

  > The weekly build. Besides that, we do have an alert mechanism that allows pipelines to
  > raise alerts that I get in a Telegram app. Assume that that'll go into the Prometheus feed
  > also at some point, although that shouldn't matter too much for now.

  So the detector is a **red or unstable `iac-scheduled-certs`**, reaching the operator through
  the pipeline alerting the job already uses — exactly the arrangement that backs the SSH host
  certs. The plan must **not** rest any claim on a Prometheus stalled-renewer signal: the alert
  rule is deferred (`/work/AnsibleSpecs/decisions.md:145`) and `metric.yml` publishes nothing
  at all on the four k8s leaves, which have no node-exporter textfile dir. Keeping the expiry
  metric published on every invocation rather than only on issuance is still correct and stays
  in — it just earns no detection claim here.

- **Ruling (2026-08-30) — the Sep 10 PVE expiry does not constrain phase order.** Asked
  whether the plan should sequence the proxmox_host path first so it is shippable before the
  PVE leaves lapse, the operator chose **natural ordering**: plan the phases in whatever order
  the design wants; the operator will rotate the PVE leaves by hand, out of band, if the slice
  looks like slipping past ~Sep 8. That hand-rotation is the operator's own action, not slice
  work.

## Task shape

cross-cutting — slice.md leaves the mechanism open (the card's "likely shape" is explicitly
"not a ruling") and its triage note names three mutually exclusive ways to reach a leaf that is
`include_role`'d from *inside* three different consumer roles; settling that sets the pattern, and
the change lands across two components — the `ansible` playbooks/roles and the root-level
`Jenkinsfile.iac-scheduled-certs`.

## Ordering constraints

None beyond producers-before-consumers. The Sep 10 PVE expiry was considered as an ordering
constraint and deliberately ruled out (see the ruling above).

### P1 — A renewal playbook that reaches every internal_tls leaf

Target: ansible

**Outcome.** One playbook under `ansible/playbooks/` renews every `internal_tls` leaf in the
fleet — safe to run at any time, a fast `changed=0` when nothing is due. After it, renewing a
leaf never needs a hand-started `iac-apply`. It is the producer P2 consumes; on its own it
already closes the "structurally cannot sign" half of R1.

**Coverage** is the ruling's ten leaves on ten hosts: pveproxy on `pve`, `pve1`, `pve2`; the
kube-apiserver homelab SNI leaf on `srvk8s1`, `srvk8s2`, `srvk8s3` and `srvk8sdev`; the OpenBao
listener leaf on `srvvault1`, `srvvault2`, `srvvault3`. `srvk8s4` drops out — worker-only, no
kube-apiserver, no leaf.

Constraints the repo will not tell you:

- **One source of truth per leaf.** The SAN list, install paths, owner/group/mode and reload
  handler are declared today at the three inclusion sites — `roles/microk8s/tasks/internal_tls.yml:11-23`,
  `roles/openbao/tasks/internal_tls.yml:2-15`, and inline with no task file of its own at
  `roles/proxmox_host/tasks/main.yml:28-40`. A renewal path that re-states any of them is a
  second copy that drifts in silence: a pveproxy leaf reinstalled `root:root` on pmxcfs, or a
  leaf signed for last quarter's SANs. The same holds for the conditions that keep the leaf off
  a worker node (`roles/microk8s/tasks/main.yml:120-126`) — whatever keeps `srvk8s4` out must be
  the expression the converge path uses, not a parallel one that can disagree with it.
- **The k8s renewal carries `serial: 1` itself.** It is not inherited from the role or the
  handler: it is expressed on the play at `playbooks/site-k8s.yml:52`, and the `Restart microk8s
  kubelite` handler only names it as a precondition in its comment
  (`roles/microk8s/handlers/main.yml:40-49`). Without it a run bounces the whole prd control
  plane at once — which is the thing the operator's ruling made conditional.
- **Handlers must actually fire on this path.** A renewal that installs a new leaf without
  reloading its consumer leaves the service on the old certificate until something unrelated
  restarts it. `Reload pveproxy`, `Reload openbao` (SIGHUP) and `Restart microk8s kubelite` are
  the three, and the microk8s one is the reason for the constraint above.
- **No Terraform in the path.** `playbooks/site-openbao.yml:35-140` opens with a localhost play
  that runs `terraform init` + `terraform output` to stage a pre-certificate `known_hosts`. The
  srvvaultN hosts carry signed SSH host certificates now, and `playbooks/renew-host-certs.yml:40`
  already reaches them weekly over the plain `ansible.cfg` args. Making a weekly cert job depend
  on a warm Terraform working directory and Proxmox credentials adds a failure mode for nothing.
- **Scopable into the two halves P2 needs** — everything but `k8s_dev`, and `k8s_dev` alone —
  the way `Jenkinsfile.iac-scheduled-certs:67-110` cuts the SSH host-cert run.
- **Credentials are already wired.** Issuance mints its token controller-side against the repo's
  root copy (`roles/internal_tls/tasks/issue.yml:106-157`), mirroring
  `roles/ssh_host_cert/tasks/issue.yml:100-158`, which this same job already runs every week; the
  vaulted password is the one var both use (`roles/ssh_host_cert/defaults/main.yml:36`,
  `inventories/prd/group_vars/all/vips.yml:53`). Nothing new is owed to the iac agent.
- **The window arithmetic this has to satisfy.** Leaves live `1128h` = 47 days
  (`docs/runbooks/step-ca-bootstrap.md:121-127`) and re-issue inside the last 14
  (`roles/internal_tls/defaults/main.yml:21`), so something must reach every leaf at least every
  33 days. Same arithmetic the SSH host certs' weekly cadence was sized against.
- **Keep the expiry metric on every run.** `roles/internal_tls/tasks/metric.yml:1-11` publishes
  the leaf's not-after on every invocation, not only on issuance — so a renewal run also refreshes
  the Prometheus signal that would catch a stalled renewer. Do not narrow it to the issuing case.
- **`site.yml`, `site-k8s.yml` and `site-openbao.yml` converge exactly what they converge today.**

Prior art for both the shape and the documentation standard: `playbooks/renew-host-certs.yml:1-49`
— its header explains why scheduled renewal is its own artifact and why drift cannot stand in for
it. The new playbook earns a header of the same kind.

### P2 — The weekly certs job renews the leaves alongside the SSH host certs

Target: root

**Outcome.** `iac-scheduled-certs` renews the `internal_tls` leaves every week, in the same job
and the same Friday slot it already renews the SSH host certs in. This is what closes R1: no
hand-started `iac-apply` anywhere in the loop.

Constraints the repo will not tell you:

- **Same job, same cron — no second schedule.** `Jenkinsfile.iac-scheduled-certs:1-24` and
  `:48-55` record why certs have their own job and their own signal, and why the Friday slot is
  the one that never contends for the `iac.lock`. A second job re-opens both questions and buys
  nothing.
- **The dev convention the ruling names**, as it stands at `:28-43` (the bounded `devUp()`
  probe), `:87-110` and `:125-135`: a powered-off `srvk8sdev` skips the stage and takes the build
  **UNSTABLE**, never red and never a page; a dev box that is up and genuinely fails is UNSTABLE
  *and* pages. The operator picks the missed dev renewal up by hand afterwards — the job must not
  chase it, retry it later, or carry it into the next run.
- **The prd path reds the build.** A lapsed leaf breaks the Proxmox web UI, the
  `kubernetes-api.home` SNI path and the OpenBao listener — the urgency class the existing prd
  stage claims at `:64-66`.
- **The `post` block is shared and was written for one class of certificate.** The failure
  description at `:120-124` and the `DEV_STAGE_FAILED` page gate at `:125-135` have to stay true
  of whichever stage actually failed once two classes run in one job.
- **The SSH host-cert stages keep their behaviour and run first.** A host that has lost SSH
  reachability is unreachable for everything, leaf renewal included.

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
- **A second scheduled job or a new cron slot** — the leaf renewal rides the existing weekly
  certs job; the reasons are in `Jenkinsfile.iac-scheduled-certs:1-24` and `:48-55`.
- **The 14-day renewal threshold and the 47-day leaf lifetime** — both stay as they are
  (`roles/internal_tls/defaults/main.yml:21`, `docs/runbooks/step-ca-bootstrap.md:121-127`).
- **Prometheus alert rules over the cert-expiry metric** — the role keeps publishing it
  (`roles/internal_tls/tasks/metric.yml`); what alerts on it is not touched here.
- **What `site.yml`, `site-k8s.yml` and `site-openbao.yml` converge** — unchanged; this slice
  adds a renewal path beside them, it does not move work out of them.
