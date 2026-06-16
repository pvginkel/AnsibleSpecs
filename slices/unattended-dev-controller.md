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
   capabilities, secret materialization, LB/DNS/ports, and the lifecycle
   loop (idle detection, grace, reaping). It drives pods through their
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
3. **Worker agent** (in the worker image) — deliberately **thin**: an
   entrypoint + a `preStop` hook + a small listener for on-request
   actions (a runner, not a bespoke daemon). It carries almost **no
   feature logic of its own** — it's a **generic capability runner**:
   each capability (clone, `claude-code`, `code-tunnel`, `github`, …)
   supplies the in-pod steps and hooks the agent executes, so the worker
   stays small even as capabilities grow. Being in-pod (rather than
   exec-driven) is what makes the `preStop` hook fire on **involuntary**
   termination too, so the `claude/` → CephFS sync survives evictions.
   Ships in the image, but the controller↔worker contract is a real
   boundary.

A future **MCP adapter** is a *sibling of the bot* — another API client —
which is exactly why the API/bot split is worth doing now. The MCP control
plane is **descoped** from the MVP; this split is the seam that keeps
re-adding it cheap. Two services is the right count; the only other
genuine seam is the worker agent, and it lives in the image.

## Control surface — bot over the API

- The bot offers **/commands** for lifecycle: create an env for a
  whitelisted project, list, stop the pod, start/resume, start the editor
  tunnel (returns the link), delete the env — each translated to a
  controller API call. Exact command set TBD.
- **Push via callbacks**: the controller POSTs lifecycle events to its
  configured callback URL(s); the bot turns them into messages with
  inline buttons:
  - Idle TTL reached → "Env X shuts down in 15 min" + **Cancel** →
    extends the timeout by another full TTL (API call).
  - On shutdown → **edit that message in place** → "Env X shut down" +
    **Delete** → removes the env, storage tier (API call).
  - Editing one message keeps the thread clean: warning → shutdown →
    tombstone.
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
  history sync on shutdown, `--resume` on restart, and the idle signal
  (session-jsonl mtime).
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
keep the per-pod footprint low; LRU pod teardown + easy restart is the
answer to standing cost. Every env runs its **own** throwaway sidecar; the
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

## Lifecycle — two tiers

Pod lifecycle and storage lifecycle are deliberately separate; the
controller owns the loop.

- **Pod (short-lived)**: idle is inferred from the `claude-code`
  capability's signal — the mtime of the session jsonl under
  `claude/projects/` — falling back to env-creation time before the first
  connect, so a never-used env still ages out, against a TTL of **at
  least an hour**. On reaching it the controller fires a callback and the
  bot renders the **15-minute grace warning** (Cancel extends by a TTL).
  If not cancelled: `preStop` hooks run (the `claude-code` `claude/` →
  CephFS sync), the pod is torn down, and the controller fires the
  shutdown callback (bot edits the message, adds Delete). Restart =
  recreate the pod against the existing env folder (capabilities re-apply;
  `claude-code` runs `--resume`). Controller-managed loop for the MVP; a
  k8s-native scale-to-zero (e.g. KEDA) is a later option.
- **Storage (long-lived)**: the env folder persists across pod teardowns;
  removed on the Delete button / `/delete` (optionally a long TTL
  backstop).

## MVP cut

- **Two services**: controller API (HTTP — lifecycle, k8s orchestration,
  callbacks) + Telegram bot (commands + callback sink); namespaced RBAC.
- Controller config: profiles (incl. a "Claude dev" profile enabling
  `claude-code` + `code-tunnel`), the **Postgres** service preset, a
  secret catalog, project whitelist (the GitHub namespace).
- Reads the known-location repo config; **one** real project (this IaC
  repo) wired end to end with one Postgres sidecar.
- hostPath-subdir workspaces; capability/service-contributed subfolders;
  `claude/` synced to CephFS on shutdown.
- Capabilities: `claude-code`, `code-tunnel`, `github` (`none/ro/rw`),
  named secrets (e.g. `openai-api-key`) — all bao-backed.
- **Port exposure**: LoadBalancer Service + webathome `.home` DNS + chat
  links, with `http`/`https`/`other` port types.
- Idle reaper with the 15-minute grace + Cancel (via callback/API).

**Descoped**: the MCP adapter (the API/bot split keeps it cheap to add
later). **Deferred**: dynamic per-env ZFS datasets via the iac-provisioner
API (isolation/quotas/snapshots); k8s-native idle (KEDA); additional
service presets (OpenSearch/MinIO) beyond the MVP proof; multi-node spread.

## Open questions

- Known-location config filename + schema; profile/preset schema; the
  controller API surface + callback contract.
- Telegram `/command` set specifics.
- Storage teardown: Delete-button/command only, or also a long TTL
  backstop.

## Repos touched

- **Ansible**: provision the dedicated node + its dev ZFS pool (disk in
  `vms.tf` + `zfs_pools` host_var) — the established pattern.
- **HelmCharts**: controller chart — **two Deployments** (controller API
  + Telegram bot) + RBAC + the ZFS share that drives affinity + the CephFS
  history sink + profiles / service presets / secret catalog / whitelist
  config.
- **DockerImages**: the worker image (extends `modern-app-dev`) **+ the
  thin in-pod worker agent** (entrypoint + `preStop` + listener;
  capabilities supply the logic).
- **Each managed project repo**: a small known-location dev-env config
  file.

The per-env LoadBalancer Service + `.home` DNS annotations are emitted by
the controller and reuse existing cluster infra (MetalLB +
dnsmasq/DNS-reservation). Telegram bot infrastructure already exists in
the homelab; the bot token is an OpenBao leaf.
