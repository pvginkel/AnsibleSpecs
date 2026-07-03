# Findings — IaC estate review, July 2026

Severity scale: **Critical** (unattended path to losing something irreplaceable),
**High** (real operational/security risk, act soon), **Medium** (process gap or
latent risk), **Low** (polish). Evidence cited as `file:line` at review time.

Findings that were already known and tracked (a slice, a decisions.md TODO, a
Triage card) are marked *(known)* — for those, the review's contribution is
severity calibration, not discovery.

---

## 1. System-level findings

### C1 — Unguarded unattended destroy of the secrets root × no backup artifact — **Critical**

Four facts compose into the estate's one genuinely dangerous window:

- `IaC/Deploy` runs `terraform apply -auto-approve` on every push to main
  (`Jenkinsfile.iac-on-push`), by design — no human gate.
- The destroy guard protects **only srviac** (`Jenkinsfile.iac-on-push:44`,
  `Jenkinsfile.iac-scheduled-drift:38` — the latter with `|| true`, which also
  swallows the script's own usage errors). `decisions.md:512-513` claims
  `prevent_destroy` on the agent VM *and* each srvvaultN plus a plan-stage
  check for both; **zero `prevent_destroy` blocks exist in
  `Ansible/terraform/`** (verified). Doctrine and implementation diverged on
  the single most dangerous unattended action — the worst kind of gap, because
  the operator believes the rail exists.
- The guard's jq match — `.change.actions == ["delete"] or
  .change.actions == ["create","delete"]`
  (`IaCAgent/bin/check-protected-vms.sh:32`) — misses Terraform's **default**
  replace ordering `["delete","create"]` (delete-before-create; the
  `managed-vm` module sets no `create_before_destroy`). An implicit replace of
  srviac itself (vm_id change, node move) sails through the one guard that
  exists.
- Stage 1 plans to `/tmp/plan.tfplan` and checks it; stage 2 runs a **fresh
  plan+apply in a separate `iac` container** — the checked plan is not the
  applied plan, so the guard is advisory even where it matches. And per slice
  005: the OpenBao backup pipeline is fully built but **nothing has ever
  landed in cloud storage** *(known)* — the May restore drill proved the
  procedure; the artifact it needs doesn't exist.

Worst case today: a bad `vms.tf` refactor destroys srvvault1-3 and their disks
in one unattended run; Shamir keys in Roboform unlock nothing without Raft
data; every runtime secret is gone, recoverable only by re-minting everything.

**Fix (all small):** `contains(["delete"])` in the jq; extend the protected
list (srvvault1-3 minimum; consider any data-bearing VM — or invert to an
allowlist of disposable VMs); add the `prevent_destroy` blocks doctrine claims;
merge plan+check+apply into one `iac -c` invocation applying the saved
`plan.tfplan`; run slice 005.

### C2 — Root-of-trust material committed to HelmCharts git — **High** *(partially known)*

`configs/prd/step-ca/prd/manifests.yaml` commits `step-ca-secrets` (encrypted
intermediate CA + SSH host CA private keys) **and** `step-ca-ca-password` +
`step-ca-ssh-host-ca-password` — the passwords that decrypt them — as k8s
Secrets in the same file. The encryption is thereby moot: the homelab's
signing root sits recoverable in every clone, in CI, and on the
unauthenticated LAN git mirror. `decisions.md:143` already specifies the fix
(ansible-vault-sourced materialisation at bring-up) as a runtime-secrets-sweep
loose end — but that slice closed as complete and the loose end didn't land.
Re-rate it: this is not cleanup, it's the estate's highest-value secret
exposure. Also in the same class:

- `configs/prd/newsfilter/prd/manifests.yaml:9-12` — two user passwords in
  `stringData` (verified).
- `configs/prd/elasticsearch/prd/values.yaml:8` — plaintext password (also
  mirrored in a dev values file).
- `configs/dev/git-sync/prd/values.yaml:11` — a live GitHub PAT (verified:
  `gitSync.gitHubToken`); `configs/dev/homeassistant-mcp/prd/values.yaml:10`
  — a Home Assistant JWT.

**Fix:** rotate everything above, then relocate — step-ca per decisions.md's
own design; app passwords behind the existing `shared.externalsecrets`
pattern; dev tokens into OpenBao. Rotation makes history-scrubbing optional.

### C3 — The unauthenticated HTTP registry is the code-delivery channel into the secret boundary — **High**

`registry:5000` has no TLS and no auth. `iac` pulls `registry:5000/iac:latest`
with `--pull=always` and runs it **with every secret the estate has**
(`IaCAgent/bin/iac:15,40`); kaniko pushes over the same channel; the Jenkins
agent floats `jenkins/inbound-agent:latest` from Docker Hub. Anything with LAN
position that can spoof or push to the registry owns the estate. The secrets
architecture itself reviewed well — this is the weak link that bypasses it.
step-ca makes TLS feasible now; push-auth is the larger lift (kaniko creds,
containerd/docker trust). Also couples availability: a wedged k8s/Ceph blocks
the containerized IaC path entirely (no cached-image fallback in the shim) —
the recovery tool's runtime is hosted on the system it recovers.

### S1 — Alerting lives inside its own blast radius — **High**

Both notification paths depend on the platform they report on: `send_message.py`
fires from Jenkins post-stages (Jenkins runs on k8s prd) via Home Assistant;
the Telegram bot is a sidecar *inside the Jenkins chart*. k8s prd dying looks
identical to "nothing happened." Aggravators: cron schedules were removed from
the Jenkinsfiles (commit `0b4f835a`) and now exist **only in controller job
config on the Jenkins PVC** — unversioned, and a job that stops being
scheduled is invisible; `Jenkinsfile.iac-image` and the architecture pipelines
have no failure notification at all; **`IaC/Scheduled Update` failed 3 of its
last 4 runs** (#7, #8, #10) — an unaddressed reliability signal and an
alert-fatigue seed. **Fix:** external dead-man's switch (healthchecks.io-style
ping on *success*; absence alerts via a channel that doesn't transit k8s);
restore cron specs to the Jenkinsfiles; JCasC/job-dsl for job topology
(see S4); triage the update-job failures.

### S2 — Total-loss recovery bottoms out on three undocumented manual layers — **Medium-High** *(partially known)*

Above the waterline the recovery story is excellent (drilled OpenBao restore,
per-consumer cold-boot docs, iac-cold-boot runbook with Roboform checklist).
Below it: bare-metal PVE install/cluster-join/bridge config documented nowhere;
the physical network fabric (UDM Pro MTU/PPPoE hacks, FRR/BGP, GPON SFP) has
no IaC and no config export; prd MicroCeph was bootstrapped from a 31-line
legacy note (see A1). The master site-DR runbook is a self-admitted TODO
(`decisions.md:110`), and the forced bring-up order is load-bearing rather
than self-correcting (`internal_tls` hard-fails when step-ca is unreachable —
no retry/backoff). The referenced "wife runbook" (`decisions.md:68`) **does
not exist** in `docs/runbooks/`. For an estate that is real prod for the home,
the bus-factor artifact is cited but unwritten.

### S3 — Cross-repo literal mirrors with no reconciliation — **Medium**

Hand-copied facts that drift silently: `homelab-root.crt` in three places
(only the Ansible copy is drift-checked); `HelmCharts/_providers/clusters.yaml`
hard-codes Ceph mon IPs / S3 endpoint / zfs pool→node maps that Ansible+TF
own; Prometheus `extraScrapeConfigs` hand-lists managed hosts; the
`kubernetes` Python client pin spans ≥3 repos per cluster upgrade
(`decisions.md:275`); the iac image bakes `known_hosts`. Doc drift from the
same force is visible now: all three `Jenkinsfile.iac-*` headers point at
IaCAgent paths that no longer exist; IaCAgent's README describes the
superseded `modern-app-dev` container; TerraformState's and the provider's
READMEs describe superseded mechanisms. **Fix:** extend the daily drift job
with cheap assertions (CA copies, clusters.yaml vs inventory) — a generator
would be over-engineering at this scale; plus a docs pass.

### S4 — Jenkins job wiring is not code — **Medium**

Pipelines are in git; the *jobs* — SCM bindings, crons, credential wiring —
live only on the Jenkins PVC in the cluster the pipelines rebuild. Last
significant piece of the delivery system not reproducible from git.
JCasC + job-dsl for the `IaC/` and `DockerImages` folders closes it and is
genuinely instructive Jenkins. (`decisions.md:76` rejected JCasC for one
credential; job topology is a different, stronger case.)

### S5 — Repo boundaries: one merge, keep the rest — **Low**

IaCAgent no longer pulls its weight as a boundary: its pipelines already moved
to Ansible, the iac image already lives there (`support/iac-image/`), and the
`iac_agent` role rsyncs the operator's *local sibling checkout* — a build-time
coupling with visible doc-drift on both sides. Fold it into
`Ansible/support/iac-agent/`. The other splits earn their keep: HelmCharts
(cadence/tier), DockerImages (build model), TerraformState (sensitivity),
HomelabTerraformProvider (toolchain), AnsibleSpecs (harmless).

### S6 — Slice/AIWorkflow process: proportionate, with a decay debt — **Low**

The ceremony is right-sized for the dual-role model (quick fixes stay
frictionless; managed changes get slices) and the docs do triple duty (design
record, runsheet, AI context). The visible cost is documentation decay:
`decisions.md` at 545 lines despite its own "this document expires" banner,
three drifted READMEs, stale Jenkinsfile headers, the unwritten wife runbook.
The existing "explanatory notes decay" / end-of-push absorption rules are the
answer — they need enforcing, not replacing.

---

## 2. Ansible repo

**Overall: top-decile.** Check-mode correctness as a designed-in property (88
`check_mode: false` read probes; the daily `--check` drift job genuinely works
— most estates cannot claim this); an SSH trust model better than most
enterprises (committed `@cert-authority` anchor, ed25519-cert-only
`HostKeyAlgorithms`, TOFU-free bootstrap via TF-generated host keys);
`update-k8s.yml` is a hardened artifact with a real failure-mode ladder
(preflight → leaked-cordon detection → version-skip guard → cold-cycle
handling → rescue-uncordon); runtime primary *election* instead of pinned
primaries (`elect-primary.yml`, `elect-bootstrap.yml`); zero plaintext secrets
found; exceptional documentation density. ~32% of role tasks are
`command`/`shell` (snap/microk8s/bao/pveum have no modules) but with real
discipline: 152 `changed_when`, output-parsed change detection, probe-then-gate
over `creates:`.

| # | Sev | Finding |
|---|---|---|
| A1 | **High** *(known)* | **prd Ceph fleet managed in name only.** `srvceph1/2/3` are in `managed` (`inventories/prd/hosts.yml:95-103`) but excluded from every convergence path (`site.yml:13` excludes `ceph_prd`; `site-ceph.yml:18-19` targets only `ceph_dev`); no `update-ceph.yml`. No baseline, no drift detection, no orchestrated patching on the three storage nodes under everything — and hand-applied state accumulating (prd PG tuning uncodified). Phase-5/microceph-prod is the plan; the longer it stands, the more reverse-engineering adoption inherits. |
| A2 | Medium | **No CI lint gate; lint not clean.** Push goes straight to live apply with no `ansible-lint`/`yamllint`/`--syntax-check` stage. 6 substantive `production`-profile findings live today (e.g. `no-changed-when` at `roles/microk8s/tasks/users.yml:23`, `name[template]` at `roles/microk8s/tasks/install.yml:43,52`); `.ansible-lint` still `strict: false` ("fail hard once roles stabilize" — they have). |
| A3 | Medium | **Collections unpinned and doubly-sourced.** `collections/requirements.yml` is all `>=`; installed tree gitignored — same commit can resolve differently by install day. `pyproject.toml` also pins `ansible ^13` (the bundle, vendoring the same collections at poetry-locked versions), which the galaxy tree silently shadows. Pick one source of truth. |
| A4 | Medium | **OpenBao integration is one-way.** Ansible provisions OpenBao superbly but never reads from it: `community.hashi_vault` + `hvac` declared, referenced nowhere — violating the repo's own no-unexercised-config rule and leaving the highest-learning integration unbuilt. (Stated plainly, as risk-acceptance: repo + vault passphrase = unseal capability; passphrase custody is the crown jewel.) |
| A5 | Medium | **"Which playbook converges this host?" enforced nowhere.** Coverage spread over four site playbooks + a growing exclusion list (`site.yml:13`); A1 is the live demonstration. A small CI assertion (every `managed` host matched by exactly one site playbook) kills the failure class. |
| A6 | Low | `Restart microk8s` handler is an undrained full-node bounce reachable from a git push (`roles/microk8s/handlers/main.yml:20-28`); tolerable under prd `serial: 1`, a full outage on single-node dev. |
| A7 | Low | Composition doctrine contradicts itself: microk8s meta says "compose via play ordering, not meta deps"; `baseline/meta` declares `dependencies: [bootstrap]`. |
| A8 | Low | Doc drift: `k8s-upgrade.md` (snap module + cordon behavior stale), `README.md` (pre-commit), `roles/README.md` (promises SSH-hardening/UFW/keycloak that don't exist). |
| A9 | Low | Operator username `pvginkel` hardcoded across 4 roles; fact cache in world-readable `/tmp/ansible-facts` (`ansible.cfg:21`). |

Stats: 13 roles (all hand-rolled, all with READMEs), ~6,000 lines role YAML,
11 playbooks, 347 commits since May 1. No molecule; scratch fleet + daily
drift job are the de-facto test tiers (defensible — see tech-radar on
right-sized testing).

---

## 3. Terraform (Ansible/terraform/) + HomelabTerraformProvider

**Overall: strong.** Data-driven prd root (one `local.vms` map → `managed-vm`
module, typed `optional()` objects, plan-time VMID/MAC validation); surgical
`ignore_changes` (the hardest part of bpg/proxmox, done right); single-source
NIC/MAC data shared with Ansible host_vars; `moved` blocks used correctly. The
custom provider is genuinely good Go: plugin-framework (not legacy SDK), clean
per-resource packages, correct CRUD semantics (404→RemoveResource,
RequiresReplace, key-rotation ModifyPlan), token redaction, ~38 unit tests +
7 acceptance tests. Every provider resource is justified (bespoke homelab APIs
or lifecycle semantics `null_resource` can't express). Git-backed sops/age
state via `terraform-backend-git` is well-reasoned — it correctly avoids the
in-cluster circular dependency an S3/minio backend would create, and lock
branches are a true remote mutex across the two real writers.

| # | Sev | Finding |
|---|---|---|
| T1 | **High** | Destroy guard gaps + plan/apply divergence — see **C1**. |
| T2 | **High** | **Provider CI publishes untested binaries.** `HomelabTerraformProvider/Jenkinsfile` = clone → `go build` → publish to `tfmirror.home`. No `go test`/`vet`/lint despite the test suite existing; consumers have **no version constraint** on `pvginkel/homelab`, so any `init -upgrade` picks up whatever was pushed last. |
| T3 | Medium | **Loose pinning where it matters.** `bpg/proxmox` at `~> 0.66` (= anything <1.0; lock has 0.106.0; bpg breaks across 0.x minors). Pin `~> 0.106.0` per root, bump deliberately. |
| T4 | Medium | **Proxmox creds: root@pam password + `proxmox_insecure=true` default** (`prd/variables.tf:22-27`); workstation credential in plaintext `terraform.tfvars` (srviac does it right via `!bao`). step-ca can issue PVE API certs; drop `insecure`. ⚠️ Note: the review itself read `terraform.tfvars` (Proxmox root password + two bearer tokens); gitignored, values not reproduced — but rotate on principle. |
| T5 | Medium | **Data-destroying provider resources lack an interlock.** `homelab_s3_storage` bucket removal deletes the bucket *and objects* (`internal/s3storage/resource.go:70-75,226`); `zfs_dataset` destroy relies on call-site lifecycle blocks. Add `force_destroy`-style opt-in attributes (the AWS-provider convention — and a good schema-design lesson). |
| T6 | Medium | Hygiene absent + docs drifted: `terraform fmt -check` fails today (`prd/vms.tf`); no fmt/validate stage in CI; `prd/README.md` references a nonexistent `import.sh` and still says state is local-only; provider README describes the retired filesystem-mirror flow. |
| T7 | Low | Nil-client panic path in resources when provider config is unknown (standard `r.client == nil` CRUD check missing). |
| T8 | Low | `managed-vm` reads `../../../ansible/inventories/prd/host_vars/` from *inside the module* — hidden input, breaks portability (scratch root would silently resolve prd). Pass it in from the root. |
| T9 | Low | Scratch root hand-rolls its own VM resource/cloud-init (already diverged from prd's template); slice 002 covers half of this. Spent `moved` blocks still in `prd/main.tf:61-72` (repo's own decay rule). |
| T10 | Low | `terraform-backend-git` is a niche third-party daemon on every apply's critical path; no runbook for clearing a stale `locks/<path>` branch; scratch state outside the daily drift job. |

Stats: 2 roots + 1 module; 12 prd VMs (9 from-scratch, 3 adopted Ceph);
provider: 6 resources, ~5,000 LOC, framework v1.13, Go 1.25 (cgo → librados
dep); **0 tests executed in CI**; 4 HelmCharts terraform-modules + ~55
per-release states consume it.

---

## 4. HelmCharts

**Overall: the harness is better than its reputation with its own author.**
Correction to the estate's shorthand: Terraform does *not* wrap Helm — the
deploy CLI (859 lines) orchestrates *TF infra → `helm upgrade --install` → TF
config* per release, with TF owning the durable substrate (namespaces, PVs,
RBD images, S3 users, Postgres DBs, Keycloak config). Data-loss safety is the
best reviewed here: hardcoded `prevent_destroy` on every data-bearing module,
Retain + claimRef pre-binding, uninstall ≠ destroy, and Released-PV reattach
logic closing the real k8s footgun. The pipeline is **target-state including
image digests** (live-vs-resolved digest diffing — ~80% of a GitOps
reconciler's semantics, push-triggered, hand-built). Secrets mainline is right
(ESO + OpenBao AppRole, TF-minted per-release S3/Postgres creds).
Prometheus-driven resource recommendations. Docs match reality.

| # | Sev | Finding |
|---|---|---|
| H1 | **High** | Committed plaintext secrets — see **C2**. |
| H2 | **High** | **One failing release aborts the run and silently consumes changes.** Sequential per-release stages, no try/catch — first failure kills the build; `changed()` is edge-triggered off `currentBuild.changeSets`, so a change whose deploy failed is **never retried** unless re-touched (only digest/version drift self-heals). A release whose image tag can't resolve is dropped with a stderr note (`resolve_helm_args.py:218-220`). |
| H3 | **High** | **Nothing on the deploy path is version-pinned; upgrades land unattended.** Upstream charts always float to latest non-prerelease (`resolve_helm_args.py:148-158`) — a breaking cloudnative-pg/ESO/ceph-csi major deploys to prd the moment version-poller notices. TF providers float via `init -upgrade` per deploy. `helm upgrade` doesn't touch `crds/`-dir CRDs → silent CRD skew accumulates across auto-upgrades. |
| H4 | Medium | **No health gating, no rollback.** No `--wait`/`--atomic`; `deploy wait` swallows failures by design (`helmops.py:156-170`) — a crashlooping deploy is a green build. Nothing calls `helm rollback`; recovery is manual-forward. |
| H5 | Medium | **No preview/diff in CI; no chart validation.** TF phases are `apply -auto-approve`, no plan gate; no `helm lint`, no `values.schema.json`, no kubeconform, no unittests — a values typo renders empty and ships to prd. (Sibling repo's doctrine is check-mode-first; the k8s estate is fire-and-observe.) |
| H6 | Medium | **Workload security posture thin.** 17/38 in-house charts mention `securityContext`; no runAsNonRoot/readOnlyRootFilesystem baseline; **zero NetworkPolicies**; one PDB. Consistent with the tracked prd-RBAC gap. |
| H7 | Medium | Any `terraform-modules/` or `_providers/` touch redeploys **all 49 release-stages** sequentially under H2's abort semantics — full-estate rollout, no canary/batching. |
| H8 | Medium | Digest pinning depends on regex-scraping template source (`image: <prefix>{{ .Values.x }}`, `resolve_helm_args.py:43-60`) — helpers/`tpl`/quoting silently escape pinning and drift detection; Jenkinsfile then `eval`s the `--set` tokens (injection-shaped). |
| H9 | Medium | Bootstrap ordering is alphabetical + two forced tails (`jenkins`, `nginx`) — no dependency graph; ESO sorts *after* some of its consumers. Steady-state fine; from-scratch replay needs multiple passes. |
| H10 | Low | Legacy residue: dead "legacy inline PV" helper branches (migration complete), broken `configs/dev/external-secrets.sh` symlink; `randAlphaNum`-per-render SSE secret in a URL query (`charts/design-assistant/templates/app-deployment.yaml:106`); `sed`-based post-renderers silently no-op if upstream refactors; static `Chart.yaml` versions. |

The decoupling analysis (what binds charts to this repo) and its fix are in
[gitops.md](gitops.md) §"What actually binds charts here".

---

## 5. IaCAgent + DockerImages

**IaCAgent overall: careful work.** `set -euo pipefail` everywhere; secrets
resolve *inside* the container at runtime (never through `docker -e`); the
`!bao` sentinel design is genuinely good (typed refs at YAML-parse time,
irreducible-literal set explicitly modelled and hard-failing); flock held
across the whole `docker run` with the agent container contending on the same
inode; `--init` zombie-reaping with the durable-task double-fork explained;
recovery runbooks with a Roboform coverage checklist. srviac dying is a
nuisance, not a disaster.

| # | Sev | Finding |
|---|---|---|
| I1 | **High** | Guard script jq bug + protected list never grew — see **C1**. |
| I2 | Medium | **PAT leaks into Jenkins logs on clone failure**: token embedded in the clone URL (`bin/iac-impl:383`) + uncaught `CalledProcessError` prints full argv to the build log; token also persists in each clone's `.git/config`. Fix: `GIT_ASKPASS`. |
| I3 | Medium | Jenkins agent secret via argv (`jenkins-agent-launch.sh:76`) — visible in `ps`/`docker inspect` for the container's lifetime; supports `-secret @file`. The format-validation error path also echoes the rejected value to the journal. |
| I4 | Medium | `/etc/docker/daemon.json` has two owners: the `iac_agent` role writes it (with restart handler); `install.sh:53` also installs it (no restart). Identical today; silent divergence when either changes alone. |
| I5 | Medium | `--pull=always` hard-couples every `iac` run to the in-cluster registry (see C3) — no cached-image fallback; the cheap escape (`IAC_IMAGE=` override / pull-with-fallback) isn't built. |
| I6 | Low | Lock-holder diagnostic truncates its own evidence (`exec 9>` — first contender erases the holder's PID before waiting; fix `exec 9>>`); drift-sum greps `changed=` across the whole log, not just the recap; `install.sh`'s yq provenance comment is wrong (apt yq on srviac is the Python one — verified live; happens to tolerate `!bao`). |
| I7 | Low | Doc drift cluster: README/runbook say `modern-app-dev` + `poetry install` (superseded); nonexistent `Jenkinsfile.iac-dqlite-watchdog` listed; on-push header points at an IaCAgent path that doesn't exist; `secrets.yaml` mode enforced by runbook prose, not convergence. |

**DockerImages overall: clean and right-sized** (reviewed lighter, per brief).
Kaniko-in-cluster, no docker socket; the internal dependency graph is *derived*
from `FROM` lines and topo-sorted with transitive descendant rebuilds — better
change detection than many professional monorepos. Base freshness is solved by
deliberate policy (time-driven weekly rebuilds via `rebuild-at` labels; the
version-poller redesign doc correctly rejects dependency-watching as false
coverage) — the pervasive floating tags are a coherent choice, but the trade
should be written down. No build-time secret issues found.

| # | Sev | Finding |
|---|---|---|
| D1 | **High** | Registry unauthenticated HTTP — see **C3**. |
| D2 | Medium | **No vulnerability scanning anywhere** (no trivy/grype). Weekly rebuilds are the de-facto patch mechanism but nothing measures the result; a base that stops receiving fixes ages silently. |
| D3 | Medium | Interim/rolling Ubuntu bases will break on EOL: `modern-app-dev` and the **iac image** build `FROM ubuntu:questing` (~9-month support) — when questing EOLs, apt 404s and the weekly rebuild of the IaC runner itself starts failing. Move to LTS or document the policy. |
| D4 | Low | Stale pins where pins exist (`registry-cleanup` on `alpine/k8s:1.30.3` vs a 1.35 cluster); 44/45 Dockerfiles run as root (cheap to fix in-house; unlocks `runAsNonRoot` in HelmCharts, pairs with H6); `curl \| bash` installs without checksums; `*-tmp/` litter at repo root. |

**Secrets-flow verdict (cross-cutting):** two rest locations by design
(OpenBao; plaintext `/etc/iac/secrets.yaml` 0600 as the conscious bootstrap
anchor — srviac disk compromise transitively yields the iac secret set, an
honest documented trade). In transit, almost everything is right (HTTPS to the
`secrets.home` VIP with the certifi/`REQUESTS_CA_BUNDLE` fix; WSS agent; no
secrets via `docker -e`; agent container pointedly doesn't mount
secrets.yaml). The one unencrypted, unauthenticated leg is the registry pull —
and it carries executable code into the container where all secrets
materialise (C3). Small leak paths: I2, I3.

---

## 6. What was checked and found healthy

Worth recording so future reviews don't re-litigate: bootstrap circularity is
engineered, not accidental (every cycle has an explicit, documented cut);
`reboot_after_update=false` + drain-aware update playbook means TF can never
bounce a cluster member; the flock + lock-branches + `disableConcurrentBuilds`
stack serializes the two delivery loops through one choke point with no
split-brain; all 57 tfstate files verified encrypted; the OpenBao whole-cluster
restore was drilled 2026-05-23 (6m32s converge + ~5min restore); secrets
tiering (Roboform → ansible-vault bootstrap tier → OpenBao → materialised
consumers) is principled with written rationale, including the public-repo
ciphertext posture; apply-on-push *without* PR gating is the right call for a
single operator **once C1 is fixed** — the compensating-control model (daily
drift + guards + no-reboot rule) is sound, and a "destroys > 0" push
notification would complete it.
