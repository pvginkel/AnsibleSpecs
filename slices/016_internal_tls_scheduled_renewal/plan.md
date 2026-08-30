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
`include_role`'d from *inside* three different consumer roles; settling that sets the pattern
and reaches into all three of those roles, and the change lands across two components — the
`ansible` roles/playbooks and the root-level `Jenkinsfile.iac-scheduled-certs`.

## Ordering constraints

None beyond producers-before-consumers. The Sep 10 PVE expiry was considered as an ordering
constraint and deliberately ruled out (see the ruling above).

### P1 — Every internal_tls leaf is declared once, and the reloads it triggers limit their own blast radius

Target: ansible

**Outcome.** Each of the three `internal_tls` consumers hands its leaf out as a single importable
declaration — SAN list, install paths, owner/group/mode, reload handler **and** the condition
deciding whether this host has that leaf at all — so a second driver can reach any of the ten
leaves without restating a word of it. And the reloads those declarations notify carry their own
blast-radius limit, instead of documenting one as a precondition every caller is trusted to have
arranged separately. What `site.yml`, `site-k8s.yml` and `site-openbao.yml` converge is unchanged.
This phase is what lets P2 exist without a second copy of anything.

Constraints the repo will not tell you:

- **The proxmox_host leaf has no task file to import.** It is inline at
  `roles/proxmox_host/tasks/main.yml:28-40`, unlike the other two
  (`roles/microk8s/tasks/internal_tls.yml:11-23`, `roles/openbao/tasks/internal_tls.yml:2-15`).
  The pmxcfs ownership note living with it (`:18-27`) is load-bearing and travels with the
  declaration.

- **The microk8s eligibility condition lives one level above the file that would be imported.**
  `roles/microk8s/tasks/internal_tls.yml` carries no `when:` at all; what keeps `srvk8s4` out is
  at `roles/microk8s/tasks/main.yml:120-126` — `_microk8s_installed.stat.exists`,
  `microk8s_apiserver_homelab_sans | length > 0`, `not (microk8s_worker_only | bool)`. The ruling
  moves it down into the task file so the renewal path *imports* it. The catch: `_microk8s_installed`
  is a fact registered at `roles/microk8s/tasks/main.yml:33` and read by fifteen further tasks in
  that same file, so it does not exist when the task file is entered on its own. The condition has
  to be right on both entry paths while still being one condition — a second copy of it is the
  thing this phase exists to prevent.

- **One node's kubelite down at a time, made real rather than assumed.** The `Restart microk8s
  kubelite` handler (`roles/microk8s/handlers/main.yml:40-49`) names "Roll one node at a time
  (serial: 1)" as a precondition its callers arrange; the only thing arranging it today is
  `playbooks/site-k8s.yml:52`. The operator's ruling requires the guarantee on the renewal path
  too, and re-expressing it on each new play is precisely the declared-in-two-places failure the
  leaf declarations are being cured of — so it belongs with the thing that does the restarting.
  Three facts it has to be built against:

  - `serial:` is not available as the mechanism (next bullet).
  - `ansible.builtin.systemd` with `state: restarted` returns once systemd has started the unit,
    not once the node's kube-apiserver answers again — tens of seconds later. "One at a time" that
    does not wait for the previous node to be serving again still takes the whole prd control plane
    down at once, which is the thing the ruling made conditional. Under `site-k8s.yml`'s serial the
    recovery gap is covered incidentally, by the minutes of the *next* host's converge; a renewal
    play has no such tail.
  - the handler is notified from worker nodes too — `roles/microk8s/tasks/kubelet-args.yml:47,54,61,71`,
    imported under a gate on `microk8s_manage_kubelet_resources` and *not* on `microk8s_worker_only`
    (`roles/microk8s/tasks/main.yml:149-152`) — and a worker's kubelite runs no apiserver. Whatever
    "serving again" is taken to mean has to mean something on a worker as well.

- **Why `serial:` is not the mechanism.** With `serial:` set, Ansible ends the play as soon as one
  whole batch fails: the batch's new failed-plus-unreachable count is compared against the batch
  size unconditionally, so at batch size 1 a single failed or unreachable host stops every later
  batch. (Verified this pass against the pinned ansible-core — 2.20.5, `poetry.lock:38-39` — in the
  *installed package*, not this repo: `ansible/executor/playbook_executor.py:188-195`.)
  `max_fail_percentage` cannot buy it back: that check only ever *adds* an earlier break
  (`ansible/plugins/strategy/linear.py:336-350`). Nor does "arrange for the host never to fail" —
  a handler failure is raised outside any `block`/`rescue`, so the wedged-node case the ruling is
  about is exactly the one that would still end the play.
  `playbooks/renew-host-certs.yml:43-47` is the repo already knowing this and carrying no `serial:`.
  The property is nonetheless buildable out of stock parts: Ansible's per-task concurrency cap is a
  plain field attribute on the shared task base (`ansible/playbook/base.py:709`) and handlers are
  queued through the same path that honours it (`ansible/plugins/strategy/__init__.py:341-359`), so
  a limit expressed on a handler is real. Which parts to use is yours; the two properties are not.

- **The OpenBao reload keeps the property its converge path holds today.**
  `playbooks/site-openbao.yml:171` serializes the openbao converge on apply, and the renewal path
  notifies `Reload openbao` — a SIGHUP (`roles/openbao/handlers/main.yml:13-18`) — on all three
  Raft peers. Per the ruling the three peers must never take it at once. The same reasoning applies:
  copying `site-openbao.yml:171`'s idiom onto a renewal play would import the `serial:` trap above,
  so the limit belongs with the reload. `Reload pveproxy` (`roles/proxmox_host/handlers/main.yml:2-8`)
  needs nothing of the kind — no ruling asks for it and there is no existing property to keep.

- **A no-op on the paths that already serialize.** `site-k8s.yml:52` and `site-openbao.yml:171`
  serialize on apply and fan out under `--check`; the new limits must be redundant there rather
  than contradictory — no added cost or failure on the daily `--check` drift run, and
  `rebuild-k8s.yml` and `update-k8s.yml`, which notify the same kubelite handler, keep working.

**Done (P1).** Each leaf is declared once, and both reloads carry their own blast-radius limit.

- `roles/proxmox_host/tasks/internal_tls.yml` extracted, pmxcfs ownership note travelling with it;
  `main.yml` imports it. `roles/openbao/tasks/internal_tls.yml` already was one file — untouched.
- microk8s: the eligibility gate (`_microk8s_installed.stat.exists`, non-empty
  `microk8s_apiserver_homelab_sans`, `not microk8s_worker_only`) is now a block-level `when:` in
  `tasks/internal_tls.yml`; `main.yml`'s import carries no `when:`. The stat moved to
  `tasks/check-installed.yml`, imported by both, so the fact is registered on whichever path
  reaches it and the repo still holds one stat task — it just runs twice on the converge path.
- Verified offline against the real role on localhost: microk8s absent → skip, `worker_only: true`
  → skip (the srvk8s4 case), empty SAN list → skip, eligible → enters `internal_tls`.
- `Restart microk8s kubelite` is one shell task — `systemctl restart` plus a wait until this node
  answers its own readiness endpoint — with `throttle: 1`. `throttle`, not `serial:`, is the
  mechanism, and it had to stay one task: proved locally that a throttled handler runs strictly
  one host at a time and holds the slot for the whole task, that a host whose handler fails does
  not stop the others (recap `failed=1`, peers `ok`, exit 2), and that Ansible runs each handler
  across every notified host before starting the next — so restart-then-wait as two handlers would
  restart every node before waiting on any.
- Readiness endpoint is per node class, verified live on srvk8s1/2/3 and srvk8s4: `16443/livez`
  where kubelite binds it, kubelet healthz `127.0.0.1:10248` on a worker, where 16443 belongs to
  the separate apiserver-proxy daemon and answers while the local kubelite is down. Budget:
  `microk8s_kubelite_ready_timeout: 180`.
- `Reload openbao` carries `throttle: 1`: the three Raft peers never take the SIGHUP at once.
- Drift is unaffected: under `--check` the shell handler is skipped where the systemd module used
  to report `changed`, so no restart and no cost, while the notifying task still reports `changed`
  — which is what `check-ansible-drift.sh` greps. Nothing else about the converge paths changed.
- `proxmox_host/README.md:55` claims drift renews the leaf; filed as close-out B2 for the doc phase
  because it sits outside this slice's diff.

### P2 — One playbook renews every internal_tls leaf in the fleet

Target: ansible

**Outcome.** A playbook under `ansible/playbooks/` renews every `internal_tls` leaf — safe to run
at any time, a fast `changed=0` when nothing is due. After it, renewing a leaf never needs a
hand-started `iac-apply`. It is the producer P3 consumes; on its own it already closes the
"structurally cannot sign" half of R1.

**Coverage** is the ruling's ten leaves on ten hosts: pveproxy on `pve`, `pve1`, `pve2`; the
kube-apiserver homelab SNI leaf on `srvk8s1`, `srvk8s2`, `srvk8s3` and `srvk8sdev`; the OpenBao
listener leaf on `srvvault1`, `srvvault2`, `srvvault3`. `srvk8s4` drops out — worker-only, no
kube-apiserver, no leaf — and it drops out through the converge path's own expression, the one P1
moved into the microk8s task file, not through a host pattern or a `when:` written here.

Constraints the repo will not tell you:

- **Reach each leaf through P1's declaration, restating none of it.** Every SAN list, install path,
  owner/group/mode and reload handler stays declared exactly once. A second copy drifts in silence:
  a pveproxy leaf reinstalled `root:root` on pmxcfs, or a leaf signed for last quarter's SANs.
  Entering a role at an alternate task entry point is what carries the role's defaults, vars and
  handlers along with the tasks — the reason P1's extraction is a *role* task file and not a loose
  include. All three are now reached the same way, `tasks_from: internal_tls`; microk8s's file
  stats the install itself and carries the eligibility gate, so the play needs no `when:` and no
  host pattern of its own. One asymmetry: openbao's file expects `openbao_tls_dir` to exist, which
  `dirs.yml` makes on the converge path — a never-converged host therefore fails loudly at
  issuance rather than being silently skipped.

- **Per-host independence, exactly as the prior art states it.** `playbooks/renew-host-certs.yml:43-47`
  gives both the property and the reason: renewal is per-host and independent, so one unreachable or
  wedged host must not stop the others from being renewed, and a host that fails still fails the run
  so the pipeline pages. The operator's ruling requires that here alongside the one-at-a-time
  guarantee — which is why P1 put the guarantee with the reloads. A run that renews eight leaves and
  fails on two must renew those eight *and* exit non-zero.

- **Handlers must actually fire on this path.** A renewal that installs a new leaf without reloading
  its consumer leaves the service on the old certificate until something unrelated restarts it.
  `Reload pveproxy`, `Reload openbao` and `Restart microk8s kubelite` are the three.

- **No Terraform in the path.** `playbooks/site-openbao.yml:35-140` opens with a localhost play that
  runs `terraform init` + `terraform output` to stage a pre-certificate `known_hosts`. The srvvaultN
  hosts carry signed SSH host certificates now, and `playbooks/renew-host-certs.yml:40` already
  reaches them weekly over the plain `ansible.cfg` args. Making a weekly cert job depend on a warm
  Terraform working directory and Proxmox credentials adds a failure mode for nothing.

- **Scopable into the two halves P3 needs** — everything but `k8s_dev`, and `k8s_dev` alone — the way
  `Jenkinsfile.iac-scheduled-certs:73` and `:100` cut the SSH host-cert run. `k8s` is `k8s_prd` plus
  `k8s_dev` in the one inventory (`inventories/prd/hosts.yml:119-122`).

- **Credentials are already wired.** Issuance mints its token controller-side against the repo's root
  copy (`roles/internal_tls/tasks/issue.yml:106-157`), mirroring
  `roles/ssh_host_cert/tasks/issue.yml:100-158`, which this same job already runs every week; the
  vaulted password is the one var both use (`roles/ssh_host_cert/defaults/main.yml:36`,
  `inventories/prd/group_vars/all/vips.yml:53`). Nothing new is owed to the iac agent.

- **The window arithmetic this has to satisfy.** Leaves live `1128h` = 47 days
  (`docs/runbooks/step-ca-bootstrap.md:121-127`) and re-issue inside the last 14
  (`roles/internal_tls/defaults/main.yml:21`), so something must reach every leaf at least every
  33 days. Same arithmetic the SSH host certs' weekly cadence was sized against.

- **Keep the expiry metric published on every invocation.** `roles/internal_tls/tasks/metric.yml:1-11`
  publishes the leaf's not-after on every run, not only on issuance; do not narrow it to the issuing
  case. Per the ruling it earns **no** detection claim here — no alert rule exists over it, and on
  the four k8s leaves nothing is written at all for want of a node-exporter textfile dir
  (`roles/internal_tls/tasks/metric.yml:23-32`). It stays because it is correct, not because
  anything rests on it. What detects a stalled renewer is the weekly build's own red-or-unstable
  signal, which is P3's.

- **`site.yml`, `site-k8s.yml` and `site-openbao.yml` converge exactly what they converge today.**

Prior art for both the shape and the documentation standard: `playbooks/renew-host-certs.yml:1-49`
— its header explains why scheduled renewal is its own artifact and why drift cannot stand in for
it. The new playbook earns a header of the same kind.

### P3 — The weekly certs job renews the leaves alongside the SSH host certs

Target: root

**Outcome.** `iac-scheduled-certs` renews the `internal_tls` leaves every week, in the same job and
the same Friday slot it already renews the SSH host certs in. This is what closes R1: no
hand-started `iac-apply` anywhere in the loop, and — per the ruling on what detects a stalled
renewer — the job's own red-or-unstable signal, reaching the operator through the alerting this
pipeline already uses, is the whole detector for a renewal that quietly stopped happening.

Constraints the repo will not tell you:

- **Same job, same cron — no second schedule.** `Jenkinsfile.iac-scheduled-certs:1-24` and `:48-55`
  record why certs have their own job and their own signal, and why the Friday slot is the one that
  never contends for the `iac.lock`. A second job re-opens both questions and buys nothing.

- **The dev convention the ruling names**, as it stands at `:28-43` (the bounded `devUp()` probe),
  `:87-110` and `:125-135`: a powered-off `srvk8sdev` skips the stage and takes the build
  **UNSTABLE**, never red and never a page; a dev box that is up and genuinely fails is UNSTABLE
  *and* pages. The operator picks the missed dev renewal up by hand afterwards — the job must not
  chase it, retry it later, or carry it into the next run.

- **The prd path reds the build.** A lapsed leaf breaks the Proxmox web UI, the
  `kubernetes-api.home` SNI path and the OpenBao listener — the urgency class the existing prd
  stage claims at `:64-66`. Note that with P2's per-host independence a partly-failed prd run
  completes across the healthy hosts before it exits non-zero, so the stage's red arrives at the
  end of the run rather than at the first bad host; it still has to arrive.

- **The `post` block is shared and was written for one class of certificate.** The failure
  description at `:120-124` and the `DEV_STAGE_FAILED` page gate at `:125-135` have to stay true of
  whichever stage actually failed once two classes run in one job.

- **The SSH host-cert stages keep their behaviour and run first.** A host that has lost SSH
  reachability is unreachable for everything, leaf renewal included.

### P4 — The serialization doctrine says what it now means

Target: ../AnsibleSpecs

**Outcome.** `decisions.md`'s "Cluster changes are serialized" entry is true of what this slice
ships. Today it reads as `serial: 1` *being* the rule
(`/work/AnsibleSpecs/decisions.md:26` — "No parallel mutations of k8s or Ceph nodes. `serial: 1`
plus drain/cordon hooks. Never two nodes at once."), and after P1 there is a play that mutates k8s
nodes — installs a leaf, restarts kubelite — and deliberately carries no `serial:`. The invariant
is unchanged and still absolute; what changes is that the play keyword is one way of meeting it
rather than its definition, and that for a per-host-independent job it is the *wrong* way, for the
reason P1 records. A reader planning the next cluster-touching playbook should be able to reach
the right shape from this entry rather than copy the keyword and re-import the coverage trap.

Derive the wording from what actually shipped in P1–P3, not from this plan's prose. Anything
`decisions.md` says elsewhere about serialization that the shipped diff falsifies is in scope here
too — `:294` describes the RBAC flip rolling one node at a time specifically "under
`site-k8s.yml`'s `serial: 1`", which after P1 is no longer the only thing holding it. Nothing else
in `decisions.md` is: the entry at `:145` about internal_tls monitoring is separately wrong and was
already wrong before this slice, and it is filed in the slice's close-out rather than fixed here.

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
- **Any Prometheus signal over the cert-expiry metric** — the alert rule and the in-cluster
  metric for the k8s leaves are deferred by `decisions.md`; the role keeps publishing what it
  publishes today and this slice adds, claims and alerts on nothing there.
- **Serializing the `Reload pveproxy` handler** — a graceful reload with no property to keep and
  no ruling asking for one.
- **What `site.yml`, `site-k8s.yml` and `site-openbao.yml` converge** — unchanged; this slice
  adds a renewal path beside them, it does not move work out of them.
