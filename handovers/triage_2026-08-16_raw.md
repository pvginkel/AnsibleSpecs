# Triage raw dump — Ansible cards in Triage/Inbox — 2026-08-16

28 cards fetched.

## #427 — k8s rolls leave pod placement badly skewed — no rebalance pass

- URL: https://trello.com/c/zspi6WDQ/427-k8s-rolls-leave-pod-placement-badly-skewed-no-rebalance-pass
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a6f9b34d0bfc4d6410d41a5
- Created/last activity: 2026-08-08T13:34:19.282Z

### Description

`update-k8s.yml` drains one node at a time, and drained pods never come back. The last node in the roll returns nearly empty while the others stay packed.

Observed on the 2026-08-02 memory roll (srvk8s1/2/3): afterwards srvk8s1 12797 Mi, srvk8s2 13599 Mi, srvk8s3 1208 Mi — an 11.3x spread against the <=1.5x criterion in AnsibleSpecs/handovers/memory-issues/07-capacity.md. Two of three nodes sat at 81% / 86% of allocatable requests, which defeats the headroom the resize was for.

Corrected by hand with `rollout restart` on five deployments (gitblit, registry, trello-mcp, jenkins, media), moving ~8.9 GiB and landing at 57/53/64% — a 1.21x spread.

The concern is that this recurs on every roll, and `IaC/Scheduled Update` runs unattended at `H 4 * * 0` with nothing to correct it. So the cluster spends most of each week skewed, and an N-1 drain check computed on a skewed cluster is measuring an artifact.

Options worth weighing:
- a descheduler (RemoveDuplicates / LowNodeUtilization strategies)
- a rebalance pass at the end of `update-k8s.yml` (restart the heaviest movable deployments once the last node rejoins)
- pod topology spread constraints on the heavier workloads
- accept it, and only rebalance before a measurement

Caveat for whichever wins: a `RollingUpdate` deployment on an RWO volume deadlocks on restart, and `Recreate` singletons cost real downtime — so a blind "restart everything" pass is not safe. Strategy and PVC access mode have to be checked per workload.

Context: AnsibleSpecs/handovers/memory-issues/HANDOVER.md

### Comments

(none)

## #49 — srvvaultN: systemd-networkd-wait-online hangs ~120s on boot

- URL: https://trello.com/c/AaazOKxa/49-srvvaultn-systemd-networkd-wait-online-hangs-120s-on-boot
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a0ecad0759c740f8e99f5f1
- Created/last activity: 2026-06-26T19:08:58.270Z

### Description

Observed during card #8 reboot-test on srvvault1: `systemd-networkd-wait-online.service` blocks for ~120s before timing out non-fatally, delaying SSH availability post-boot. Boot completes after the unit's TimeoutStartSec fires, so it's a delay-bug not a fail-stop, but adds 2 minutes to every reboot of every srvvaultN.

Likely cause: the static netplan has an IPv6 global address (`2a10:3781:16a9:1::40/64` on srvvault1) configured with `accept_ra: false` and no static IPv6 default route, so networkd's "online" check waits for v6 routability that never materialises until timeout.

Three candidate fixes (operator pick):
- Add an explicit IPv6 default route per host (`routes:` entry in `network_devices`), matching the v4 gateway pattern. Most "correct" — gives the host a real v6 default.
- Configure `RequiredForOnline=routable:ipv4` on the networkd unit for hosts that don't need v6 routability. Downgrades the online check, keeps v6 link-local-only.
- Set `optional: true` on the v6 portion of the netplan (per-address). Skips wait-online's check for that address.

Affects every static-netplan host with v6 addresses + accept_ra: false (today: srvvault1/2/3, k8s_prd nodes too). Fix likely lives in the baseline role or in the cloud-init/netplan template Terraform writes. Not blocking card #9.

### Comments

(none)

## #51 — ES logstash-http: find the writer, stop the shard sprawl at source

- URL: https://trello.com/c/EcEpYXPm/51-es-logstash-http-find-the-writer-stop-the-shard-sprawl-at-source
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a3065eeb48e96f69318ac6e
- Created/last activity: 2026-06-26T19:09:00.540Z

### Description

Live-fixed 2026-06-15: `logstash-http-*` was 269 daily indices / 538 shards (replica-on-single-node + 365d retention) — the bulk of the cluster's shards and a major ES slow-start cause. Applied `replicas:0` + 14d ILM retention live, and committed the policy/template bootstrap to `elasticsearch-setup` (DockerImages 2ec5c59).

Remaining:
1. Find what writes `logstash-http-*` — there's no Logstash; an iotsupport app HTTP-appends directly to ES with a date-based daily index name. Not in HelmCharts/iot chart (baked into an app image). Locate it.
2. Confirm it doesn't recreate a competing index template that would override `logstash-http-retention` (reverting `replicas:0`).
3. Migrate daily indices -> ILM rollover alias / data stream (roll at ~1 GB or 7d) to collapse ~14 tiny daily indices into one or two.
4. While there: ES pod `cpu` request is `20m` (starves recovery) and `bootstrap.memory_lock` is failing — both worth a HelmCharts pass.

Context: ES on single-node elasticsearch-prd, 1 GB heap. Guideline is <=20 shards/GB heap; logstash-http alone was ~530 over.

### Comments

(none)

## #327 — iac shim: --pull=always turns a registry blip into a failed build

- URL: https://trello.com/c/kXcGQrOS/327-iac-shim-pullalways-turns-a-registry-blip-into-a-failed-build
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a663e54d39e7002781f8684
- Created/last activity: 2026-07-26T17:05:25.042Z

### Description

`/usr/local/bin/iac` (IaCAgent repo) runs `docker run --pull=always registry:5000/iac:latest` on *every* invocation, so any transient registry/DNS failure fails whatever pipeline stage it lands in.

IaC/Scheduled Update #10 (2026-06-28) is the evidence: the prd roll succeeded in full, then `lookup registry on 127.0.0.53:53: server misbehaving` broke the dev stage *and* the `post { failure }` notification step. Exit 125, build reported FAILURE. A green roll read as a red build.

Options: retry the pull a couple of times, or fall back to the cached image when the registry is unreachable (`--pull=missing`) — the current comment argues never to run a stale image, so a bounded retry is probably the better fit.

Cheap tell when triaging a red IaC build: exit code 125 means the shim, not the roll.

### Comments

(none)

## #457 — Project the Terraform provider credentials into KubeCoder envs so plan/apply work there

- URL: https://trello.com/c/tZXLaa6o/457-project-the-terraform-provider-credentials-into-kubecoder-envs-so-plan-apply-work-there
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a74d99e0ee6a296753d4096
- Created/last activity: 2026-08-06T18:59:42.289Z

### Description

Follow-on from #446 (slice 135, `terraform-backend-git`), which is now fully discharged.

## Where things stand

The state backend is reachable from a KubeCoder env. `pvginkel/Ansible`'s `.kubecoder/config.yaml` runs the `terraform-backend-git` sidecar (commit `f13ca0e`), and from the `iac` sidecar `terraform init` and state reads succeed against both `terraform/prd` and `terraform/scratch` — verified live: 38 real prd resources, 8 scratch. The backend URL names the git store (`pvginkel/TerraformState`, ref `main`), so this daemon and the one `iac-impl` runs on **srviac** resolve to the same state. Reads here are the real thing.

## The gap

Anything that contacts Proxmox still fails, and not because of the backend — the **provider credentials are not present in the environment**.

`terraform/prd` takes them as variables (`terraform/prd/variables.tf`):

- `proxmox_endpoint`
- `proxmox_username`
- `proxmox_password`
- `dns_reservation_token`
- `backup_server_token`

(plus `proxmox_insecure`, `dns_reservation_url`, `backup_server_url` — non-secret.)

Only `terraform.tfvars.example` is checked in. Verified absent in the pod: no `TF_VAR_*` or `PROXMOX_*` env vars in the `iac` sidecar, and `kc catalog` carries none of these secret names on **either** the dev or prd KubeCoder instance. So `plan`/`apply` fail on missing variables.

## What the work is

Cross-repo, Ansible-led:

1. Seed the credential values into the OpenBao catalog leaves (`eso/prd/kubecoder/{dev,prd}/catalog`) so they appear in `kc catalog`.
2. Project them in `.kubecoder/config.yaml` under `secrets:` as `TF_VAR_*` names, so the `iac` sidecar picks them up. Note the secret-mapping change is restart-forcing — needs `kc env sync --mode full-sync`.
3. Re-verify with a real `terraform plan` against `terraform/scratch` first (lower stakes than prd), then decide whether prd plan/apply should be permitted from a dev environment at all.

## Worth deciding before starting

**Do we actually want prd apply capability inside a KubeCoder env?** Today the split is deliberate: real terraform runs happen in the `IaC/*` Jenkins pipelines or by hand on srviac, and `CLAUDE.md` codifies "the operator runs all terraform." Putting live Proxmox root credentials into an environment where an agent operates is a meaningful change to that posture. A narrower option is scratch-only credentials, which unlocks iteration on the disposable fleet without handing over prd.

`CLAUDE.md` was updated in `f455a18` to describe the current half-state accurately; it needs revisiting again if this lands.

### Comments

(none)

## #69 — site.yml layout — does it still make sense?

- URL: https://trello.com/c/9xe2i4qB/69-siteyml-layout-does-it-still-make-sense
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a3eceb13961954a211718ca
- Created/last activity: 2026-08-06T19:22:48.736Z

### Description

Open design question parked at AnsibleSpecs/change_requests/site_yml_layout/. Is site.yml still the right organizing artefact for "apply all roles"? Analysis request, no direction proposed yet. Soft-related to the IaCAgent friction.

### Comments

(none)

## #125 — Telegram IaC bot — messaging hub, dead-man's switch, report rendering

- URL: https://trello.com/c/0XOqhECV/125-telegram-iac-bot-messaging-hub-dead-mans-switch-report-rendering
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a480ebdd7bcba1f13fec532
- Created/last activity: 2026-08-07T20:12:35.446Z

### Description

Bundle at AnsibleSpecs/change_requests/telegram_iac_bot/. New container, dedicated namespace: in-cluster message API (TF-minted creds), text/image/render-URL messages, dead-man's switch funneling to healthchecks.io (only external leg), scheduled reports, possible Alertmanager channel. Replaces send_message.py. Consumers queued: trivy reports, update-train reports, rotation instructions, destroys>0 plan alerts. Run /write-slice when ready.

### Comments

- Pieter van Ginkel, 2026-08-07T20:12:35.420Z:
This also needs to be integrated with Prometheus Alertmanager.

## #127 — TF safety rails — destroy guard, prevent_destroy, apply the checked plan

- URL: https://trello.com/c/iiFSFRZ9/127-tf-safety-rails-destroy-guard-preventdestroy-apply-the-checked-plan
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a480ec453c0d9db61d3b045
- Created/last activity: 2026-08-06T19:22:48.163Z

### Description

Bundle at AnsibleSpecs/change_requests/tf_safety_rails/. Review C1: guard jq misses default replace ordering; only srviac protected; zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan. Fix jq (contains(["delete"])), extend protection (srvvault1-3+), add prevent_destroy, single iac invocation applying the saved plan, drop `|| true` in drift job. Slice 005 (backups) is the other half — already authored, run it. Urgent-rated. Run /write-slice when ready.

### Comments

(none)

## #129 — CI quality gates + trivy — lint/validate/test gates on the push-to-prod pipelines

- URL: https://trello.com/c/QaU5mlMx/129-ci-quality-gates-trivy-lint-validate-test-gates-on-the-push-to-prod-pipelines
- Reporter: Pieter van Ginkel
- Labels: Ansible
- Card id: 6a480ecbd1db3e881b3524c3
- Created/last activity: 2026-08-06T19:22:47.941Z

### Description

Bundle at AnsibleSpecs/change_requests/ci_quality_gates/. ansible-lint strict (+fix 6 findings) + yamllint + syntax-check; terraform fmt/validate (fmt fails today); go test/vet before provider publish (currently untested binaries ship); helm lint + kubeconform + values.schema.json reference chart; trivy warn-only in DockerImages. Four repos, each gate independent. Run /write-slice when ready.

### Comments

(none)

## #506 — Remove the /var/lock/iac.lock flock from bin/iac

- URL: https://trello.com/c/yzCrLvTB/506-remove-the-var-lock-iaclock-flock-from-bin-iac
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a777461cd11efd7ea897d37
- Created/last activity: 2026-08-08T18:24:33.349Z

### Description

The flock existed because `iac-impl` cloned TerraformState and did sync_state_in/out with no remote lock (decisions.md:503). That's gone — `terraform-backend-git` takes `locks/<state-path>` branches, wired via lock_address/unlock_address in both backend.tf. As a state guard the flock is also illusory: wrkdev and the KubeCoder pod write the same store and it sees neither.

Cross-job serialisation, its other job, is already covered — the `IaC Agent` node is set to 1 executor, and it queues instead of failing.

Why it actively hurts:
- `flock -w 60` fails rather than queues; a collision becomes a red build.
- Post-block `iac -c 'send_message.py …'` takes the same lock, so a build failing on contention can't page.
- Global: HelmCharts takes it once per release (~55 `iac -c` calls); Argo PreSync hooks would contend dev-vs-prd and fail at 60s, with `-w 60` hardcoded in the shim (argo-cd/qa.md:704, review-fable.md R1). Likely blocker for Argo CD.

Accepted loss: hand-run Ansible on srviac no longer interlocks with a running job (terraform still does, via lock branches).

Scope: `IaCAgent/bin/iac` + README; decisions.md 130/503; docs/runbooks/iac-agent.md 11/41/51/120; Jenkinsfile header comments (on-push, certs, calico) + HelmCharts Jenkinsfile; argo-cd plan.md/qa.md.

### Comments

(none)

## #573 — OpenBao backup: harden the credential handoff and failure visibility

- URL: https://trello.com/c/UjQumz5e/573-openbao-backup-harden-the-credential-handoff-and-failure-visibility
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e03966e1e614ddc21d37f
- Created/last activity: 2026-08-13T19:06:26.530Z

### Description

Fixed 2026-08-13 — backups flow now (bundle 497820 bytes from srvvault2, 20:46). The premise of this card was wrong: the upload leg was never broken.

The 400 came from the AppRole login at `openbao-backup.sh.j2:38`, not the backup-server POST. Nodes held a current role\_id paired to a secret\_id from a retired role generation — the live role's only accessor dates to 2026-05-22, the nodes were written 2026-05-23 from a stale staging file. A rotation run re-minted it. Diagnosis in the comment.

Remaining work:

1. Root cause: `backup.yml` delivers the staged secret_id on `stat.exists` alone, never checking it against the live role. The staging dir is a persistent per-checkout `tmp/`, so one stale file installs a dead credential permanently.
2. Every leg of the wrapper is a bare `curl -fsS`, so a failure never says which call broke. Cost three months of misdiagnosis.
3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere.
4. ~~First run today 504'd at 69s; the retry succeeded at 46s. nginx fronts backup-server with no~~ `proxy_read_timeout` ~~set (default 60s) and~~ `client_max_body_size 500M`~~. Set~~ `proxy_read_timeout 600s` ~~— a deliberately high ceiling, since a slow backup should wait rather than fail. No retry in the wrapper.~~

Orphaned 2026-05-22 accessor still on the role.

### Comments

- Jeeves, 2026-08-13T18:51:58.459Z:
## Investigation, 2026-08-13

**The 400 was never the upload.** Replayed the AppRole login on srvvault2 with the node's own on-disk credentials:

```
login HTTP: 400
login errors: ["invalid role or secret ID"]
```

`openbao-backup.sh.j2:38` is a bare `curl -fsS` against `/v1/auth/approle/login`, so it exits 22 with exactly the message that was read as the upload POST. The script never reached `tar`, let alone the upload.

**Ruled out, with evidence:**

- backup-server reachable from srvvault2 (10.2.1.7, health 200). Auth is checked before anything that can 400 — unauthenticated POST returns 401 "missing bearer token", bogus token 401 "invalid token".
- Only three 400s exist on `/upload`: missing filename, filename outside [A-Za-z0-9._-], and a nil-body branch unreachable in Go. The script sends `filename=openbao-backup.tgz`, which is valid — it could never have produced a 400.
- AppRole mount healthy: ESO logs in continuously via clustersecretstore `openbao-prd`.
- Not decay: `secret_id_ttl` and `secret_id_num_uses` are never set in `approle.yml`, so minted secret_ids never expire and are unlimited-use.

**Failure history follows Raft leadership**, which is why it looked like a single-node problem: srvvault1 Jun 5–Aug 1 (40 failures), srvvault3 Aug 2–Aug 8 (7), srvvault2 Aug 9–Aug 13 (5). Zero successes on any node, ever.

**Root cause.** The live role holds exactly one secret_id accessor: created 2026-05-22 11:24, no TTL, unlimited uses, no CIDR binding. The node credentials were written 2026-05-23 17:06. Since nothing here expires or revokes secret_ids, every mint against the current role generation would still be listed — so no mint happened on May 23. The value `backup.yml` wrote that day came from a leftover controller-side staging file, not from a mint. The role_id delivered alongside it was correct, because role_id is re-read from the API and re-staged every run. Result: valid role_id + dead secret_id = `invalid role or secret ID`, permanently.

**Fix applied.** `site-openbao.yml -e openbao_rotate_secret_ids=true`. No admin token needed — `auth-token.yml` falls back to the ansible-vault'd admin AppRole in `inventories/prd/group_vars/openbao.yml`; `openbao_admin_token` is the bootstrap/rescue override only, and the root token was retired long ago. The run is additive: nothing revokes existing secret_ids, so ESO, Jenkins and iac-agent were unaffected. `/etc/openbao/backup-secret-id` is now dated 2026-08-13 20:38, and a manual run at 20:46 logged `backup uploaded (snapshot 471414 bytes, bundle 497820 bytes)`.

**Follow-up.** Once the new credential has survived a few timer cycles, destroy the orphaned accessor:

```
bao write auth/approle/role/backup/secret-id-accessor/destroy secret_id_accessor=<the 2026-05-22 guid>
```

## #574 — Auto-derive the deterministic MAC instead of writing it out per NIC

- URL: https://trello.com/c/PVz7YZAX/574-auto-derive-the-deterministic-mac-instead-of-writing-it-out-per-nic
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e039d53b8b955413b5792
- Created/last activity: 2026-08-13T17:49:17.847Z

### Description

Every NIC still carries a hand-written `mac_address` that follows a fixed convention (decisions.md "MAC addressing for managed VMs": `02:A7:F3:VV:VV:EE` — prefix, VMID as two big-endian bytes, NIC index). It should be computed, not typed.

Open design question, and it is the whole point of the card: the MACs now live in `ansible/inventories/prd/host_vars/<name>.yml`, which is the single source of truth since the network-devices-host-vars-sot slice, and `terraform/prd/vms.tf` yamldecodes them back out. Ansible also matches netplan interfaces by that MAC. So deriving it inside the `managed-vm` Terraform module — the original plan, written when the MACs lived in vms.tf — would put the derivation on the wrong side of the SoT. Decide where it belongs before designing.

Legacy adoption MACs (`BC:24:11:...` on srvceph1/2/3) must stay explicit until the Ceph rebuilds rotate them.

`terraform/scratch/main.tf` already derives inline for its single-NIC VMs; folding scratch in is opportunistic, not required.

Supersedes slice 002 (retired). Prior material, incl. the module sketch and the bpg case-normalisation caveat: AnsibleSpecs/change_requests/managed_vm_mac_derivation/

### Comments

(none)

## #575 — Keycloak OIDC login for Grafana and pgAdmin

- URL: https://trello.com/c/LzTmUT83/575-keycloak-oidc-login-for-grafana-and-pgadmin
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e03a780375af56bd59c3f
- Created/last activity: 2026-08-13T17:49:27.498Z

### Description

Put Grafana and pgAdmin behind the homelab Keycloak (`homelab` realm at https://auth.ginbov.nl/realms/homelab) instead of their app-local logins, same shape as dnsmasq / electronics-inventory / iot / guacamole / open-webui / zigbee2mqtt already use: per-app confidential client, secret in OpenBao at `eso/<cluster>/<app>/<stage>/oidc`, materialised by ESO, OIDC config in the chart/release values.

These two are the clean chart-side wins. Grafana has native `auth.generic_oauth` (upstream chart, so the ExternalSecret goes through the release's manifests.yaml); pgAdmin needs a `config_local.py` in `charts/pgadmin/files/` with the client secret injected as an env var.

Clients are hand-created in the realm until keycloak-tf lands — that slice should then import these, never recreate. Redirect URIs are the internal `.home` hostnames even though the IdP is public.

Open question for refinement: per app, map a Keycloak group to an elevated role (Grafana Admin, pgAdmin admin) or keep everyone at base and manage in-app? And do we keep each app's local admin as fallback once OIDC is verified?

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

### Comments

(none)

## #576 — Decide: OIDC on the microk8s apiserver (gates Headlamp SSO)

- URL: https://trello.com/c/P7y8oouI/576-decide-oidc-on-the-microk8s-apiserver-gates-headlamp-sso
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e03adaae6f3bbb89fd017
- Created/last activity: 2026-08-13T17:49:33.168Z

### Description

A doctrine call before any Headlamp work, not a chart change.

Headlamp can be pointed at Keycloak through its chart values, but it forwards the id_token straight to the kube-apiserver — so it only actually authorises if microk8s' apiserver trusts the issuer (`--oidc-issuer-url=https://auth.ginbov.nl/realms/homelab`, `--oidc-client-id=headlamp`, a username/groups claim) and RBAC binds the mapped Keycloak group. Setting the chart flags alone does nothing useful.

So the question is whether we want OIDC on the prd apiserver at all. If yes: it is an Ansible/microk8s change plus RBAC, and Headlamp SSO follows from it. If no: Headlamp stays on its current static admin-user ServiceAccount token pasted into the login form, and we close the idea out.

Either way the answer belongs in decisions.md — it affects more than Headlamp.

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

### Comments

(none)

## #577 — Jenkins OIDC login via oic-auth (in-app, no chart change)

- URL: https://trello.com/c/AEO1suJp/577-jenkins-oidc-login-via-oic-auth-in-app-no-chart-change
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e03b481d58d8fe9be344f
- Created/last activity: 2026-08-13T17:49:40.860Z

### Description

Operator task in the running Jenkins, filed here so it is not forgotten — move it to Operator Actions if you would rather work it there.

The Jenkins chart has no JCasC / security-realm surface (no casc or jenkins.yaml anywhere in it), so there is no comfortable chart-side path and we deliberately do not want a half-JCasC config bolted in for this. The natural route is in-app:

1. Install the `oic-auth` plugin.
2. Configure the OIDC security realm against the `homelab` realm (https://auth.ginbov.nl/realms/homelab), client `jenkins`, via the well-known config endpoint.
3. Keep an in-process emergency admin until the realm is verified.

Needs a `jenkins` confidential client in the realm and its secret, same convention as the other apps.

If we ever add a proper JCasC surface to the chart, fold the realm in then — separate decision.

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

### Comments

(none)

## #581 — iac-image: the poller's weekly rebuild can still be skipped and never retried

- URL: https://trello.com/c/f1ZHXKa0/581-iac-image-the-pollers-weekly-rebuild-can-still-be-skipped-and-never-retried
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e162a46bbc3452585ba8e
- Created/last activity: 2026-08-13T19:08:26.989Z

### Description

From slice 013 (PA reviewer r2 + completion consult) — needs an operator ruling.

Jenkinsfile.iac-image infers "the version poller triggered this" from an empty changeset. A poller-triggered build that happens to absorb commits touching no image input therefore still skips, and per the poller's bookkeeping that weekly rebuild is never retried — rebuild-at does not advance, and after STALE_GRACE the poller reports the image orphaned.

Narrower than the r1 blocker PA fixed, same failure mode. Closing it needs a ruling because the "no escape hatch" ruling weighed manual forcing, not the poller — DockerImages solves this with a params-driven force path that 013 deliberately did not adopt.

Also unverified: verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and the test phase confirmed the pure-skip path is unobservable from inside the slice.

Slice: AnsibleSpecs/slices/completed/013_iac_pipeline_restructure/

### Comments

(none)

## #582 — iac_agent rsync ships gitignored build artifacts to /opt/IaCAgent

- URL: https://trello.com/c/7SGDyHZH/582-iacagent-rsync-ships-gitignored-build-artifacts-to-opt-iacagent
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e162d06b68d0793b55cca
- Created/last activity: 2026-08-13T19:08:29.982Z

### Description

From slice 013 (PC advisory).

ansible/roles/iac_agent/tasks/main.yml:88-95 rsyncs support/iac-agent with delete: true and only --exclude=.git. Any gitignored build artifact present in the operator's workstation checkout (__pycache__/ being the obvious one) ships to /opt/IaCAgent on srviac, and re-ships on every apply.

Suggested fix: --filter=':- .gitignore', or an explicit __pycache__ exclude.

Slice: AnsibleSpecs/slices/completed/013_iac_pipeline_restructure/

### Comments

(none)

## #583 — Slice 013 residuals: managed-vm versions.tf still claims the homelab provider is baked into the image

- URL: https://trello.com/c/epj7i46y/583-slice-013-residuals-managed-vm-versionstf-still-claims-the-homelab-provider-is-baked-into-the-image
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e16366759f1a2b89a6c6b
- Created/last activity: 2026-08-13T19:08:38.264Z

### Description

Doc debt from tf-provider-registry, surfaced three times during slice 013 (PC r1, PC r2, doc phase) — verified false, still open.

terraform/modules/managed-vm/versions.tf:9-11 says the homelab provider binary is "baked into the modern-app-dev image, which is the version source of truth" and cites slices/completed/embed-homelab-provider.md. Neither support/iac-image/Dockerfile nor DockerImages/modern-app-dev/Dockerfile bakes a provider or a filesystem mirror; both resolve registry.terraform.io/pvginkel/* from the tfmirror.home network mirror via /etc/terraform.rc.

One-line fix: correct the comment and point it at slices/completed/tf-provider-registry.md.

The twin claim in docs/runbooks/operator-workstation.md was fixed by 013's doc phase; this one is a code comment in a Terraform module, outside that diff's work list.

### Comments

(none)

## #616 — docs/live-infra-access.md: the mounted kubeconfigs have no cluster-scoped rights at all, not just on nodes

- URL: https://trello.com/c/KgHxsx5S/616-docs-live-infra-accessmd-the-mounted-kubeconfigs-have-no-cluster-scoped-rights-at-all-not-just-on-nodes
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f21dae88245f61376ca
- Created/last activity: 2026-08-14T21:56:49.662Z

### Description

`~/.kube/config-prd-write` is `kubecoder-rw`, a namespaced-edit identity with no cluster-scoped verb whatsoever — it cannot get/list/patch PVs, nor create namespaces, on prd.

The doc states this limit only for the `nodes` resource, which reads as a narrow exception. Slice 007 planned its PV reattach proof around that write path and found it could not do the job; the fixture's cluster-scoped objects ended up created over SSH (`sudo microk8s kubectl` on srvk8s1) instead.

Generalise the sentence so the next slice plans against the real limit.

### Comments

(none)

## #617 — Slice 009: the tf-presync ServiceAccount needs PV get/list/patch cluster-wide

- URL: https://trello.com/c/hARxhMJR/617-slice-009-the-tf-presync-serviceaccount-needs-pv-get-list-patch-cluster-wide
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f222b6ba9f1e22a984b
- Created/last activity: 2026-08-14T21:56:50.129Z

### Description

Verified behaviour from slice 007, not speculation: a reattach run without it gets a 403, and the hook fails the sync on it.

Narrowing the grant with `resourceNames` was considered and rejected — 007's throwaway proof SA could enumerate its two fixture volumes, but the real hook cannot know volume names in advance.

Input for 009's A.4 RBAC.

### Comments

(none)

## #618 — argo-cd/decisions.md D31: the hook image's contents list is stale

- URL: https://trello.com/c/liPx5qs2/618-argo-cd-decisionsmd-d31-the-hook-images-contents-list-is-stale
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f227dd2eb1a64fac397
- Created/last activity: 2026-08-14T21:56:50.611Z

### Description

D31 (:241-243) says the image carries "Terraform, terraform-backend-git, git, and the presync scripts — nothing else". librados2/librbd1, image/terraform.rc and image/homelab-root.crt all ride beyond that, and design.md's image section repeats the same "nothing else (D31)" clause.

Pre-existing; slice 007's P7 reviewer flagged it as outside that phase's mandate.

Second half of the same gap: nothing in the set points at the hook image as a consumer, so a sweep that rotates the step-ca root or readdresses tfmirror.home has nothing telling it this image is affected.

### Comments

(none)

## #619 — The argo-cd set names a credential inventory it gives no way to find

- URL: https://trello.com/c/wTHP8RE6/619-the-argo-cd-set-names-a-credential-inventory-it-gives-no-way-to-find
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f231c1826c47daf8d82
- Created/last activity: 2026-08-14T21:56:51.134Z

### Description

phases.md A.2/A.4 both owe and read "the inventory of a run's whole environment". That inventory exists only at `slices/completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md` and is cited nowhere under `argo-cd/`.

Either cite it from the set or promote it into the set — slice 009 plans from the documents, not from 007's plan.md.

### Comments

(none)

## #620 — presync: an unparseable ServiceAccount ca.crt escapes the named-error handler

- URL: https://trello.com/c/lAShNeBe/620-presync-an-unparseable-serviceaccount-cacrt-escapes-the-named-error-handler
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f23a47d29ab34b146a2
- Created/last activity: 2026-08-14T21:56:51.590Z

### Description

In ArgoCDTools, a present-but-unparseable `ca.crt` raises `ssl.SSLError` out of `Api`'s TLS-context construction, escaping `__main__`'s `PresyncError` handler.

The run still exits non-zero, so the sync stays gated — but the operator gets a traceback instead of a named cause.

Found as slice 007 P3 r1 F3; the completion consult judged it too small to justify a phase.

### Comments

(none)

## #622 — presync exports an empty stage or namespace argument as an empty TF_VAR_*

- URL: https://trello.com/c/lN7XPBXd/622-presync-exports-an-empty-stage-or-namespace-argument-as-an-empty-tfvar
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f24227c354c77d8b315
- Created/last activity: 2026-08-14T21:56:52.525Z

### Description

Slice 007 P9 r1 F1. presync passes an empty `stage` or `namespace` through verbatim, reproducing the silent misnaming that P9 closed.

Unreachable from a rendered Job — the library chart's Helm `required` guard rejects the empty string too — so today the chart's guard is the whole of the protection. Defence in depth would be a check in presync itself.

### Comments

(none)

## #623 — Ruling wanted: does argo-cd/phases.md carry a shipped marker?

- URL: https://trello.com/c/fDkBy887/623-ruling-wanted-does-argo-cd-phasesmd-carry-a-shipped-marker
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f24efe526dec5064bab
- Created/last activity: 2026-08-14T21:56:52.973Z

### Description

Every item in A.1 (shipped as slice 006) and A.2 (shipped as slice 007) still reads `- [ ]`, so the set read on its own presents shipped work as pending.

007's doc phase did not invent a convention: no `[x]` exists anywhere in the file, and status is tracked in slices/README.md and on the board.

If phases.md should carry one, the ruling also needs to say how it handles items like A.2's "CI publishes registry:5000/argocd-hook:<n>" — code-complete but owed to an operator keystroke.

### Comments

(none)

## #624 — Slice 007 residuals

- URL: https://trello.com/c/Utiy8yX7/624-slice-007-residuals
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7f8f2528c9b0b805786677
- Created/last activity: 2026-08-14T21:56:53.463Z

### Description

Two mechanical leftovers from slice 007, neither behavioural:

- Charts' `tests/render-consumer.sh` locates the `args:` block with an awk latch on the render's first `args:`, with nothing tying it to the hook Job (P10 r1 F1). A future fixture manifest that helm sorts ahead of the Job and carries its own `args:` makes the gate fail claiming the hook renders the wrong arguments — a misleading false red, never a false green.
- plan.md's P5 done-record cites `tests/consumer/values.yaml:37-40` and `tests/render-consumer.sh:104-106`; P10's later insertion shifted these to `:39-44` and `:124-128`. Content and semantics are correct — only the stamped pointers are stale, and verification.json cites the current lines.

### Comments

(none)

## #625 — srvk8s3: memory PSI counter wedged at 1.000 s/s — stuck-on alerts nobody receives

- URL: https://trello.com/c/zvUKmXfl/625-srvk8s3-memory-psi-counter-wedged-at-1000-s-s-stuck-on-alerts-nobody-receives
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a806ab0dfcc2cc6d51eeb0e
- Created/last activity: 2026-08-15T13:35:08.040Z

### Description

srvk8s3's memory PSI "some" counter advances at exactly 1.000 s/s — 1800.0s of stall per 1800s bucket — while the node reports 5.3 GiB MemAvailable and 2.2 major faults/s. That is not pressure; the counter is wedged.

NodeMemoryStalled (critical) and NodeMemoryStallElevated (warning) have both been firing on srvk8s3 since ~2026-08-13, across 485 five-minute buckets.

Alertmanager still has no receiver configured, so none of it was sent anywhere. The detection layer added after the 2026-08-02 memory incident is currently stuck-on, and the "nobody hears it" half is what makes that dangerous rather than merely noisy.

Two coupled facets: the alert rules trust a counter that can wedge, and there is no delivery path to notice when they misfire — or when they fire for real.

Split out of #412 (kube-reserved on the microk8s nodes), archived 2026-08-15 — its 08-02 execution shipped these alerts as HelmCharts `97fa810` + `9898d0a`. See that card's closing comment for the reservation-value and liveness-probe threads it left open.

### Comments

(none)

## #635 — Retire the now-unused HA_URL / HA_TOKEN from the IaC agent

- URL: https://trello.com/c/ZpUz4EYx/635-retire-the-now-unused-haurl-hatoken-from-the-iac-agent
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a816fc22699ede094308c6f
- Created/last activity: 2026-08-16T08:07:30.236Z

### Description

send_message.py is gone (Ansible 7cdc788): the IaC pipelines now report through jenkins-telegram-bot and raise the rest via JenkinsPipelineUtils' notify var. It was the only consumer of HA_URL and HA_TOKEN, which are still wired up.

Left out of that commit because retiring them touches four places plus a live host:

- `support/iac-agent/etc/iac/secrets.example.yaml` — the `HA_URL` literal and the `HA_TOKEN` `!bao kv/iac/homeassistant#token` ref
- `ansible/inventories/prd/group_vars/openbao.yml` — the `kv/iac/homeassistant` grant in `openbao_iac_agent_kv_paths`
- `docs/runbooks/iac-cold-boot.md` — its `HA_TOKEN` step
- the OpenBao leaf itself, and srviac's live `/etc/iac/secrets.yaml`

Order matters: dropping the grant while a `!bao` ref survives hard-fails iac-impl at next container start. Remove the refs and converge first, then the grant and the leaf.

The token is minted distinct from the homeassistant-mcp chart's (decisions.md, per-consumer named accounts), so nothing else loses access.

### Comments

(none)
