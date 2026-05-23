# Runtime secrets sweep — consumer migration into OpenBao

## Goal

Move every runtime secret in the homelab from its current home —
`srviac:/etc/iac/secrets.yaml` literals, Jenkins credential store
entries, HelmCharts per-environment values, the few candidates in
ansible-vault — into OpenBao KV. Each consumer reads via its already-
provisioned mechanism: ESO for in-cluster, the HashiCorp Vault plugin
for Jenkins, `iac-impl`'s `!bao` resolver for everything that runs
through the IaC agent (Ansible + Terraform + `send_message`).

After this slice, adding a new homelab secret is a one-path operation:
`bao kv put kv/<consumer>/<name> <key>=<value>` plus a consumer-side
ref (and a policy widening if the path is new). No more vault edits,
no more secret blocks in Helm values, no more Jenkins credential UI
clicks.

This slice supersedes phase 2 card #15 ("first consumer migration +
close the phase"). It depends on phase 2 (cluster + AppRoles + audit
+ backup) being closed; all three consumer AppRoles (`iac-agent`,
`jenkins`, `eso`) were provisioned by phase 2 card #11 with inert
policies waiting for paths.

## Decisions

The per-consumer mechanism is settled in
[`decisions.md`](../decisions.md) §Secrets — OpenBao ("All Vault
integrations work unchanged: `community.hashi_vault` (Ansible),
External Secrets Operator (Helm), HashiCorp Vault Jenkins plugin")
and §Runtime secrets — IaC agent resolver ("Ansible-via-iac-impl
consumes env + files materialised by the resolver before it ever
runs, so it does not need an AppRole of its own"). The decisions
below cover the layout + execution shape this slice enforces on top
of those.

- **KV layout: consumer-rooted.** `kv/iac/<name>#<key>`,
  `kv/jenkins/<name>#<key>`, `kv/eso/<chart>/<name>#<key>`. Cross-
  consumer shared values go under `kv/shared/<area>/<name>` and
  every consumer policy that needs them grants the path. Consumer-
  rooted because policy management is per-consumer; a flat layout
  muddles that. Migration is mechanical: every secret picks a home
  from its *primary* consumer.

- **No new AppRole for Ansible converge.** Per decisions.md §Runtime
  secrets, Ansible reads the env materialised by `iac-impl` —
  `lookup('env', '<NAME>')` in roles, or a role default bound to the
  env. The `community.hashi_vault` collection is *not* installed;
  Ansible never makes its own OpenBao round-trip.

- **The vault is already minimal.** Of the four ansible-vault'd
  entries today, three are bootstrap-tier per existing doctrine:
  - `openbao_admin_role_id` / `_secret_id` — the credential that
    authenticates to OpenBao itself. Circular.
  - `internal_tls_jwk_provisioner_password` — decisions.md
    §Internal TLS is explicit: *"never moves into OpenBao, because
    OpenBao's own listener cert is issued by this same path."*
  - `roles/openbao/files/static.key` — the seal key. Self-explanatory.

  Only `vrrp_auth_password` is even a candidate. **This slice leaves
  it in vault.** The `keepalived` role is invoked by the `openbao`
  role itself on srvvaultN — bringing the VIP up needs the password
  to be in hand before OpenBao is reachable on `secrets.home`.
  Direct-node-IP reads bypass the loop but cost a load-bearing
  exception. Not worth it for one 8-character secret.

  Net: the vault holds the same four things after this slice as
  before. The "as much as possible" answer is "almost nothing" — by
  design, captured in decisions.md.

- **Hard-fail on miss, everywhere.** Each consumer's failure surface
  is loud and immediate: `iac-impl` exits non-zero before any clone;
  `withVault` blocks the pipeline; an `ExternalSecret` stays in
  `SecretSyncError` and pods don't pick up new values. No fallback
  to literal anywhere.

- **Per-consumer cold-boot story.** `iac-cold-boot.md` already covers
  the IaC path. Jenkins, ESO, and (transitively) anything they feed
  each need a paragraph in the openbao runbook describing how they
  degrade and how the operator forces a literal value temporarily.
  Most consumers degrade gracefully because they cache values at the
  moment of last successful resolution (ESO into k8s Secrets,
  Jenkins-Vault into the in-flight pipeline) — new resolutions
  block; live state keeps running.

## Steps

### A. Bring up the consumer-side infrastructure

These prerequisites are not "secret migration" but their absence
blocks the per-secret work.

1. **HelmCharts: deploy External Secrets Operator.** New chart +
   `configs/prd/external-secrets-values.yaml` + `external-secrets.sh`
   wrapper. Then a `ClusterSecretStore` named `openbao-prd` pointing
   at `https://secrets.home` with the `eso` AppRole. The
   `eso` AppRole's `secret_id` reaches ESO via a small hand-created
   k8s Secret (same trick `step-ca` uses for its passphrase per
   decisions.md §Internal TLS — "regular Kubernetes Secret, not
   delivered via ESO from OpenBao"). That Secret + the role_id in the
   ClusterSecretStore spec are the ESO-side bootstrap-tier credential.
2. **Jenkins: install the HashiCorp Vault plugin + configure.** In
   the Jenkins Helm values (HelmCharts), pin the plugin in JCasC,
   add the OpenBao server entry (`https://secrets.home`), and bind
   the `jenkins` AppRole via a Jenkins Credentials entry pointing at
   an ESO-materialised k8s Secret — so the `jenkins` AppRole
   `secret_id` itself isn't typed into the Jenkins UI. This is the
   first ESO consumer; a useful early proof that the ESO path works
   end-to-end.
3. **IaC agent: no work.** `iac-impl` is already in place (phase 2
   card #40 / [`iac-secrets-resolver`](completed/iac-secrets-resolver.md)).

### B. KV layout + initial seed

- `bao secrets list` confirms `kv/` is mounted (phase 2 card #11).
- Establish the top-level prefixes by writing a `_README` placeholder
  in each: `kv/iac/_README`, `kv/jenkins/_README`, `kv/eso/_README`,
  `kv/shared/_README`. Pure convention so `bao kv list kv/` shows
  the prefixes from day one.

### C. Per-consumer migration sweeps

Each sweep follows the same shape; do one consumer at a time so the
operator's attention stays focused.

#### C.1. `iac/secrets.yaml` literals → `kv/iac`

Smallest surface; lights up the AppRole that runs Ansible. First.

1. List the literals in `srviac:/etc/iac/secrets.yaml`, excluding
   the four irreducibles (`OPENBAO_URL`, `OPENBAO_ROLE_ID`,
   `OPENBAO_SECRET_ID`, `GIT_API_TOKEN`).
2. For each: `bao kv put kv/iac/<name> <key>=<value>`. Convention:
   the KV path's last segment matches the env var in lowercase
   kebab (`HA_TOKEN` → `kv/iac/ha-token`); the inner key is the env
   var's natural suffix (`token`).
3. Extend `openbao_iac_agent_kv_paths` in
   `inventories/prd/group_vars/openbao.yml` with the new path; one
   drift converge widens the policy via `approle.yml`.
4. Operator edits `/etc/iac/secrets.yaml` on srviac: literal →
   `!bao kv/iac/<name>#<key>`. An `iac` round-trip proves
   resolution.
5. Update `pvginkel/IaCAgent/etc/iac/secrets.example.yaml` so the
   schema stays self-documenting. (The live `secrets.yaml` is
   operator-curated and never overwritten — phase 2 lesson.)

Repeat until the only literals left are the four irreducibles.

#### C.2. Jenkins credential store → `kv/jenkins`

1. Audit Jenkins credentials in the UI. For each, decide pipeline
   secret (move) vs. infrastructure (leave). API tokens, deploy
   keys, registry creds → move. The Vault plugin's own AppRole, the
   bootstrap admin creds → leave.
2. For each migrated credential: `bao kv put kv/jenkins/<name>
   <key>=<value>`.
3. Extend `openbao_jenkins_kv_paths`; converge.
4. Refactor each pipeline that consumed the credential:
   `withCredentials([...])` → `withVault([configuration: [...],
   vaultSecrets: [[path: 'kv/data/jenkins/<name>', secretValues:
   [[envVar: 'X', vaultKey: '<key>']]]]])`. The closure body reads
   `env.X` exactly as it did before.
5. Once a pipeline runs green against the OpenBao-backed secret,
   delete the Jenkins credential entry. The migrated pipeline is
   now atomic with the OpenBao value.

#### C.3. HelmCharts secrets → `kv/eso` + `ExternalSecret`

The "truckload." Two passes.

**First pass — replace existing `Secret` manifests.** Each chart
that templates a `kind: Secret` today (`dnsmasq`, `filebeat`,
`media` so far, plus whatever lives in `configs/<env>/`):

1. `bao kv put kv/eso/<chart>/<name> <key>=<value>` for each
   secret value currently sourced from the chart's values file.
2. Extend `openbao_eso_kv_paths`; converge OpenBao.
3. In the chart, replace the `kind: Secret` template with an
   `ExternalSecret` whose `target.name` matches the Secret name the
   consumer pods already reference, so the pod spec doesn't change:
   ```yaml
   apiVersion: external-secrets.io/v1
   kind: ExternalSecret
   metadata:
     name: {{ include "<chart>.fullname" . }}-<name>
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: openbao-prd
       kind: ClusterSecretStore
     target:
       name: <existing-Secret-name>
     data:
       - secretKey: <pod-env-var>
         remoteRef:
           key: kv/eso/<chart>/<name>
           property: <kv-key>
   ```
4. Remove the secret values from `configs/<env>/<chart>-values.yaml`.
5. Re-deploy the chart; ESO syncs on the next refresh; consumer
   pods restart via the chart's existing checksum annotation
   (or get a deliberate kick).

**Second pass — secrets lurking inline in values files.** Some
charts embed secrets directly (database URLs with passwords, OAuth
client secrets, registry pull secrets). For each:

1. Promote to its own `ExternalSecret` + Secret (same shape as
   above); reference the Secret from the chart instead of the
   inline value.
2. KV path under `kv/eso/<chart>/<name>`.

Count of charts/secrets to touch is unknown until the audit runs;
expect 1–2 weekends of mechanical work spread across HelmCharts.
**One chart per commit** — these are independent moves.

### D. Cold-boot doc updates

Append per-consumer sections to
[`docs/runbooks/openbao.md`](../../Ansible/docs/runbooks/openbao.md):

- **Jenkins** — in-flight pipelines fail at `withVault`; queued ones
  retry per plugin config. Workaround: re-enable a temporary Jenkins
  credential with the same env var name (the pipeline closure body
  is unchanged); pull the value from Roboform.
- **ESO** — existing k8s Secrets keep working (cached). New
  `ExternalSecret` values stall at `SecretSyncError` until OpenBao
  returns; consumer pods don't see updates but don't crash.
  Workaround: edit the Secret directly with the Roboform value and
  suspend the ExternalSecret with
  `external-secrets.io/suspend: "true"` until OpenBao is back.
- **IaC agent** — cross-link to
  [`docs/runbooks/iac-cold-boot.md`](../../Ansible/docs/runbooks/iac-cold-boot.md).

## Verification

- **iac/secrets.yaml** — literal count in the live file is down to
  the four irreducibles; an `iac` invocation resolves every ref.
  Removing one path from `openbao_iac_agent_kv_paths` and
  re-converging breaks `iac` at startup with a clear policy-denied
  message.
- **Jenkins** — a representative pipeline (one with multiple
  secrets) runs green using `withVault`. Pull the `jenkins`
  AppRole `secret_id` in OpenBao to a fresh value; ESO refresh
  re-materialises the Secret; the next pipeline run picks up the
  new credential. The Jenkins credential UI no longer holds any of
  the migrated entries.
- **ESO** — `kubectl get externalsecret -A` shows every chart's
  sync as `Ready`; `kubectl get secret -A` shows every previously
  Helm-templated Secret. Edit a KV value in OpenBao, force-sync the
  ExternalSecret, verify the k8s Secret updates within seconds; for
  envFrom-style consumers a pod restart picks it up, for
  volume-mounted secrets the file updates in-place.
- **Vault file** — `grep -rl 'ANSIBLE_VAULT\|!vault' ansible/`
  shows the same files as before (no regression in the irreducible
  set, no leftovers from migration drafts).
- **Drift cycle** — a full `iac-scheduled-drift` cycle is green
  end-to-end after the sweep.

## Caveats

- **The vault doesn't shrink.** Future-self read: this slice's
  headline claim is "everything possible into OpenBao," and
  "possible" excludes the bootstrap-tier set already named in
  decisions.md. The win is on the other three surfaces.
- **ESO has its own boot story.** The `eso` AppRole `secret_id`
  reaches ESO via a hand-created k8s Secret on first cluster
  bring-up (same shape as step-ca's passphrase Secret). Document
  this in the openbao runbook and the whole-site DR TODO
  (decisions.md §OpenBao backup / DR notes that master site-DR
  runbook is a TODO; ESO's hand-creation step belongs in it).
- **Jenkins Vault plugin caches tokens for the duration of a
  pipeline run, not across runs.** Token TTL is 1h
  (`openbao_jenkins_token_ttl` default). Pipelines longer than
  the TTL break mid-run; if any exist, lengthen `token_max_ttl`
  for the `jenkins` AppRole.
- **Per-chart Helm audit is the slow part.** Don't batch; one
  chart per commit makes review and rollback tractable. CLAUDE.md
  "commit early and often" applies in HelmCharts.
- **Adding the (N+1)th iac secret is now a four-touch change:**
  KV write + group_vars policy widening + Ansible converge +
  `secrets.yaml` ref. Worth a one-paragraph "adding a new iac
  secret" section in the iac-agent runbook once the dust settles.
  Jenkins and ESO follow the same pattern at their respective
  surfaces.
- **No automated drift between consumer config and KV paths.** A
  pipeline that references a KV path the policy doesn't grant
  fails at runtime, not at config-edit time. A small lint script
  comparing each consumer's referenced paths against
  `openbao_*_kv_paths` would catch divergence pre-merge; not in
  v1 scope.

## Commits

This slice produces commits across three repos. Suggested cadence:

1. **/work/AnsibleSpecs** — this slice doc. Single commit.
2. **/work/HelmCharts** — ESO chart + `ClusterSecretStore`, one
   commit. Then one commit per migrated chart (the "truckload"
   individual moves). Jenkins values changes (plugin pin + server
   config) land alongside the Jenkins prereq work.
3. **/work/Ansible** — `openbao_iac_agent_kv_paths`,
   `openbao_jenkins_kv_paths`, `openbao_eso_kv_paths` grow
   per-consumer in `group_vars/openbao.yml`; one commit per
   migration batch, same drift cycle reconverges the AppRole
   policies. The iac-agent and openbao runbooks gain their
   cold-boot sections — separate commit.
4. **Jenkins pipeline repos** — out of scope for this repo; tracked
   alongside the HelmCharts commits since most pipelines live in
   chart-adjacent CI definitions.
