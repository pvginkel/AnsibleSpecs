# Triage raw dump — 2026-09-14

Source: the Triage board's Inbox — the `Ansible`- and `HelmCharts`-tagged cards that do not carry
`Project-ArgoCD`, plus the open entries of the close-out report that `[016] close-out` card #750
names. Scope, per the operator: "Everything in Inbox that's not dependent on the Argo CD project.
I'm halfway through and I appreciate there are residuals in there that likely make more sense to
bundle with whatever else comes out of the Argo CD project. Do include the HelmCharts cards."
Left out: #844, #976, #977, #980, #990, #991 (`Project-ArgoCD`) and #992 (`[010] close-out`, an
Argo CD slice).

Fetched 2026-09-14, whole and verbatim, by read-only sub-agents. One structural edit: a heading
inside a card description or comment that sat at depth 2 is demoted two levels (depth only) so it
does not collide with this dump's `## #NNN` card sections — #573's comment heading
"Investigation, 2026-08-13".

## #127 — TF safety rails — destroy guard, prevent_destroy, apply the checked plan

- URL: https://trello.com/c/iiFSFRZ9
- List: Inbox
- Labels: Ansible, Major
- Reporter: Pieter van Ginkel (@pietervanginkel1)
- Created/last activity: 8/17/2026, 7:33:53 AM

### Description

Bundle at AnsibleSpecs/change_requests/tf_safety_rails/. Review C1: guard jq misses default replace ordering; only srviac protected; zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan. Fix jq (contains(["delete"])), extend protection (srvvault1-3+), add prevent_destroy, single iac invocation applying the saved plan, drop `|| true` in drift job. Slice 005 (backups) is the other half — already authored, run it. Urgent-rated. Run /write-slice when ready.

### Comments (in the order the tool returned them)

#### Jeeves — 8/17/2026, 7:33:53 AM

Triaged 2026-08-16: Major — "zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan."

Operator ruling: "Agreed."

Raised at triage, worth confirming before this is grouped into a slice: the card names slice 005 (backups) as "the other half — already authored, run it". That slice's current status was not checked.

## #129 — CI quality gates + trivy — lint/validate/test gates on the push-to-prod pipelines

- URL: https://trello.com/c/QaU5mlMx
- List: Inbox
- Labels: Ansible, Test gap
- Reporter: Pieter van Ginkel (@pietervanginkel1)
- Created/last activity: 8/17/2026, 7:34:19 AM

### Description

Bundle at AnsibleSpecs/change_requests/ci_quality_gates/. ansible-lint strict (+fix 6 findings) + yamllint + syntax-check; terraform fmt/validate (fmt fails today); go test/vet before provider publish (currently untested binaries ship); helm lint + kubeconform + values.schema.json reference chart; trivy warn-only in DockerImages. Four repos, each gate independent. Run /write-slice when ready.

### Comments (in the order the tool returned them)

#### Jeeves — 8/17/2026, 7:34:18 AM

Triaged 2026-08-16: Test gap — "go test/vet before provider publish (currently untested binaries ship)."

Operator ruling: "Agreed."

Two things noted at triage: the card records one observed failure inside the gap ("terraform fmt/validate (fmt fails today)"), so adding that gate turns something already red; and it spans four repos with each gate independent, which is the natural split point if the group gets too big for one slice.

## #506 — Remove the /var/lock/iac.lock flock from bin/iac

- URL: https://trello.com/c/yzCrLvTB
- List: Inbox
- Labels: Ansible, Minor
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:32:26 AM

### Description

The flock existed because `iac-impl` cloned TerraformState and did sync_state_in/out with no remote lock (decisions.md:503). That's gone — `terraform-backend-git` takes `locks/<state-path>` branches, wired via lock_address/unlock_address in both backend.tf. As a state guard the flock is also illusory: wrkdev and the KubeCoder pod write the same store and it sees neither.

Cross-job serialisation, its other job, is already covered — the `IaC Agent` node is set to 1 executor, and it queues instead of failing.

Why it actively hurts:
- `flock -w 60` fails rather than queues; a collision becomes a red build.
- Post-block `iac -c 'send_message.py …'` takes the same lock, so a build failing on contention can't page.
- Global: HelmCharts takes it once per release (~55 `iac -c` calls); Argo PreSync hooks would contend dev-vs-prd and fail at 60s, with `-w 60` hardcoded in the shim (argo-cd/qa.md:704, review-fable.md R1). Likely blocker for Argo CD.

Accepted loss: hand-run Ansible on srviac no longer interlocks with a running job (terraform still does, via lock branches).

Scope: `IaCAgent/bin/iac` + README; decisions.md 130/503; docs/runbooks/iac-agent.md 11/41/51/120; Jenkinsfile header comments (on-push, certs, calico) + HelmCharts Jenkinsfile; argo-cd plan.md/qa.md.

### Comments (in the order the tool returned them)

#### Jeeves — 8/17/2026, 7:32:26 AM

Triage research, 2026-08-16 — the flock is still there and unchanged. `support/iac-agent/bin/iac:45-55` takes `/var/lock/iac.lock` on fd 9 with `flock -w 60 -x`, and exits 1 on timeout rather than queueing; the header comment at :10-11 restates the same. Nothing else in `support/iac-agent/` takes it — `bin/jenkins-agent-launch.sh:49,67` only bind-mounts `/var/lock` into the agent container so the host lock is visible across the boundary.

One of the card's three "why it actively hurts" bullets is now moot: `send_message.py` is gone (Ansible 7cdc788 / 123f0f2), so the post-block paging path no longer takes the lock. `install.sh:54-64` sweeps the stale on-host copy.

The card's scope list also predates the fold-in — `IaCAgent/bin/iac` is now `support/iac-agent/bin/iac`.

Triaged 2026-08-16: Minor. Operator ruling: "Agreed."

## #573 — OpenBao backup: harden the credential handoff and failure visibility

- URL: https://trello.com/c/UjQumz5e
- List: Inbox
- Labels: Ansible, Major
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:33:23 AM

### Description

Fixed 2026-08-13: the credential was re-minted and backups flow. The orphaned 2026-05-22 accessor has since been destroyed by the operator. What remains is stopping it recurring undetected.

1. `backup.yml` delivers the staged secret_id on `stat.exists` alone, never checking it against the live role. The staging dir is a persistent per-checkout `tmp/`, so one stale file installs a dead credential permanently.
2. Every leg of the wrapper is a bare `curl -fsS`, so a failure never says which call broke. Cost three months of misdiagnosis.
3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere.

Severity rests on the history, not the current state: zero successful backups on any node from 2026-06-05 to 2026-08-13, silently. The investigation comment below carries the full root-cause analysis and stays as the record.

Trimmed at triage 2026-08-16 to what is still outstanding, per operator ruling. Original description: `AnsibleSpecs/handovers/triage_2026-08-16_raw.md`.

### Comments (in the order the tool returned them)

#### Jeeves — 8/13/2026, 6:51:58 PM

#### Investigation, 2026-08-13

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

## #575 — Keycloak OIDC login for Grafana and pgAdmin

- URL: https://trello.com/c/LzTmUT83
- List: Inbox
- Labels: Ansible, Feature
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:34:16 AM

### Description

Put Grafana and pgAdmin behind the homelab Keycloak (`homelab` realm at https://auth.ginbov.nl/realms/homelab) instead of their app-local logins, same shape as dnsmasq / electronics-inventory / iot / guacamole / open-webui / zigbee2mqtt already use: per-app confidential client, secret in OpenBao at `eso/<cluster>/<app>/<stage>/oidc`, materialised by ESO, OIDC config in the chart/release values.

These two are the clean chart-side wins. Grafana has native `auth.generic_oauth` (upstream chart, so the ExternalSecret goes through the release's manifests.yaml); pgAdmin needs a `config_local.py` in `charts/pgadmin/files/` with the client secret injected as an env var.

Clients are hand-created in the realm until keycloak-tf lands — that slice should then import these, never recreate. Redirect URIs are the internal `.home` hostnames even though the IdP is public.

Open question for refinement: per app, map a Keycloak group to an elevated role (Grafana Admin, pgAdmin admin) or keep everyone at base and manage in-app? And do we keep each app's local admin as fallback once OIDC is verified?

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

### Comments (in the order the tool returned them)

#### Jeeves — 8/17/2026, 7:34:16 AM

Triaged 2026-08-16: Feature — "Put Grafana and pgAdmin behind the homelab Keycloak ... instead of their app-local logins."

Operator ruling: "Agreed."

The card's own open questions — per-app group-to-role mapping, and whether each app keeps a local admin as fallback — were left to refinement rather than settled at triage. Forward constraint carried from the card: a future keycloak-tf slice must import these hand-made clients, never recreate them.

Related and ruled the same day: #576 (OIDC on the microk8s apiserver) was answered yes and is now a Feature, and #577 (Jenkins oic-auth) went to Operator Actions as a chore.

## #581 — iac-image: the poller's weekly rebuild can still be skipped and never retried

- URL: https://trello.com/c/f1ZHXKa0
- List: Inbox
- Labels: Ansible, Minor
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:33:46 AM

### Description

From slice 013 (PA reviewer r2 + completion consult) — needs an operator ruling.

Jenkinsfile.iac-image infers "the version poller triggered this" from an empty changeset. A poller-triggered build that happens to absorb commits touching no image input therefore still skips, and per the poller's bookkeeping that weekly rebuild is never retried — rebuild-at does not advance, and after STALE_GRACE the poller reports the image orphaned.

Narrower than the r1 blocker PA fixed, same failure mode. Closing it needs a ruling because the "no escape hatch" ruling weighed manual forcing, not the poller — DockerImages solves this with a params-driven force path that 013 deliberately did not adopt.

Also unverified: verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and the test phase confirmed the pure-skip path is unobservable from inside the slice.

Slice: AnsibleSpecs/slices/completed/013_iac_pipeline_restructure/

### Comments (in the order the tool returned them)

#### Jeeves — 8/17/2026, 7:33:46 AM

Triaged 2026-08-16: Minor. The card asked for a ruling on adopting a params-driven force path; the operator's answer widens the card well past iac-image.

Operator ruling, verbatim: "The issue more general. All pipelines that conditionally build the image likely won't based on the version poller signal. I see two options. Either this is always two stage: detect whether the image needs to be rebuilt, and then schedule a separate pipeline. That second pipeline is then picked up by version poller. The alternative is that we send a signal to the pipeline it can test for, e.g. the trigger field. The first option is cleaner, but more verbose. All pipelines need to be checked."

So the ask is now: audit every pipeline that conditionally builds an image for the same deafness to the version-poller signal, and pick between the two shapes above. That is its own slice rather than a Jenkinsfile.iac-image fix, and it is worth planning before more pipelines copy the pattern.

Also carried forward from the card: verification.json had no criterion covering Jenkinsfile.iac-image:37-39, and slice 013's test phase confirmed the pure-skip path is unobservable from inside that slice.

## #625 — srvk8s3: memory PSI counter wedged at 1.000 s/s — stuck-on alerts nobody receives

- URL: https://trello.com/c/zvUKmXfl
- List: Inbox
- Labels: Ansible, Major
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:33:51 AM

### Description

srvk8s3's memory PSI "some" counter advances at exactly 1.000 s/s — 1800.0s of stall per 1800s bucket — while the node reports 5.3 GiB MemAvailable and 2.2 major faults/s. That is not pressure; the counter is wedged.

NodeMemoryStalled (critical) and NodeMemoryStallElevated (warning) have both been firing on srvk8s3 since ~2026-08-13, across 485 five-minute buckets.

Alertmanager still has no receiver configured, so none of it was sent anywhere. The detection layer added after the 2026-08-02 memory incident is currently stuck-on, and the "nobody hears it" half is what makes that dangerous rather than merely noisy.

Two coupled facets: the alert rules trust a counter that can wedge, and there is no delivery path to notice when they misfire — or when they fire for real.

Split out of #412 (kube-reserved on the microk8s nodes), archived 2026-08-15 — its 08-02 execution shipped these alerts as HelmCharts `97fa810` + `9898d0a`. See that card's closing comment for the reservation-value and liveness-probe threads it left open.

### Comments (in the order the tool returned them)

#### Jeeves — 8/17/2026, 7:33:51 AM

Triaged 2026-08-16: Major — "the detection layer added after the 2026-08-02 memory incident is currently stuck-on, and the 'nobody hears it' half is what makes that dangerous rather than merely noisy."

Operator ruling: "Agreed."

Cross-item note from triage research on #125, because it bears on how this is grouped: the "no receiver configured" half is neither srvk8s3-specific nor new. `/work/DockerImages/docs/alert-manager/plan.md`, written 2026-08-12 and not implemented, documents the same state — a single default-receiver with no receiver configuration, alerts firing and being silently discarded — and plans the delivery path as a separate Telegram channel via Alertmanager's native telegram_configs plus an SMTP gateway. #125's Alertmanager clause is the same thread. The wedged-counter half is this card's alone.

## #635 — Retire the now-unused HA_URL / HA_TOKEN from the IaC agent

- URL: https://trello.com/c/ZpUz4EYx
- List: Inbox
- Labels: Ansible, Improvement
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:34:22 AM

### Description

send_message.py is gone (Ansible 7cdc788): the IaC pipelines now report through jenkins-telegram-bot and raise the rest via JenkinsPipelineUtils' notify var. It was the only consumer of HA_URL and HA_TOKEN, which are still wired up.

Left out of that commit because retiring them touches four places plus a live host:

- `support/iac-agent/etc/iac/secrets.example.yaml` — the `HA_URL` literal and the `HA_TOKEN` `!bao kv/iac/homeassistant#token` ref
- `ansible/inventories/prd/group_vars/openbao.yml` — the `kv/iac/homeassistant` grant in `openbao_iac_agent_kv_paths`
- `docs/runbooks/iac-cold-boot.md` — its `HA_TOKEN` step
- the OpenBao leaf itself, and srviac's live `/etc/iac/secrets.yaml`

Order matters: dropping the grant while a `!bao` ref survives hard-fails iac-impl at next container start. Remove the refs and converge first, then the grant and the leaf.

The token is minted distinct from the homeassistant-mcp chart's (decisions.md, per-consumer named accounts), so nothing else loses access.

### Comments (in the order the tool returned them)

#### Jeeves — 8/17/2026, 7:34:22 AM

Triaged 2026-08-16: Improvement — "It was the only consumer of HA_URL and HA_TOKEN, which are still wired up."

Operator ruling: "Agreed."

Kept out of the straightforward-changes document deliberately: the card states an ordering constraint with a live consequence — "dropping the grant while a `!bao` ref survives hard-fails iac-impl at next container start" — and the work touches the OpenBao leaf and srviac's live `/etc/iac/secrets.yaml` as well as the repo. The sequencing is part of the ask, so this wants a slice rather than an ad-hoc edit.

## #567 — HelmCharts deploys fail on transient terraform provider checksum fetches

- URL: https://trello.com/c/IaGwCqOa
- List: Inbox
- Labels: HelmCharts
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/16/2026, 5:59:08 PM

### Description

Jenkins IaC/HelmCharts 5752 failed in "Deploying prometheus@prd": terraform init could not install cyrilgdn/postgresql v1.27.0 — "failed to retrieve authentication checksums" fetching SHA256SUMS. 5751 failed the same way on keycloak; 5753 passed on retry. Transient, but it takes a whole deploy down.

Why it recurs: .terraform.lock.hcl is gitignored (.gitignore:11), _providers/providers.tf pins no versions, and _init passes -upgrade (tf.py:129) — so every release and phase re-resolves and re-authenticates every provider. The iac container is `docker run --rm` with no /work mount, so nothing persists between releases.

Measured, not assumed: a plugin cache does not help — warm cache with no lock still fetches checksums. A committed lock does: zero downloads, one registry version-list call. Pinning makes -upgrade a no-op for the public providers while homelab still floats to the newest tfmirror build.

Agreed fix:
- pin kubernetes, keycloak, postgresql, random in _providers/providers.tf
- un-ignore .terraform.lock.hcl, commit per-chart locks
- retry terraform init on transient failure
- verify what a stale committed homelab entry does under -upgrade

Deferred: routing public providers through tfmirror.

https://jenkins.webathome.org/job/IaC/job/HelmCharts/5752/

### Comments (in the order the tool returned them)

_(no comments)_

## #645 — OIDC on the prd microk8s apiserver, and Headlamp SSO on top of it

- URL: https://trello.com/c/x8mduDeq
- List: Inbox
- Labels: Ansible
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:43:51 AM

### Description

The implementation #576's ruling authorised. #576 recorded the doctrine call only and is closed; nothing here has shipped.

Doctrine: AnsibleSpecs/decisions.md, "The prd apiserver trusts Keycloak as an OIDC issuer" (in the k8s group, after "Dashboard tooling"). It names what the trust requires and why chart flags alone do nothing.

The work: on the prd microk8s apiservers, `--oidc-issuer-url=https://auth.ginbov.nl/realms/homelab`, `--oidc-client-id=headlamp`, a username claim and a groups claim; plus RBAC binding the mapped Keycloak group. These are per-node apiserver args, same shape as the `--authorization-mode` flip the microk8s role's tasks/rbac.yml already does — so Ansible plus RBAC, not Helm. Headlamp SSO follows from it.

Presupposes RBAC enforcement on the target cluster: under AlwaysAllow a group-mapped binding is inert. Needs a Keycloak `headlamp` client. Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/.

Untriaged — the ask is the operator's yes at triage on 2026-08-16, not a rubric verdict.

### Comments (in the order the tool returned them)

_(no comments)_

## #667 — ansible-jwk's name allow-list is inert — decisions.md documents it as a control

- URL: https://trello.com/c/WAB6RIwN
- List: Inbox
- Labels: Ansible
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/22/2026, 6:31:42 PM

### Description

Raised separately from KubeCoder card #666 (SSH transport), whose CA research found it. Estate-level, not KubeCoder's.

step-ca 0.30.2's per-provisioner name policy does not work in a file-based ca.json: AllowedNames/DeniedNames/AllowWildcardNames carry `json:"-"` (authority/provisioner/options.go:89-97), filled only via the remote-management API this estate does not use. `step ca policy provisioner --help`: "currently only supported in Certificate Manager". ansible-jwk's committed options.x509.allow.dns list is dead configuration.

Confirmed three ways: OpenBao's listener cert, issued through ansible-jwk, holds DNS:secrets.home and DNS:srvvault1.home, neither on the list; ca.home/provisioners advertises ansible-jwk as options {"x509":{},"ssh":{}}, so only the policy half is dropped — claims survive; and on a throwaway 0.30.2 CA, allow.dns plus deny.dns ["*"] still issued forbidden.example.com.

What does work: per-provisioner options.x509/ssh.template ({{ fail }} refused everything), authority.policy (enforced, but polices every provisioner at once), enableAdmin (migrates provisioners into the CA's badger DB).

KubeCoder slice 165 adds a kubecoder-jwk provisioner configured the same way — its policy block is inert too, by operator ruling.

Why it matters: AnsibleSpecs/decisions.md §Internal TLS presents the allow-list as a control, and it is not one. Fix the mechanism or correct the doctrine.

Full analysis: KubeCoderSpecs/slices/backlog/170_ssh_transport/ssh-host-certs-from-step-ca.md §4.2, §8 item 1; slice 165 close-out B1.

### Comments (in the order the tool returned them)

#### Jeeves — 8/22/2026, 6:31:42 PM

The last loose end from the comment above is closed too — `step-ca-bootstrap.md` commit `fdf4d07`. Nothing in that runbook is left for this card.

It was worse than the one line I flagged. **Five `kubectl` invocations addressed namespace `step-ca`, which does not exist**, and the intermediate-rotation restart addressed `deployment step-ca`, which is a StatefulSet:

- `:249` and `:539` — both `step-ca-intermediate` Secret recipes (bootstrap and rotation).
- `:461` — the `kubectl exec ... cat` fallback in the Windows trust-store import.
- `:545-546` — the intermediate-rotation restart, wrong on both counts.

The Secret recipes fail loudly on a missing namespace, so they cost a minute. The restart is the dangerous one: it would report success against nothing, leaving the operator believing a freshly rotated intermediate is live while the CA keeps serving the old one — the same class of silent no-op as the provisioner-edit paragraph, in the same document.

Verified before writing: only `step-ca-prd` exists (prd cluster; the dev cluster has no step-ca namespace live), it holds `statefulset/step-ca`, and `configs/{dev,prd}/step-ca/prd/manifests.yaml` both declare that same namespace — a single stage, `prd`, on either cluster. Stated once in the runbook so the next `kubectl` added to it inherits the right address. `kc project test` green across all four components.

#### Jeeves — 8/22/2026, 6:24:14 PM

**Follow-up to the comment above: the two riding-along items (3) are now fixed — don't redo them.** They stay documented here for context only.

- **S4** — `Ansible/docs/runbooks/step-ca-bootstrap.md` (commit `ad504d9`). The provisioner-claims procedure now states that the deploy is not what makes the edit live, explains why (upstream chart, no `checksum/config` on the pod template, `ca.json` read at process start only), carries the `rollout restart` / `rollout status` pair, and names the workload the release actually runs — `statefulset/step-ca` in `step-ca-prd`, confirmed against the cluster as the one stage deployed (there is no `step-ca-dev` namespace and no `configs/prd/step-ca/dev/`). Verification line added: `curl -sk https://ca.home/provisioners`.
- **S7** — `AnsibleSpecs/decisions.md` (commit `b1bf0d0`). The leaf is now written `kv/eso/prd/kubecoder/<stage>/step-ca-provisioner-password`.

**One thing left in that area, deliberately not touched:** the same runbook's intermediate-rotation section (`:526-531`) tells you to `kubectl -n step-ca rollout restart deployment step-ca`. By the same evidence that fixed S4, that is wrong for this release on both counts — the workload is a StatefulSet and the namespace is `step-ca-prd`. It was outside what the close-out entry asked for, so it is still there.

**Items 1 and 2 of the previous comment are untouched and are this card's work** — `decisions.md:141`'s mechanism sentence, and `kubecoder-jwk`'s under-declared `options.x509` block.

#### Jeeves — 8/22/2026, 6:07:28 PM

**Slice 165's close-out is closed; everything from it that touches this card lands here.** Source: `KubeCoderSpecs/slices/completed/165_cross_repo_sidecar_and_ssh_prereqs/close-out.md` (B1, S2, S3, S4, S7).

**1. The decisions.md sentence names the wrong mechanism, not just an over-claimed one** (close-out S2). `AnsibleSpecs/decisions.md:141` reads: *"Scoping comes from the provisioner's `allowedSANs` regex (`*.home` plus the kube-apiserver internal names) rather than per-consumer credentials."* Independent of this card's inertness finding, that is not what is deployed. Decoding the `ca.json` in `HelmCharts/configs/prd/step-ca/prd/manifests.yaml:19`, `ansible-jwk` has no `allowedSANs` and no regex at all — it carries `options.x509.allow.dns` with 21 **exact** names (`pve`, `pve.home`, `pve1`, `pve2` and their `.home` forms, `srvceph1..3`, the `kubernetes*` and `kubernetes-api*` names) plus `allow.ip` with three addresses. That is the step-ca policy engine, not a SAN regex, and `*.home` is not among the names — so a `.home` name outside the list would be *refused* if policy worked at all, the opposite of what the decision implies. The sentence needs rewriting whichever way this card lands: correcting the doctrine means describing the policy block that exists, and fixing the mechanism means the regex claim is still wrong.

**2. `kubecoder-jwk`'s block is under-declared as well as inert — do not enable enforcement over it unchanged** (close-out S3). The committed block declares `options.x509.deny.dns: ["*"]` and no `allow` of any kind. The settled intent (slice 165 plan.md:410-412, acceptance criterion V14) was X.509 permitting **no name at all**. DNS is one of the five name types the policy form covers, so the declaration says nothing about IP, email, URI or common-name SANs. Harmless today — the block never loads, and the controller never asks this provisioner for an X.509 leaf. It stops being harmless the moment this card is closed by making per-provisioner policy actually enforce (templates or `enableAdmin`): the block would then be applied as written, which is not what V14 settled. Rewrite it in the same change.

**3. Two small corrections in the same area, riding along because they have no card of their own.** Neither is this card's defect; both are estate step-ca documentation and would otherwise be lost.

- (close-out S4) `Ansible/docs/runbooks/step-ca-bootstrap.md:384-385` closes its "edit the provisioner claims" procedure with *"Validate the JSON (`jq . <file>`), re-encode to base64, redeploy `step-ca`"*. **A redeploy of that release applies the Secret and rolls nothing**, and step-ca 0.30.2 reads `ca.json` only at process start — reproduced during slice 165 on a throwaway 0.30.2 CA, where the provisioner appeared only after `SIGHUP`, a signal a Secret update never sends. Slice 165 walked into exactly this. The same runbook already carries the missing sentence for other Secret-mounted CA material (`:526-531`, `rollout restart` after writing the intermediate). Two corrections belong in that paragraph: the restart, and the workload — prd runs `statefulset/step-ca` in namespace `step-ca-prd`, not the `deployment step-ca` in `step-ca` that `:526-531` names.
- (close-out S7) `AnsibleSpecs/decisions.md:142` writes the new OpenBao leaf as `eso/prd/kubecoder/<stage>/step-ca-provisioner-password`, without the `kv/` mount prefix that `:78` and `:90` both carry. Right for the surface it came from (an ESO `remoteRef` `path:`, where the `openbao-prd` ClusterSecretStore pins the mount), wrong for an operator reading a decision record — `bao kv put eso/prd/…` hits a mount that does not exist. Three characters.

**4. State of `AnsibleSpecs/decisions.md` after 165's close-out** (so a fixer knows what has already moved, commit `7bfd100`): a fifth secret-rotation pattern was added for the `kubecoder-jwk` password — it decrypts the provisioner's `encryptedKey` inside step-ca's own `ca.json`, so a KV-only `bao kv put` desynchronises the two sides, and the KubeCoder controller takes the value as a start-time env var with nothing hashing the Secret into the pod template. The `"sixth out-of-repo copy"` ordinal was dropped from the root-rotation bullet. §Internal TLS `:141` — item 1 above — was **not** touched; it is left for whoever fixes this card.

**5. `kubecoder-jwk` is now live, with the inert block as committed.** Verified 2026-08-22 after the step-ca roll: `https://ca.home/provisioners` lists it alongside `admin`, `acme` and `ansible-jwk`, `kid sihtizNMEttxQBnxP-zj3x5dTaptmdyR8VPmqq_wo80`, `enableSSHCA: true`, `defaultHostSSHCertDuration 168h`, `maxHostSSHCertDuration 336h`. A host certificate was issued through it end to end. So this card's blast radius now covers two provisioners rather than one.

## #978 — HelmCharts generator: resolve a Service's in-house product from its own container, so kube-coder-tunnel-reclaim can be mapped

- URL: https://trello.com/c/EUybfPNG
- List: Inbox
- Labels: HelmCharts
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 9/13/2026, 1:17:31 PM

### Description

Split out of #971.

`charts/kubecoder/architecture.yaml` can't map the controller pod's `kube-coder-tunnel-reclaim` image yet. DockerImages already declares `app:kube-coder-tunnel-reclaim` (`2febafe3-…`), and that product realizes its own service.

Mapping the image would give the `kubecoder-controller` workload two in-house services. `_inhouse_service_for` in `tools/chart_tools/gen_architecture.py` then stops referencing `svc:kubecoder-controller-api` for kubecoder.home and mints a duplicate service. A session confirmed this on 2026-09-13 by running the helper against the live dataset.

Fix: make the generator consider only the container behind the Service when it picks the in-house service, then add `kube-coder-tunnel-reclaim: app:kube-coder-tunnel-reclaim` to the annotation.

Until then the image stays a `gap:` line on every AaC/HelmCharts build. The annotation carries a comment explaining why, so the central architecture update's session leaves it alone.

### Comments (in the order the tool returned them)

_(no comments)_

## #750 — [016] close-out: Scheduled renewal for the internal_tls leaf certificates

- URL: https://trello.com/c/ytgQ38Fl
- List: Inbox
- Labels: Ansible
- Reporter: Jeeves (@jeevesginbov)

### Description

A close-out report is waiting: `slices/completed/016_internal_tls_scheduled_renewal/close-out.md` (AnsibleSpecs).

Entries: **A 1 · N 2 · B 7 · Q 0 · S 5**

**Summary.** The ten `internal_tls` step-ca leaves — pveproxy on pve/pve1/pve2, the kube-apiserver homelab SNI leaf on the k8s control planes, the OpenBao listener leaf on srvvault1/2/3 — got a scheduled renewer. Each leaf is now declared once, in its consumer role's own `tasks/internal_tls.yml` with its eligibility gate alongside it, so a converge and a direct entry cover the same hosts; `playbooks/renew-internal-tls.yml` enters all three roles at that file and renews the fleet in one un-serialised play; and `iac-scheduled-certs` runs it every Friday in two stages of its own, beside the SSH host certs it already renewed.

The one-node-at-a-time property the reloads need moved onto the reloads themselves: `throttle: 1` on `Restart microk8s kubelite` — now a restart plus an in-task readiness poll bounded by the new `microk8s_kubelite_ready_timeout` — and on `Reload openbao`, so no caller has to arrange `serial:` for them. `decisions.md` states the serialization invariant in those terms: what is serialized is the step that takes a node out of service, and `serial: 1` is one way to hold that line rather than the line itself.

Nothing has been signed yet. The code is on `main` (b7de205), but a real apply against prd is the operator's keystroke, so the six leaves already inside their window — pve/pve1/pve2 and srvk8s1/2/3, expiring Sep 10-12 2026 — wait on either the Friday 2026-09-04 cron or a hand run (V01, N1, A1).

**Focus lines.**

- *Outstanding actions:* A1 is a deadline, and N1 has already overtaken its remedy — the shipped path exists, so what is owed is the leaves being signed before Sep 10, by Friday's cron or by hand, not an out-of-band PVE-only rotation.
- *Notes:* N1 first — the fleet's live state, six of ten leaves already inside their window, is what puts a date on this slice. N2 is one missing CI signal, not a failure.
- *Bugs / gaps:* B1 first — it is the one that misleads about coverage an operator would rely on: four of the ten leaves have no expiry gauge and no leaf has an alert. B2 and B4 were fixed in the doc phase (see their notes); B10 is the runbook that phase could not write. B3, B6 and B7 are visibility gaps — what a dry run shows, and what a red build tells the operator.
- *Questions:* None — nothing in this run was left for the operator to rule on.
- *Suggestions:* S4 is the one that can cost a whole renewal cycle — a red host-cert stage skips both leaf stages. S1 changes an operational signal the operator reads daily (drift now reds for renewals the certs job will handle by itself). S2, S3 and S5 are precision items with no consequence today.

Subsumes #737. Disposition the entries with `/dev:close-out`.

### Comments (in the order the tool returned them)

#### Jeeves — 2026-08-30T12:36:41.961Z

Live confirmation from the first post-merge runs, 2026-08-30.

**`IaC/Build-Main` #145** built `658a341` (the slice HEAD) — SUCCESS, `terraform plan`: "No changes. Your infrastructure matches the configuration."

**`IaC/Scheduled Drift` #86** (today's 11:24 UTC cron, post-merge) — FAILURE, and correctly so:

```
TASK [internal_tls : Report the pending leaf (re)issue under --check]
changed: [pve]  => "/etc/pve/local/pveproxy-ssl.pem needs (re)issuing —
                    missing=False, within renewal window=True, SAN drift=False"
changed: [pve1] => (same)
changed: [pve2] => (same)
check-ansible-drift.sh: DRIFT — ansible reports 3 pending changes
```

Yesterday's #85 failed with the opaque `ansible-playbook --check failed (rc=2)`. So 2ec9d0f + this slice turned it into an accurate, named report — S1 confirmed working, and N1's live state confirmed on the wire.

**But it extends S4 into something active.** The red lands in the *first* Ansible stage, so #86 skipped the five stages after it: `Ansible drift (k8s prd)`, `(k8s dev)`, `(openbao)`, `(ceph dev)` and `Homelab CA root drift`. Every daily drift run will do the same until the leaves are signed — so the estate is drift-blind past the proxmox group for the next five days, including the srvk8s1/2/3 leaves this slice also covers. S4's warning about the certs job applies to the drift job too, and it is happening now rather than hypothetically.

**Separate, pre-existing, not this slice's doing** (#85 has it too, and neither file was touched by 016): `Jenkinsfile.iac-scheduled-drift:61,63` and `Jenkinsfile.iac-on-push:43` use bash `[[ ]]` inside `iac -c`, which runs under dash — the log shows `sh: 7: [[: not found` / `sh: 9: [[: not found`. In the drift job a real terraform rc=2 falls through both tests to `else exit $rc`, so the build still reds, but the `DRIFT: terraform plan proposes changes against prd` message and the `check-protected-vms.sh` call never run. Worth its own card.

### Report: slices/completed/016_internal_tls_scheduled_renewal/close-out.md — open entries

#### Summary

The ten `internal_tls` step-ca leaves — pveproxy on pve/pve1/pve2, the kube-apiserver homelab
SNI leaf on the k8s control planes, the OpenBao listener leaf on srvvault1/2/3 — got a
scheduled renewer. Each leaf is now declared once, in its consumer role's own
`tasks/internal_tls.yml` with its eligibility gate alongside it, so a converge and a direct
entry cover the same hosts; `playbooks/renew-internal-tls.yml` enters all three roles at that
file and renews the fleet in one un-serialised play; and `iac-scheduled-certs` runs it every
Friday in two stages of its own, beside the SSH host certs it already renewed.

The one-node-at-a-time property the reloads need moved onto the reloads themselves: `throttle:
1` on `Restart microk8s kubelite` — now a restart plus an in-task readiness poll bounded by the
new `microk8s_kubelite_ready_timeout` — and on `Reload openbao`, so no caller has to arrange
`serial:` for them. `decisions.md` states the serialization invariant in those terms: what is
serialized is the step that takes a node out of service, and `serial: 1` is one way to hold
that line rather than the line itself.

Nothing has been signed yet. The code is on `main` (b7de205), but a real apply against prd is
the operator's keystroke, so the six leaves already inside their window — pve/pve1/pve2 and
srvk8s1/2/3, expiring Sep 10-12 2026 — wait on either the Friday 2026-09-04 cron or a hand run
(V01, N1, A1).

Taken: every LIVE (not struck) entry whose `**Disposition:**` line is blank or says `defer`. Skipped: S1 (disposition: "operator, 2026-09-03 — fix now, the first option: drift tolerates a leaf that is merely inside its window. It happened as predicted (drift #91 red on the three OpenBao leaves, 13 days out, the day before the Friday run). The drift stages now check one certs-job period shorter than the renewer — `internal_tls_renewal_threshold_days=7` against the role's 14 — so drift reds only for a renewal the Friday run already missed, which keeps it as the last warning for a broken certs job without the six-day noise. Ansible 9af8fb9; doctrine in decisions.md \"Internal TLS\"."); struck entries not transcribed.

#### A1 — Rotate the PVE leaves by hand if this slice slips past ~Sep 8 2026 (section: Outstanding actions)

At triage the operator declined a pre-emptive hand-run `iac-apply` on the grounds that the
slice starts today, and at planning chose natural phase ordering over sequencing the
proxmox_host path first — both rulings are recorded in `plan.md`. Neither is revisitable by
the plan: the leaves lapse on wall-clock regardless of the slice's state, so if the run is
still open around ~Sep 8 the operator's own out-of-band rotation is the only thing that
stops the expiry. This entry exists so the deadline is visible on the board rather than only
inside the plan's rulings.

**Consequence:** The pveproxy leaves on pve, pve1 and pve2 expire Sep 10 2026; if the slice has not shipped and applied by then the Proxmox web UI serves an expired certificate on all three nodes, and internal_tls cannot help a leaf that has already lapsed.

**Provenance:** read, plan-writer, plan phase, round 1, plan.md rulings section and slices/backlog/016_internal_tls_scheduled_renewal/slice.md
**Disposition:**

#### N1 — Test phase (r1): six of ten internal_tls leaves are already inside their renewal window in prod, right now · major (section: Notable events)

Live --check --diff against the whole reachable prd fleet (2026-08-30) plus direct openssl reads confirm this is not hypothetical: pve/pve1/pve2 (notAfter Sep 10 20:37:42 2026 GMT), srvk8s1 (Sep 12 08:35:38), srvk8s2 (Sep 12 08:37:26) and srvk8s3 (Sep 10 20:45:27) are all inside the 14-day renewal window today, and playbooks/renew-internal-tls.yml correctly flags all six for reissue under --check. srvvault1/2/3 (Sep 16) are not yet due; srvk8s4 correctly has no leaf. b7de205 is pushed to main. The Friday 2026-09-04 04:00 UTC iac-scheduled-certs cron will pick these six up with six days of margin before the PVE expiry, or the operator can run it now: cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook --diff playbooks/renew-internal-tls.yml --limit '!k8s_dev' --check, then the same command with --check deleted. See verification.json V01 for the full evidence.

**Consequence:** If neither the Friday cron nor a manual run happens before Sep 10, the pveproxy leaves on pve/pve1/pve2 lapse and the Proxmox web UI serves an expired certificate on all three nodes -- the exact outage this slice exists to prevent. This supersedes close-out A1's manual-rotation fallback: the tested, reviewed path now exists and should be used instead of an out-of-band PVE-only rotation.

**Provenance:** witnessed, test-agent r1, live --check --diff + direct SSH cert reads against the prd fleet, 2026-08-30
**Disposition:**

#### N2 — Test phase (r1): iac-on-push's result for b7de205 could not be confirmed -- Jenkins MCP was down · minor (section: Notable events)

Push (d4e5a60..b7de205) completed and is pre-authorized under the devlock hold. Per slice-testing-strategy.md section 4 the pushed commit should be confirmed against iac-on-push (terraform plan + protected-VM destroy check), but the jenkins MCP server returned 502 for the whole test-phase pass and this pod carries no JENKINS_TOKEN for the track_build.py CLI fallback (env checked directly: only GH_TOKEN, KUBECODER_*, TF_VAR_* tokens are projected). This does not block the certs renewal itself -- iac-scheduled-certs is a separate cron-triggered job with no dependency on iac-on-push's result -- but the operator should glance at the iac-on-push build for b7de205 before assuming main is plan-clean.

**Consequence:** Low: iac-on-push only plans and destroy-checks, it converges nothing, so an unnoticed red there costs a delayed signal rather than a live mutation. Worth a look next time Jenkins is reachable.

**Provenance:** witnessed, test-agent r1, jenkins MCP 502 + empty JENKINS_TOKEN env, 2026-08-30
**Disposition:**

#### B1 — AnsibleSpecs — decisions.md overstates internal_tls metric coverage: the four k8s apiserver leaves get no expiry gauge from either path it names · minor (section: Bugs)

`decisions.md:145` says each leaf's absolute expiry "is published as the Prometheus gauge
`internal_tls_cert_not_after_seconds` — written by the `internal_tls` role to a node-exporter
textfile collector for VM consumers, and by an equivalent in-cluster collector for the certbot
path", and separately records that "the alert rule and the in-cluster metric are deferred".

The kube-apiserver homelab SNI leaf is a VM consumer of the `internal_tls` role, but it falls
through both halves of that sentence. `roles/internal_tls/tasks/metric.yml:23-32` skips the
textfile write when the node-exporter textfile directory is absent, and its own comment records
that this is the steady state on k8s nodes — they run node_exporter as an in-cluster DaemonSet
and carry no Debian `prometheus-node-exporter` package. The "other path" that comment points at
is the in-cluster collector the same decisions.md bullet defers.

So the bullet reads as fleet-wide coverage of the VM consumers when it is coverage of the
Proxmox and OpenBao leaves only. Out of scope for slice 016, which adds a renewal path and does
not touch the metric or what alerts on it — but it is a doctrine page stating something broader
than what ships, and the deferred monitoring slice
(`slices/deferred/internal-tls-monitoring.md`) is where the gap is supposed to be tracked.

**Consequence:** Anyone reading decisions.md concludes every internal_tls leaf's expiry is observable in Prometheus. For the kube-apiserver SNI leaves on srvk8s1, srvk8s2, srvk8s3 and srvk8sdev no gauge is written at all, and no alert exists on any leaf — so a stalled renewer on 4 of the 10 leaves is invisible except through the daily drift red.

**Provenance:** read, plan-reviewer, plan phase, round 1, plan_review_r1.md finding F4 (AnsibleSpecs/decisions.md:145, Ansible roles/internal_tls/tasks/metric.yml:23-32)
**Disposition:**

#### B2 — Ansible — roles/proxmox_host/README.md:55 says the pveproxy leaf is renewed on each iac-scheduled-drift cycle, which drift cannot do · minor (section: Bugs)

The line reads: "**Renewal** is threshold-gated by `internal_tls` (re-issue under 14 days left) on each `iac-scheduled-drift` cycle." The drift job runs `ansible-playbook --check` (check-ansible-drift.sh), so it can report a due re-issue and can never sign one — the premise of this whole slice. The line is outside P1's diff (no task file I touched contains it), so the slice's diff-based doc phase can miss it; it should end up naming the weekly certs job P3 adds instead. The equivalent microk8s README lines (:26, :114) are accurate and need nothing.

doc-writer, doc phase, 2026-08-30 — Fixed in the doc phase. roles/proxmox_host/README.md now says the leaf is threshold-gated by internal_tls and driven by the weekly iac-scheduled-certs job running playbooks/renew-internal-tls.yml against every PVE node, and that iac-scheduled-drift is --check-only and never signs. The same false driver claim appeared in three more places and was corrected with it: roles/internal_tls/README.md's cadence section (which still said nothing calls the role on a schedule), AnsibleSpecs decisions.md:140, and two 'run the drift cycle' instructions in docs/runbooks/step-ca-bootstrap.md.

**Consequence:** An operator reading the proxmox_host role README concludes the pveproxy leaves are already renewed daily and stops looking — the exact belief that let the pve/pve1/pve2 leaves run to within 14 days of expiry with nothing signing them.

**Provenance:** read, code-writer, P1, r1, ansible/roles/proxmox_host/README.md:55
**Disposition:**

#### B3 — Ansible — the kubelite restart no longer shows up in a --check --diff run of site-k8s.yml · minor (section: Bugs)

P1 changed 'Restart microk8s kubelite' from ansible.builtin.systemd to ansible.builtin.shell (roles/microk8s/handlers/main.yml:60-71) so the restart-then-wait could be one throttled task. The shell module has no check-mode support, so under --check the handler is skipped rather than reported, and ansible.cfg:12 sets display_skipped_hosts = False, so it vanishes from the output entirely. Reproduced on the pinned ansible-core 2.20.5 with a three-host play: 'RUNNING HANDLER [H] skipping: [h1] [h2] [h3]', recap changed=1 skipped=1 per host. Drift detection is unaffected — check-ansible-drift.sh:39-43 sums recap changed= counts and the notifying lineinfile tasks still report changed in check mode.

**Consequence:** An operator running the docs/design-philosophy.md-mandated --check --diff before an iac-apply of site-k8s.yml sees three changed lineinfile tasks and no mention of the kubelite restart they notify — the most disruptive action in the role, a bounce of each prd control-plane node, is the one thing the dry run does not name.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F1
**Disposition:**

#### B6 — Ansible — a dev-stage failure in iac-scheduled-certs loses its Telegram warning when a later prd stage then reds the build · minor (section: Bugs)

notify.warning only echoes a [raisealert|type=warning] marker into the build log (/work/JenkinsPipelineUtils/vars/notify.groovy:46-48), and the job echoes it solely from post { unstable } (Jenkinsfile.iac-scheduled-certs:205-217), which Jenkins runs only when the final build result is UNSTABLE. Before slice 016 the dev host-cert stage was the last stage in the job, so nothing could downgrade an UNSTABLE build to FAILURE after DEV_STAGE_FAILED was set. P3 puts prd work after a dev stage for the first time: Host certs (k8s dev) at :102-125 sets the flag, and TLS leaves (excl. k8s dev) at :144-161 can red the build afterwards. The same shape already exists in Jenkinsfile.iac-scheduled-drift, whose dev k8s stage at :119-142 precedes prd stages at :144-161 and :195-229, so this is the repo's standing flag idiom rather than something P3 invents.

**Consequence:** srvk8sdev is up, its host-cert renewal fails (build UNSTABLE, flag set), then the prd leaf run fails on an unreachable host (build FAILURE). The unstable handler never runs, so no warning marker reaches the log and the operator's only push is the bot's FAILURE report for the leaf stage — the dev failure, and the genuinely-failed-vs-powered-off distinction, survive only in the build log.

**Provenance:** read, code-reviewer, P3 round 1, phases/P3/code_review_r1.md F1
**Disposition:**

#### B10 — Ansible — docs/runbooks/ has no X.509 counterpart to ssh-host-cert-expiry.md, so a lapsed internal_tls leaf has no documented recovery · minor (section: Bugs)

The SSH side has a full runbook: symptom, the job that should have prevented it, and `reissue-host-cert.yml` as the fix. The X.509 side now has a fix worth documenting for the first time — `playbooks/renew-internal-tls.yml` — but no runbook names it as a recovery path, and an expired leaf has three distinct symptoms nothing points at: a PVE web UI certificate error, SNI validation failing for `kubernetes-api.home`, and the OpenBao listener refusing connections (docs/runbooks/openbao.md:257 already lists 'listener cert expired' as a cold-boot cause and points nowhere). The doc phase did not write that runbook because its central claim could not be grounded from the repo: internal_tls re-issues when the leaf is missing, inside the threshold, or SAN-drifted (roles/internal_tls/tasks/issue.yml), and the threshold check is `step certificate needs-renewal --expires-in`, whose exit code on an *already expired* certificate is not stated anywhere in the repo and cannot be verified without running step against a lapsed leaf. Writing 'run renew-internal-tls.yml and the leaf comes back' would have been an unverified recovery instruction in a runbook read under outage pressure.

**Consequence:** An operator facing an expired homelab leaf — Proxmox UI, kubernetes-api.home or the OpenBao listener — finds no runbook, and has to work out from the role's source whether a plain renewal run recovers a certificate that has already lapsed or whether the leaf must be removed first.

**Provenance:** read, doc-writer, doc phase, docs/runbooks/ inventory and roles/internal_tls/tasks/issue.yml:26-70
**Disposition:**

#### B4 — Ansible — ansible/playbooks/README.md catalogues playbooks but lists none of the certificate ones · nit (section: Bugs)

The README's playbook list stops at `refresh-k8s-addons.yml`, `adopt.yml` and `grow-disks.yml`. It has never listed `renew-host-certs.yml`, `reissue-host-cert.yml`, `site-openbao.yml` or `refresh-calico-token.yml`, and P2's `renew-internal-tls.yml` joins that set. The omission predates this slice, so it sits outside the slice's diff; left alone rather than half-fixed in a code phase.

doc-writer, doc phase, 2026-08-30 — Fixed in the doc phase, for the certificate playbooks only. ansible/playbooks/README.md now lists renew-host-certs.yml and renew-internal-tls.yml as one entry (scheduled renewal, threshold-gated no-ops outside the window, both run weekly by iac-scheduled-certs) and reissue-host-cert.yml as the lapsed-cert recovery. The catalogue's other pre-existing omissions — site-openbao.yml, site-ceph.yml, refresh-calico-token.yml — are untouched: they are outside this slice's behaviour and the doc phase reconciles rather than rewrites.

**Consequence:** An operator scanning ansible/playbooks/README.md for what renews certificates finds nothing and concludes no scheduled renewal playbook exists — the belief this whole slice is closing for the leaves, now reproduced one directory up.

**Provenance:** witnessed | code-writer, P2, r1 — read while placing renew-internal-tls.yml; ansible/playbooks/README.md:15-22
**Disposition:**

#### B7 — Ansible — iac-scheduled-certs no longer sets any build description when the failure is outside its two prd stages · nit (section: Bugs)

P3 removed the job-level post { failure } that unconditionally set currentBuild.description = 'host certs may lapse' (Jenkinsfile.iac-scheduled-certs:196-204; base commit 3b971a5 :113-124) in favour of two stage-scoped handlers at :85-91 and :154-160, so the two certificate classes can each state their own cost. Anything that reds the build outside those two stages — a failing 'library' step at :34, an unallocatable iac-controller agent, a failed SCM checkout — now leaves the description null. Arguably the right trade, since a blanket 'host certs may lapse' on an agent-allocation failure was a claim the job had not earned; recorded so the catch-all's absence is known before the next stage is added.

**Consequence:** A red iac-scheduled-certs whose failure is infrastructural rather than in a renewal stage produces a Telegram FAILURE message with no cost line appended — the job name and build link only, where before it read 'host certs may lapse'.

**Provenance:** read, code-reviewer, P3 round 1, phases/P3/code_review_r1.md F2
**Disposition:**

#### S2 — Ansible — the kubelite wait gates on /livez, which is liveness, not the 'serving again' the handler comment claims · minor (section: Suggestions)

roles/microk8s/handlers/main.yml:65,73-75 releases the throttle slot when https://127.0.0.1:16443/livez answers on an apiserver node, or http://127.0.0.1:10248/healthz on a worker; the comment at :48-51 describes this as the next node going down 'only once this one is serving'. Probed live against the prd apiserver: /readyz?verbose runs etcd-readiness, informer-sync and shutdown, which /livez?verbose does not — exactly the checks separating 'the process answers' from 'this apiserver can serve'. The worker branch is weaker again: kubelet healthz says the health server is up, not that the kubelet has re-registered or its lease resumed, which is the failure mode playbooks/tasks/wait-node-ready.yml:11-28 records from build #15 (a local check on srvk8s4 passing in 0.471s).

**Consequence:** None observed. With three prd control-plane members the VIP still has a healthy peer if one node is live-but-not-ready while the next is restarting, and the plan asked only that the wait last until the apiserver 'answers again', which /livez satisfies. Worth knowing before anyone treats the comment as a guarantee.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F2
**Disposition:**

#### S3 — Ansible — Reload openbao now carries throttle 1 but Restart openbao, in the same role, still does not · nit (section: Suggestions)

roles/openbao/handlers/main.yml:23 puts throttle: 1 on Reload openbao and its comment states the doctrine: the limit belongs with the reload 'rather than restated on each caller'. Restart openbao at :8-11 — a full service restart, strictly more disruptive to the Raft peers than a SIGHUP — is left relying on playbooks/site-openbao.yml:171's serial being arranged by whatever drives it. It is notified from config.yml and hardening.yml.

**Consequence:** Nothing today: the ruling asked only about the reload, and P2's renewal path enters at tasks_from: internal_tls, which notifies Reload openbao and nothing else. It becomes real the first time a driver enters the openbao role at an entry point touching config or the hardening drop-in without arranging serial itself — all three peers would restart at once.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F3
**Disposition:**

#### S4 — Ansible — a failed SSH host-cert stage aborts iac-scheduled-certs before either leaf stage runs · minor (section: Suggestions)

The four stages are plain declarative stages, so the two prd ones fail the pipeline outright: if `Host certs (excl. k8s dev)` reds on one unreachable host, `TLS leaves (excl. k8s dev)` and `TLS leaves (k8s dev)` never execute and the fleet loses that week's leaf renewal. This is the stage ordering P3 was given ("the SSH host-cert stages keep their behaviour and run first") plus the estate-wide convention that a prd stage failure aborts the build — the same coupling the job's own header comment rejects at the job level ("a wedged node blocks certificate renewal fleet-wide"), reproduced one level down between stages. The remedy would be `catchError(buildResult: FAILURE, stageResult: FAILURE)` around the two prd stages so each class runs independently and the build still reds; that changes the SSH stages' behaviour, which P3 was told not to do, and it is a pattern no iac-* Jenkinsfile uses today.

**Consequence:** One unreachable host during the host-cert stage silently costs all ten internal_tls leaves their weekly renewal. The build is red and pages, so it is visible; but two consecutive red Fridays inside a leaf's 14-day window would let that leaf lapse while the operator is still chasing the host-cert failure.

**Provenance:** witnessed | code-writer, P3, r1, Jenkinsfile.iac-scheduled-certs stages block
**Disposition:**

#### S5 — AnsibleSpecs — slices/deferred/internal-tls-monitoring.md still argues its urgency from 'no detector exists', which this slice changed · nit (section: Suggestions)

The deferred monitoring design says that until the expiry gauge and alert land, 'no expiry alert fires — a silent renewer failure would surface only when a leaf actually expires', and that this is acceptable given '47-day leaves, a working renewer, and a small fleet'. Both premises moved: the renewer now has a schedule rather than depending on someone starting an apply, and a red or unstable iac-scheduled-certs is a detector for a renewal that stopped happening — one that reaches the operator by Telegram, ahead of any leaf expiring. The doc phase left the file alone: slice documents are outside its surfaces per docs/slice-doc-plan.md, and this one is a parked design rather than a live claim about the fleet. The gap the file describes is still real and still worth its §J work — the four kube-apiserver leaves emit no gauge at all (close-out B1), and the certs job only detects a renewal that fails loudly, not one that silently stops covering a host.

**Consequence:** Whoever reactivates the deferred monitoring work reads a risk argument written before the renewal had a schedule, and either over-rates the urgency or dismisses the file as stale; the genuine remaining gap — no gauge on the k8s leaves, no alert on any leaf — is in the same file and easy to lose with it.

**Provenance:** read, doc-writer, doc phase, slices/deferred/internal-tls-monitoring.md:10-17 and Jenkinsfile.iac-scheduled-certs:195-217
**Disposition:**
