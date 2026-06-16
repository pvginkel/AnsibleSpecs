# Unattended dev-environment controller

**Status**: design. Concept agreed and MVP scoped (this doc); not yet
designed in detail or built. It is fundamentally a **remote
dev-environment controller**; Claude Code is a (first-class) *capability*
on top, not the core. Two services — a headless **controller API** and a
**Telegram bot** that drives it. Spans Ansible (node + pool), HelmCharts
(both services + storage + presets), DockerImages (worker image + in-pod
agent), and a small per-project config file in each managed repo.

## Goal

Run remote dev environments inside Kubernetes, with Claude as the headline
use. The controller spins up a per-project environment — repos cloned,
credentials present, optional tuned data services
(Postgres/OpenSearch/MinIO) alongside — then **leaves it idle**. Work is
**always operator-initiated**: nothing seeds a task. The worker sits in a
live tmux session until the operator **connects in** (VSCode remote tunnel
→ tmux) and starts working; execution from there may be attended or not.

Environments are defined by a **split config**: the controller owns
profiles, service presets, a secret catalog, and a project whitelist; each
project repo carries its own dev-env config file at a known location.
Everything below — capabilities, services, ports, requested secrets — is
declarative in those YAML files; nothing is hardcoded.

## Architecture — two services + a worker agent

Clean separation of concerns, so adding control surfaces later is cheap:

1. **Controller API** (headless) — the brain. Owns env state and all k8s
   orchestration: provision/teardown pods, storage subfolders, services,
   capabilities, secret materialization, LB/DNS/ports, and lifecycle
   (manual stop/delete in the MVP — no auto-reaping; see Lifecycle &
   capacity) plus an **admission gate**. Env state lives in **k8s objects
   labelled with `env-id`** — those are the source of truth, no separate
   database. It drives pods through their
   **spec, env, and lifecycle hooks — deliberately not `kubectl exec`** —
   so RBAC stays create/delete/get on pods + secrets with **no
   `pods/exec`** (which would be code-exec in any reachable pod); exec is
   reserved for ad-hoc operator actions only. Scoped k8s RBAC (namespaced
   Role/RoleBinding/SA, per the `dnsmasq` DNS-API precedent in
   HelmCharts). Has OpenBao access. **Exposes every feature as an HTTP
   API.** Push notifications leave via **callback URLs configured on the
   controller pod** — it has no knowledge of Telegram.
2. **Telegram bot** (adapter) — calls the controller API for every
   action, and exposes a callback endpoint the controller POSTs lifecycle
   events to; it renders messages + inline buttons, and button presses
   call back into the API. All Telegram specifics live here.
3. **Worker agent** (in the worker image, in each env pod) — runs the
   in-pod side of capabilities: applies setup, hosts on-request actions,
   and owns the `preStop` hooks (the `claude-code` `claude/` → CephFS
   sync). Being in-pod is deliberate — the `preStop` fires on
   **involuntary** termination too, so the sync survives evictions, and
   the controller needs no `pods/exec`. **Its shape is open**: a *thin
   runner* (logic pushed from the controller; the worker just executes)
   vs a *smart worker* exposing per-capability HTTP endpoints
   (`api/claude/…`, `api/github/…`) the controller calls. Either way it
   avoids exec. The **capability interface and this controller↔worker
   boundary are a primary spec deliverable** (see Open questions).

A future **MCP adapter** is a *sibling of the bot* — another API client —
which is exactly why the API/bot split is worth doing now. The MCP control
plane is **descoped** from the MVP; this split is the seam that keeps
re-adding it cheap. Two services is the right count; the only other
genuine seam is the worker agent (in the image / env pod), whose
thin-vs-smart shape is still open (above).

## Control surface — bot over the API

- The bot offers **/commands** for lifecycle: create an env for a
  whitelisted project, list, stop the pod, start/resume, start the editor
  tunnel (returns the link), delete the env — each translated to a
  controller API call. Exact command set TBD.
- **Push via callbacks**: the controller POSTs lifecycle events (env
  ready with links, create **blocked** by the admission gate, stop /
  delete done) to its configured callback URL(s); the bot renders them,
  with inline buttons where useful (e.g. a Delete button on a stopped
  env). The automatic-idle grace/Cancel notification flow is deferred
  (see Lifecycle & capacity).
- On env creation the bot **dumps the exposed-port links** (see below).

## Configuration model

Two layers:

- **Controller-owned** (in the controller's chart/config, versioned):
  - **Profiles** — base settings a project config extends: defaults, the
    default worker base image, the default-enabled **capabilities** (the
    "Claude dev" profile enables `claude-code` + `code-tunnel`), and the
    base env-preamble text.
  - **Service presets** — named, dev-tuned data services (`postgres`,
    `opensearch`, `minio`, …): image/version, small-dataset resources,
    init. Projects opt in by name; tuning stays centralized.
  - **Secret catalog** — named credentials mapped to OpenBao paths (like
    Jenkins credentials referenced by ID), exposed for repos to request
    by name (e.g. `openai-api-key`). The bao mapping lives here, never in
    a repo.
  - **Project whitelist** — the operator's GitHub namespace; only
    whitelisted repos can be spun up.
- **Repo-owned** — a config file at a **known location** in each project
  repo (name TBD, e.g. `.devenv.yaml`). The controller clones the
  whitelisted repo, reads it, and provisions from it. It declares:
  profile, enabled **capabilities** (e.g. `github: rw`), **services**
  (from presets, with light overrides), **requested secrets** (by name
  from the catalog — never a bao path), extra repos, setup hooks,
  preamble facts, and **exposed ports**. Tracking it in the repo versions
  the env definition alongside the project.

### Capabilities

Named, controller-understood integrations a profile/config opts into —
each bundles its OpenBao secret-sourcing, in-pod wiring (via the worker
agent), an optional env-preamble contribution, and optional lifecycle
hooks. The controller core is **dev-env-generic**; the Claude integration
is just a capability. Initial set:

- **`claude-code`** — installs/launches Claude in tmux with
  `--dangerously-skip-permissions`. Owns the rendered preamble
  (`~/.claude/CLAUDE.md`), the `claude/` storage subfolder, the CephFS
  history sync on shutdown, and `--resume` on restart. (If idle detection
  is ever added, this capability is also the natural source of an activity
  signal — session-jsonl mtime — but that's deferred.)
- **`code-tunnel`** — the VSCode remote-tunnel editor attach; started on
  request, returns the link. Separate from application ports.
- **`github`** (`none | ro | rw`) — token from OpenBao into the pod's git
  auth (`GH_TOKEN` / credential helper). Enforcement (an `ro` token can't
  push) *and* a preamble statement. `rw` is a deliberate per-env trust
  grant — pushing to real repos is a genuine side effect gated by this
  flag — tokens **fine-grained / scoped to the config's repos**.
- **Named secrets** (the plain end) — the repo requests a credential by
  **name** (e.g. `openai-api-key`); the controller resolves name →
  OpenBao path and materializes a per-env k8s Secret on each pod
  (re)start (its own k8s-auth identity + policy), deleted on teardown,
  never written to ZFS. **The repo YAML never contains OpenBao paths** —
  governance stays controller-side, like Jenkins credentials by ID.

Future capabilities (registry, cluster/kubeconfig, object store, …) follow
the same shape. Bao access is in-scope for the MVP.

## Storage layout

One env folder on the ZFS share, one subfolder per mount — most
subfolders are **contributed by a capability or service** (e.g. `claude/`
by `claude-code`, `postgres/` by the Postgres service). MVP carves them as
**hostPath subdirs** — the controller `mkdir`s on create and `rm -rf`s on
storage-teardown; no per-env Terraform:

```
<share>/<env-id>/
  workspace/    cloned repos
  claude/       ~/.claude (HOME) — from the claude-code capability
  postgres/     PGDATA            (only if the config enables it)
  opensearch/   data
  minio/        data
```

`claude/` lives on ZFS so history survives pod teardown and `--resume`
works. On **pod shutdown** the `claude-code` capability **bulk-syncs it
one-way to a CephFS RWX subvolume** (the history sink, via the
`static-cephfs-pv` module) for data-mining. The sink is the durable
archive; ZFS `claude/` is the live copy.

## Placement — share-driven affinity

A dedicated high-performance Kubernetes node (outside the control plane,
to keep these loads off E-core capacity) carries its own ZFS pool. The
**controller's Helm chart defines a share on that pool, and that share's
PV node-affinity is the single source of truth for placement** — the
controller and every worker pod inherit affinity from it. The node name
and pool name are not hardcoded anywhere in the controller or config;
swapping the share repoints everything. Node pinning is intended and
preferred here.

Mechanism reuses the established ZFS path (`static-zfs-pv` module +
`homelab_zfs_dataset` via the iac-provisioner node agent — see
[zfs-dataset-provider](completed/zfs-dataset-provider/plan.md)) and the
`vms.tf` disk-add + `zfs` role pattern to provision the pool.

## Services (data sidecars)

Per-config toggles for data services (Postgres, OpenSearch, MinIO), drawn
from the controller's service presets, each mounting its own subfolder.
They run as **native sidecars in the worker pod** (init-containers with
`restartPolicy: Always`) — non-negotiable: localhost networking, one
lifecycle, and native ordering so a service is ready before the workload
and shuts down cleanly *after* the `preStop` hooks. Presets **tune
services for dev use** — small datasets, dev/integration testing only — to
keep the per-pod footprint low; memory limits + the admission gate bound
standing cost, and the operator reclaims memory by manually `/stop`-ping
an env (easy `--resume` restart). Every env runs its **own** throwaway
sidecar; the
shared CNPG Postgres substrate
([postgres-cluster-substrate](postgres-cluster-substrate.md)) is
deliberately **not** used for dev/CI databases. If OpenSearch proves
unmanageable per-env, it (and only it) graduates to a shared service — not
separate per-env Deployments.

## Ports & networking

A config may **expose ports**. Each env gets one **LoadBalancer Service**
(MetalLB IP) fronting the worker pod, carrying the **webathome DNS
annotations** so it resolves at a semi-random `.home` name —
`<env-id>.home`, e.g. `design-assistant-a3efb1.home`. The **`env-id`**
(`<project-slug>-<6 hex>`) is the single shared label: it names the
storage folder, the DNS host, and the Service.

Each declared port carries a **type** — `http`, `https`, or `other` —
which drives the rendered URL scheme. On env creation the bot **dumps the
links** built from the exposed ports, e.g.
`http://design-assistant-a3efb1.home:5000` (`https` → `https://…`;
`other` → bare `host:port`). Each env consumes one LB IP from the pool.

The Service is **env-tier**: created at env creation and kept across pod
`/stop`+`/start` so the `.home` URL is stable; it (and its LB IP) are
released only on `/delete`. An existing env therefore holds one LB IP for
its lifetime, even while stopped.

Reuses the cluster's MetalLB LoadBalancer and the annotation-driven
`.home` DNS (dnsmasq DNS API / DNS-reservation provider). The
`code-tunnel` editor attach is separate from these application ports.

## Environment preamble (global CLAUDE.md)

The `claude-code` capability writes `~/.claude/CLAUDE.md` into the env's
`claude/` folder at provision time — Claude Code loads it as user memory
above the repo's own `CLAUDE.md`. It's **rendered**: a base preamble (from
the profile) plus per-config facts. Framing is a normal dev environment
the operator connects into to request work — **not** "you are
unattended", and **no** mention of teardown (disposability is the
controller's concern, not Claude's). Exact wording is the operator's to
fine-tune later; the durable content:

- It's a dev environment on Kubernetes; sidecars are reachable at
  `localhost` and **tuned for small dev datasets** — don't load
  production-scale data.
- Permissions are skipped (the pod is the blast radius), but anything
  reaching **outside** the pod (git push, external APIs) is real.
- Its capability/credential scope, including the **GitHub level**
  (`none`/`ro`/`rw`) and what that permits.

## Lifecycle & capacity

**No automatic cleanup in the MVP** — lifecycle is manual, in two
separable tiers:

- **Pod**: `/stop` tears the pod down (a `preStop` hook runs first — the
  `claude-code` `claude/` → CephFS sync), keeping the env folder.
  `/start` recreates the pod against the existing folder (capabilities
  re-apply; `claude-code` runs `--resume`). The `preStop` sync also fires
  on **involuntary** termination (eviction, node drain), so history isn't
  lost — this is why it lives in-pod, not in the controller.
- **Env**: `/delete` removes the whole env — pod, the env-tier Service
  (LB IP + `.home` DNS), and the storage folder.

Rather than reclaim memory by idling, the MVP **caps** it:

- Every pod carries a **memory limit** (from the profile/config).
- On a create/start request the controller runs an **admission gate**: if
  Σ(memory limits of running envs) + the new one would exceed the node's
  allocatable memory, the request is **blocked** (the bot reports why).
  The operator frees capacity by `/stop`-ping or `/delete`-ing an env.

Automatic idle teardown (TTL / LRU / grace warning) is **deferred** — the
callback model already supports the grace/Cancel/Delete notification flow
for when it's wanted, and a k8s-native scale-to-zero (KEDA) is an option.
The idle *signal* itself is also unsettled (worker-reported activity, or
the controller reading `claude/projects/` mtime off the share it mounts —
or it may not be worth having).

## MVP cut

- **Two services**: controller API (HTTP — lifecycle, k8s orchestration,
  callbacks; env state in k8s objects, no DB) + Telegram bot (commands +
  callback sink); namespaced RBAC.
- Controller config: profiles (incl. a "Claude dev" profile enabling
  `claude-code` + `code-tunnel`), the **Postgres** service preset, a
  secret catalog, project whitelist (the GitHub namespace).
- Reads the known-location repo config; **one** real project (this IaC
  repo) wired end to end with one Postgres sidecar.
- hostPath-subdir workspaces; capability/service-contributed subfolders;
  `claude/` synced to CephFS on shutdown.
- Capabilities: `claude-code`, `code-tunnel`, `github` (`none/ro/rw`),
  named secrets (e.g. `openai-api-key`) — all bao-backed.
- **Port exposure**: env-tier LoadBalancer Service + webathome `.home`
  DNS + chat links, with `http`/`https`/`other` port types.
- **Manual lifecycle** (no auto-cleanup): `/stop` (pod down, history
  synced, storage kept), `/start` (`--resume`), `/delete` (env + Service
  + storage).
- **Memory limits + admission gate**: per-pod limit; block create when
  Σ(running-env limits) + new > node capacity.

**Descoped**: the MCP adapter (the API/bot split keeps it cheap to add
later). **Deferred**: automatic idle cleanup (TTL/LRU/grace warning; a
k8s-native scale-to-zero like KEDA); dynamic per-env ZFS datasets via the
iac-provisioner API (isolation/quotas/snapshots); additional service
presets (OpenSearch/MinIO) beyond the MVP proof; multi-node spread.

## Open questions

- **Capability interface + controller/worker boundary** — the contract a
  capability implements (subfolder, requested secrets, preamble
  contribution, setup steps, lifecycle hooks) and *where its logic runs*:
  thin runner vs smart worker exposing `api/<capability>/…`. Primary spec
  deliverable.
- Known-location config filename + schema; profile/preset schema; the
  controller API surface + callback contract.
- Telegram `/command` set specifics.
- Memory-limit defaults + how node allocatable is measured for the
  admission gate.

Settled: env state = k8s objects labelled with `env-id` (no DB); Service
is env-tier; lifecycle is manual (no auto-cleanup) in the MVP.

## Repos touched

- **Ansible**: provision the dedicated node + its dev ZFS pool (disk in
  `vms.tf` + `zfs_pools` host_var) — the established pattern.
- **HelmCharts**: controller chart — **two Deployments** (controller API
  + Telegram bot) + RBAC + the ZFS share that drives affinity + the CephFS
  history sink + profiles / service presets / secret catalog / whitelist
  config.
- **DockerImages**: the worker image (extends `modern-app-dev`) **+ the
  in-pod worker agent** (shape TBD — thin runner vs smart per-capability
  API; see Architecture).
- **Each managed project repo**: a small known-location dev-env config
  file.

The per-env LoadBalancer Service + `.home` DNS annotations are emitted by
the controller and reuse existing cluster infra (MetalLB +
dnsmasq/DNS-reservation). Telegram bot infrastructure already exists in
the homelab; the bot token is an OpenBao leaf.
