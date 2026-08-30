# P1 — code review, round 1

Commit under review: `c0389e659d9e` (`git diff d5d4a32..HEAD`, branch `phase/016-P1`).
Gate: green (`kc project test --project ansible` — yamllint + ansible-lint), taken as an input.

## Readiness

**Ready to merge.** The phase's two outcomes both land, and I verified the load-bearing mechanisms
independently rather than taking the done-record's word for them. Each of the three consumers now
hands its leaf out as one importable task file with nothing restated: `proxmox_host`'s is a verbatim
extraction with the pmxcfs ownership note travelling with it
(`ansible/roles/proxmox_host/tasks/internal_tls.yml:1-29`), `openbao`'s was already one file and is
untouched, and microk8s's eligibility gate moved down character-for-character from
`tasks/main.yml`'s import into a block-level `when:` in `tasks/internal_tls.yml:29-34`, with the
`stat` it reads hoisted into `tasks/check-installed.yml` so the fact exists on the standalone entry
path. I ran that standalone path — `import_role: {name: microk8s, tasks_from: internal_tls}` on
localhost — and it enters cleanly, registers the fact and skips the block on a host with no microk8s
(`ok=1 skipped=2`, rc 0), so P2 really can reach the leaf without a second copy of anything. On the
blast-radius half, I reproduced the throttled-handler behaviour against the pinned ansible-core
2.20.5 with a three-host play: handler windows are strictly non-overlapping
(`h1 069.3→072.3`, `h2 072.5→075.5`, `h3 075.7→078.7`), a host whose handler fails does **not** stop
the peers (`h2 failed=1`, `h1`/`h3` `ok=2`), and the run still exits 2 — which is exactly the
"one at a time **and** no coverage loss **and** still page" pair the operator's ruling demanded and
that `serial:` provably cannot give. I also confirmed the readiness endpoints answer unauthenticated
on both node classes live (`srvk8s1` and `srvk8s4`: `16443/livez` rc 0, `10248/healthz` rc 0, `curl`
present on both), so the wait loop is not going to hang on an auth failure. What `site.yml`,
`site-k8s.yml` and `site-openbao.yml` converge is unchanged; the drift signal is intact (checked
below). The three findings are all advisory — none of them is a reason to hold the merge.

## Findings

### F1 — the kubelite restart is now invisible to a `--check --diff` review · Minor · advisory · anchor `none`

`Restart microk8s kubelite` changed from `ansible.builtin.systemd` to `ansible.builtin.shell`
(`ansible/roles/microk8s/handlers/main.yml:60-71`). The `shell` module has no check-mode support, so
under `--check` the handler is skipped rather than reported. I ran this: a three-host play whose
notifying task is a `lineinfile` and whose handler is a throttled `shell` reports
`RUNNING HANDLER [H] skipping: [h1] [h2] [h3]` and a recap of `changed=1 skipped=1` per host. With
`display_skipped_hosts = False` (`ansible/ansible.cfg:12`) the handler line does not appear in the
operator's output at all.

The drift job is unaffected and I checked why: `support/iac-agent/bin/check-ansible-drift.sh:39-43`
sums `changed=N` out of the recap, and the notifying task (`Serve the homelab leaf as an apiserver
SNI cert`, `internal_tls.yml:47-54`; `rbac.yml:19-24`; the four `kubelet-args.yml` tasks) still
reports `changed` in check mode. So drift still reds, and the plan's "no added cost or failure on
the daily `--check` drift run" holds.

What is lost is the pre-apply review signal. `docs/design-philosophy.md` makes `--check --diff`
before an apply the standard workflow ("a role that can't be dry-run is a role that can't be
reviewed"), and the single most disruptive thing this role does — bouncing the prd control plane one
node at a time — is now the one action that a dry run does not name. An operator reading a
`--check` of `site-k8s.yml` sees three changed `lineinfile` tasks and must know from memory that they
notify a kubelite restart. Previously the handler said so itself, on each affected host.

Advisory, not blocking: the notifying tasks still surface the change, and the design-philosophy
document itself contemplates shelling out where a module will not do. But it is a real reduction in
what a dry run tells the operator, and it arrived as a side effect rather than as a decision.

### F2 — `/livez` is a liveness signal, not the "serving again" the property is stated in terms of · Minor · advisory · anchor `none`

The wait loop releases the throttle slot when `https://127.0.0.1:16443/livez` returns 2xx on an
apiserver node, or `http://127.0.0.1:10248/healthz` on a worker
(`ansible/roles/microk8s/handlers/main.yml:65,73-75`). The handler comment frames this as "the next
node goes down only once this one is serving" (`:48-51`).

Against the live prd apiserver, `/readyz?verbose` runs three checks that `/livez?verbose` does not:
`etcd-readiness`, `informer-sync` and `shutdown`. Those three are precisely the difference between
"the process is up and answering" and "this apiserver can serve requests" — so `livez` can go green
while the restarted node has not yet reached the datastore or synced its caches, and the next node's
kubelite goes down in that window.

The worker branch is weaker still. `kubelet healthz` on `127.0.0.1:10248` reports that kubelet's own
health server is up; it says nothing about the kubelet having re-registered or its node lease having
resumed. This repo has already been bitten by exactly that class of signal:
`ansible/playbooks/tasks/wait-node-ready.yml:11-28` records build #15, where a local readiness check
on `srvk8s4` "passed in 0.471s" and let the uncordon fire ~2s behind a reboot that had barely
finished — which is why that file waits on the `kube-node-lease` renewTime instead.

No harm is demonstrated and none is easy to construct: with three prd control-plane members the VIP
still has a healthy peer even if one node is live-but-not-ready while another is down, and the
plan's own wording asks only that the wait last until "the node's kube-apiserver answers again",
which `/livez` satisfies literally. Recording it because the gap between the comment's claim and the
endpoint's semantics is the kind of thing that reads as settled a year from now.

### F3 — the blast-radius limit is on `Reload openbao` but not on `Restart openbao` · Minor · advisory · anchor `none`

`Reload openbao` now carries `throttle: 1` (`ansible/roles/openbao/handlers/main.yml:23`), and its
comment states the doctrine the phase is built on: the limit "carried by the reload itself rather
than restated on each caller" (`:16-19`). Two handlers up, `Restart openbao`
(`ansible/roles/openbao/handlers/main.yml:8-11`) — a full service restart, strictly more disruptive
to the Raft peers than a SIGHUP — carries no limit and is still relying on
`playbooks/site-openbao.yml:171`'s `serial:` being arranged by whoever drives it. It is notified from
`config.yml` and `hardening.yml`, so any future driver entering the role at a task entry point that
touches either would restart all three peers concurrently.

No product consequence in this slice: the ruling asked only about the reload, and the renewal path
P2 will drive enters at `tasks_from: internal_tls`, which notifies `Reload openbao` and nothing else.
Noted once because the phase established a rule and left one handler in the same role outside it.

## Checks made that produced nothing

- **`throttle` is honoured for handlers on the pinned core.** Handlers are inlined into the linear
  strategy's task list at the `flush_handlers` meta point (`plugins/strategy/linear.py:92-93,195`)
  and queued through the same `_queue_task` that applies `throttle` by narrowing the worker rewind
  point (`plugins/strategy/__init__.py:341-359`); `ALLOW_BASE_THROTTLING` is `True` for the linear
  strategy and no play or config in this repo selects `free`. Confirmed empirically as described
  above.
- **The microk8s gate is one condition, not two.** The three `when:` clauses in
  `tasks/internal_tls.yml:29-34` are textually identical to the ones deleted from
  `tasks/main.yml:118-126`, comment included.
- **Endpoint reachability.** `curl -sfk` returns 0 for both `16443/livez` and `10248/healthz` on
  `srvk8s1` and on the worker-only `srvk8s4`, and `/usr/bin/curl` exists on both — so the new shell
  dependency and the anonymous `/livez` access the loop assumes are both real.
- **Converge parity.** `proxmox_host`'s extraction is byte-identical task content behind an
  `import_tasks`; the extra `check-installed.yml` run on the microk8s converge path re-registers the
  same fact with no reader affected; `openbao` is untouched.
- **Repo prose.** `ansible/roles/microk8s/tasks/rbac.yml:17` still attributes the one-node-at-a-time
  roll to `site-k8s.yml`'s `serial: 1`. That remains true as written (it is no longer the *only*
  thing holding it, which is P4's `decisions.md` scope), so it is not a finding here.
  `roles/proxmox_host/README.md:55` is already filed as close-out B2.
