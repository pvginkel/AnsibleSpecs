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

## Next-session entry point

A fresh Claude picking this up: read this slice top to bottom,
then read `tmp/secret-inventory.md` (§3.d included),
`tmp/helmcharts-new-values.md`, `tmp/jenkins-credentials-dump.txt`,
`tmp/naming-review.md`, and `tmp/further-audit-request.md`. The
status block below names every decision settled in prior sessions
plus the artifacts that hold the working data; no re-litigation
needed unless the operator opens one.

Starting position is **execute C.0** (write `kv/shared/*` paths,
widen consumer policies). Naming-review markup is final per the
status block; KV path grammar is settled. The five Q1–Q5 open
questions and Q6 naming aesthetics are all resolved. After C.0,
sweep C.1 (iac) → C.2 (jenkins + global env vars) → C.3 (eso,
four-pass).

If the operator triggered the secondary audits per
`tmp/further-audit-request.md` between sessions, fold those
findings into the per-chart C.3 sweeps as you touch each chart;
don't re-block the slice on them.

## Status (as of 2026-05-25)

**Stage A — consumer-side infrastructure**: ✓ DONE. End-to-end
smoke test green: `kv/jenkins/smoke` → `withVault` pipeline →
masked value in console output. Operational landmarks shipped:

- **ESO**: chart `external-secrets` (upstream wrapper) in
  HelmCharts. `ClusterSecretStore openbao-prd` Ready=True, auth via
  the `eso` AppRole. The AppRole `secret_id` is hand-staged into
  the `openbao-eso-approle` Secret in the `external-secrets`
  namespace (not in git).
- **TLS trust to `secrets.home` (cluster side)**: the CSS uses
  `caProvider` pointing at the `homelab-root-ca` ConfigMap;
  `charts/external-secrets/post-install.sh` refreshes that
  ConfigMap each deploy from `/work/HelmCharts/homelab-root.crt`
  (canonical in-repo copy of the homelab root).
- **TLS trust to `secrets.home` (Jenkins side)**: init-container
  pattern landed in `charts/jenkins/templates/jenkins-deployment.yaml`
  — copies `$JAVA_HOME/lib/security/cacerts` into an emptyDir,
  `keytool -importcert`s the homelab root, main container sets
  `JAVA_OPTS=-Djavax.net.ssl.trustStore=/cacerts/cacerts`. ConfigMap
  source mirrors the `charts/nginx/files/ca/` shape.
- **Jenkins AppRole credential**: UI-entered (id
  `jenkins-vault-approle`). The HashiCorp Vault plugin doesn't
  register any `SecretToCredentialConverter` extensions, so
  ESO-materialised auto-import isn't possible; JCasC rejected as
  over-machinery for an operator-initiated yearly rotation. Pattern
  captured in decisions.md §Secret rotation as its own category
  (UI-entered, not KV-stored).
- **`kv/jenkins/*` policy scope**: prefix-glob.
  `openbao_jenkins_kv_paths: [jenkins/*]` in
  `inventories/prd/group_vars/openbao.yml`. Single one-time
  widening; subsequent migrations don't touch the policy. Per-
  consumer scoping choice for `iac-agent` and `eso` is deferred to
  each sweep based on whether that consumer has a leaf manifest
  worth mirroring.
- **Token-self capabilities** (`lookup-self`, `renew-self`,
  `capabilities-self`) added to
  `roles/openbao/templates/policy.hcl.j2` — every non-admin AppRole
  gets these so Vault clients can validate their own tokens after
  login. Surfaced by ESO failing validation; same gap would have
  hit the Vault plugin and `iac-impl`.
- **Rotation patterns** captured in decisions.md §Secret rotation
  — TODO codify: KV-stored (`iac-agent`), UI-entered (`jenkins`),
  hand-staged k8s Secret (`eso` bootstrap-tier), and application
  secrets. Codification into `docs/runbooks/openbao.md` is Stage D.
- **Homelab root rotation mechanism** captured in decisions.md
  §Root rotation mechanism (unrelated to this slice but surfaced
  here; runbook + baseline task updates are TODOs there, not here).

**Stage B — KV layout placeholders**: ✗ SKIPPED. The smoke test
already populates `kv/jenkins/`; `_README` placeholders were pure
convention with no consumer.

**Stage C — per-consumer migration sweeps**: ready to execute.
The audit + naming review are complete; per-consumer policy
scoping settled; sweep order locked. Artifacts in `tmp/`:

- `tmp/secret-inventory.md` — every literal across `srviac:/etc/iac/secrets.yaml`,
  the Jenkins credential store, and HelmCharts (`configs/<env>/*.yaml`,
  `charts/<chart>/templates/*`, `charts/<chart>/values.yaml`,
  `charts/<chart>/files/*`). §3.a = configs literals; §3.b = extra-manifest
  Secrets; §3.c = chart-template hard-coded DB passwords (20 lines
  across 13 templates); §3.d = chart `files/` directory leaks (9
  files across 7 charts, all glob-loaded into ConfigMaps); §4 =
  cross-source duplications; §"Methodology gap" = secrets that
  *should* be wired but aren't (guacamole OIDC client_secret is
  the worked example).
- `tmp/helmcharts-new-values.md` — per-chart `externalSecrets:`
  blocks needed in each chart's `values.yaml` to feed ESO, plus
  the `_externalsecret.tpl` helper proposal.
- `tmp/jenkins-credentials-dump.txt` — UI-side credential dump
  (live secrets, captured to disambiguate audit §2.a's "unknown"
  rows). Rotate on close; listed in §Loose ends.
- `tmp/naming-review.md` — every concrete KV leaf+key the audit
  implies. **Operator markup complete** — Q1 (bundle OIDC
  client_id+client_secret) ✓, Q2 (`kv/shared/wifi-iot` flat) ✓,
  Q3 (distinct per stage) ✓, Q4 (S3 keys via shared transitional
  bucket — strategy A) ✓, Q5 (don't migrate gmail/calendar dead
  creds) ✓, Q6 (naming aesthetics — `homeassistant` not
  `home-assistant` since chart name is `homeassistant-mcp`;
  other proposed names accepted as-is) ✓.
- `tmp/further-audit-request.md` — three follow-up audit passes
  (DockerImages, AnsibleSpecs, Ansible-repo-unvaulted) plus §4
  optional repos and §5 "what the audits will NOT catch."
  **Assume operator runs these between sessions; fold findings
  into per-chart C.3 sweeps as you touch each chart, don't
  re-block the slice on them.**

Decisions settled in the latest session (all reflected in §Decisions
below + the relevant §C subsections):

- **KV path grammar.** `kv/iac/<leaf>#<key>`,
  `kv/jenkins/<leaf>#<key>`, `kv/shared/<area>/<leaf>#<key>`,
  `kv/eso/<cluster>/<ns-base>/<stage>/<leaf>#<key>`. Stage always
  present (even single-stage charts); one flat leaf segment;
  consumer-rooted by AppRole name; the originally-proposed
  `kv/eso/k8s/...` collapsed to `kv/eso/<cluster>/...` because
  ESO is k8s-only.
- **URLs never enter Vault.** Endpoint URLs / realm names /
  broker addresses go to Jenkins global env vars or chart
  values, not KV.
- **Per-consumer named accounts** for Elasticsearch, MQTT, Home
  Assistant, OpenAI, GitHub PAT, RGW-S3 (when TF provider
  mint lands). `kv/shared/` shrinks from 11 audit candidates to
  4 survivors: `ceph-rgw/s3` (transitional), `samba/users`,
  `jenkins/admin-password`, `wifi-iot`.
- **OIDC credentials bundle**: `client_id` + `client_secret`
  travel in the same KV leaf.
- **step-ca bootstrap secrets** (the four `step-ca-*` Secrets in
  `configs/prd/step-ca.yaml`) extract from HelmCharts to
  ansible-vault, materialised at cluster bring-up via a small
  Ansible role — same bootstrap-tier as the OpenBao seal key
  and JWK provisioner password (decisions.md
  §Bootstrap-tier ciphertext + §Internal TLS).
- **custom_metadata for documentation**: mechanism known
  (`bao kv metadata put -custom-metadata=…`); decision to adopt
  as convention deferred to first rotation cycle.
- **Guacamole OIDC client_secret**: chart-template gap — chart
  wires only `OPENID_CLIENT_ID` today (implicit flow), needs
  authorization-code flow with both. Fix required before
  guacamole's §C.3 sweep; tracked in §Loose ends.

Sweep order: **C.0 (shared bucket) → C.1 (iac) → C.2 (jenkins +
global env vars) → C.3 (eso, four passes)**. Shared-first avoids
the "write to `kv/iac` then move to `kv/shared` later" churn.

**Stage D — cold-boot doc updates**: pending; can land after any
one of the C.* sweeps.

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

- **KV path grammar: consumer-rooted, stage-explicit, flat leaf.**

  ```
  kv/iac/<leaf>#<key>                                       (iac-agent)
  kv/jenkins/<leaf>#<key>                                   (jenkins)
  kv/eso/<cluster>/<ns-base>/<stage>/<leaf>#<key>           (eso)
  kv/shared/<area>/<leaf>#<key>                             (cross-consumer)
  ```

  Conventions inside the ESO path:
  - `<cluster>` is `prd` (homelab main) or `dev` (the srvk8sdev
    workstation cluster). Always present.
  - `<ns-base>` is the chart name without any stage suffix
    (`design-assistant`, `dnsmasq`). The live k8s namespace
    today may or may not carry a `-<stage>` suffix; the planned
    chart-redeploy normalises that. KV path uses the base
    regardless, so the path doesn't change when the live ns gets
    renamed.
  - `<stage>` is always present, even for charts that have only
    one stage today (`dnsmasq` → `kv/eso/prd/dnsmasq/prd/...`).
    Explicit so adding a future dev/uat stage never requires
    moving the prd keys.
  - `<leaf>` is one segment, hyphen-compound for sub-structure
    (`oidc`, `samba-users`, `mqtt-cronjob`, `sidecar-a-database`).
    No further nesting — releases-pulling-releases is unbounded, so
    don't draw a line that won't be wrong for some chart. A leaf
    groups co-rotated keys (`oidc#client_id` + `oidc#client_secret`;
    `mqtt#username` + `mqtt#password`).

  Consumer-rooted because policy management is per-consumer; a flat
  layout muddles that.

  The granularity rule: glob at the boundary where a *distinct principal*
  reads, enumerate where multiple principals share. `kv/shared` is
  enumerated per consumer because three consumers (iac, jenkins, eso)
  read it and "which leaf each gets" is a real least-privilege line.
  `kv/jenkins/*` and `kv/eso/<cluster>/*` are globbed because each is
  read by a single principal — a per-(chart,stage) eso whitelist grants
  the same working set as `eso/<cluster>/*` while adding a silent-failure
  footgun (forget a group_vars line → the chart's ExternalSecret sits in
  SecretSyncError after deploy). The per-*cluster* eso split is kept
  because the dev workstation cluster is a separate trust domain (its own
  ESO, likely its own AppRole + `eso/dev/*`). Secrets too sensitive for
  ESO to hold are bootstrap-tier and never live under `kv/eso` anyway, so
  the glob doesn't widen real exposure. (Earlier drafts enumerated eso
  per (chart,stage); reverted — the C.3 pass-4 SecretSyncError gap was
  that footgun firing.) `kv/iac` is the one consumer kept enumerated:
  it's a single principal too, but its source is the small hand-curated
  `/etc/iac/secrets.yaml` manifest (6 leaves), so the explicit list
  mirrors the manifest 1:1 and the friction is negligible. The same rule
  would permit `iac/*`; it's enumerated by choice, not necessity.

- **URLs never enter Vault.** Vault holds credentials only. Endpoint
  URLs (S3, Elasticsearch, Keycloak, HA, MQTT broker), realm names,
  service hostnames — all non-secret. ESO consumers keep them in
  chart values; Jenkins pipelines get them from Jenkins **Global
  properties → Environment variables** (set once, referenced as
  `env.X` from any pipeline). Putting URLs in Vault adds policy +
  ESO churn for zero security benefit and was actively painful in
  the current Jenkins credential-store-as-everything pattern.
  The only URL irreducibly in `iac/secrets.yaml` is `OPENBAO_URL`
  itself, because it gates the path that fetches everything else.

- **Per-consumer named accounts over shared accounts of convenience.**
  Where today's pattern is "every consumer reuses the admin
  credential" (Elasticsearch `elastic` user, the single Home
  Assistant long-lived token, the single iotsupport MQTT password,
  one OpenAI key, one GitHub PAT used by iac+jenkins), the
  migration mints a dedicated account per consumer. Each lands in
  the consumer's own KV path; rotation is per-consumer; blast
  radius is bounded. **`kv/shared/` shrinks to the small set of
  values that are genuinely one principal in many places** —
  today: the Ceph RGW S3 user (until per-app minting lands —
  see decisions.md §Ceph RGW credentials), the two samba users,
  the Jenkins admin password, and the Wi-Fi password (genuinely
  one physical credential used by Jenkins firmware-burn pipelines
  and the iot chart's management UI). The audit's §4 listed 11
  shared candidates; only 4 survive this principle. Account-creation is
  a per-consumer migration prerequisite, not part of the KV write
  step. **Rotation stays operator-driven; not automated** — the
  win is the *ability* to rotate per-consumer, not the cadence.

- **Jenkins global env vars are the right home for non-secret
  pipeline test config.** Anything that was hidden in a Jenkins
  "Secret text" credential because pipelines needed an indirection,
  but isn't actually secret — realm names, base URLs, OIDC token
  URLs, Elasticsearch cluster URL — moves to **Manage Jenkins →
  System → Global properties → Environment variables**. Pipelines
  reference `env.X` exactly as they do credentials today. Same
  decoupling, none of the false-secret-in-Vault smell. Documented
  as a sibling pattern to Vault in the openbao runbook.

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

### A. Bring up the consumer-side infrastructure (DONE — see Status above)

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
2. **Jenkins: install the HashiCorp Vault plugin + configure (UI
   only).** This Jenkins chart (`charts/jenkins/`) is a bare wrapper
   around `jenkins:lts-jdk21` — no JCasC, no plugin pinning. Plugins
   are operator-installed via the Jenkins UI and persist on the PVC.
   No HelmCharts changes are needed for this prereq.

   The earlier draft of this step routed the `jenkins` AppRole
   `role_id`/`secret_id` through ESO + a labelled k8s Secret + the
   `kubernetes-credentials-provider` plugin, so the `secret_id`
   would never be typed into Jenkins. That bridge doesn't exist:
   the HashiCorp Vault plugin does not register any
   `SecretToCredentialConverter` extensions
   (`grep -rn SecretToCredentialConverter` against the plugin
   source returns empty). The only ways to populate a Vault
   AppRole credential into Jenkins's credential store are UI
   entry, JCasC, or a startup script. JCasC was rejected as
   over-machinery — the `jenkins` AppRole `secret_id` has no TTL
   set in OpenBao and rotates only when the operator decides to;
   it isn't worth a ConfigMap + envFrom + pod-restart-for-rotation
   chain for a once-a-year UI click.

   Operator steps:
   - Install `hashicorp-vault-plugin` from Manage Plugins.
   - Mint the AppRole creds:
     `bao read -field=role_id auth/approle/role/jenkins/role-id`
     and
     `bao write -force -field=secret_id auth/approle/role/jenkins/secret-id`.
   - Jenkins → Manage Credentials → System → Global: create a
     "Vault App Role Credential" with `id` = `jenkins-vault-approle`,
     role_id + secret_id pasted from above, path `approle`.
   - Manage Jenkins → System → Vault Plugin: Vault URL =
     `https://secrets.home`, paste the contents of
     `/work/Ansible/ansible/roles/baseline/files/homelab-root.crt`
     into "Vault CA Bundle" (the Jenkins container's JVM
     truststore doesn't carry the homelab root), select the
     `jenkins-vault-approle` credential as the default.

   Rotation flow is its own distinct pattern (UI-entered, not
   KV-stored), tracked in
   [`decisions.md`](../decisions.md) §Secret rotation — TODO codify.
3. **IaC agent: no work.** `iac-impl` is already in place (phase 2
   card #40 / [`iac-secrets-resolver`](completed/iac-secrets-resolver.md)).

### B. KV layout + initial seed (SKIPPED — see Status above)

Original intent: write `_README` placeholders under each top-level
prefix so `bao kv list kv/` shows the structure from day one.
Skipped — the smoke test established `kv/jenkins/` already, and the
placeholders were ceremony without a consumer.

### C. Per-consumer migration sweeps

**Prerequisite: secrets inventory audit (DONE).** Three documents
in `tmp/` are the authoritative source for what moves where:

- `tmp/secret-inventory.md` — current-state map across all three
  surfaces, with per-row disposition (`move` / `keep-vault` /
  `bootstrap` / `not-secret`) and the §3.c chart-template DB
  password block.
- `tmp/helmcharts-new-values.md` — per-chart `externalSecrets:`
  block + the unified `_externalsecret.tpl` helper proposal.
- `tmp/jenkins-credentials-dump.txt` — the Jenkins UI credential
  store with verbatim values. Used to disambiguate the audit's
  `unknown` / `move?` rows and resolve same-value-across-credentials
  cases. Wiped at slice close.

**Naming review (DO BEFORE C.0).** Operator passes through
`tmp/naming-review.md` to finalise every leaf-and-key name before
any `bao kv put` runs. The file lists every concrete KV path the
audit + slice imply (one row per leaf, with proposed leaf name and
keys); operator marks up renames inline. Catches the `wifi-iot`
rename, the `oidc-client` vs `oidc` question, and anything else
the operator spots while scanning. Single atomic step rather than
retrofitting names mid-sweep. File generation deferred — slice
ships first so operator sees the strategy whole; naming-review
generation is the immediate next step.

Each sweep below follows the same shape; do one consumer at a time
so the operator's attention stays focused.

#### C.0. Shared bucket → `kv/shared`

First. The remaining `kv/shared/*` set is small (per Decisions —
"Per-consumer named accounts" shrank audit §4 from ~11 candidates
to 4 survivors), but doing it ahead of C.1 avoids the
"write-to-iac-then-move-to-shared" churn for values whose shared
status is already known.

Surviving shared values (from audit §4 cross-checked against the
named-accounts principle):

- `kv/shared/ceph-rgw/s3#access_key_id,secret_access_key` — the
  single Ceph RGW user used by every chart and the Jenkins
  artifact-upload pipelines. **Transitional** — retires when the
  per-app RGW user work lands (see decisions.md §Ceph RGW
  credentials).
- `kv/shared/samba/users#pvginkel,mvdbovenkamp` — same two samba
  accounts referenced from 5 namespaces (storage, media,
  scantopdf, fundachecker, shell) in prd.
- `kv/shared/jenkins/admin-password#password` — same value
  referenced from `infra-statistics` (chart) and the Jenkins admin
  account itself.
- `kv/shared/wifi-iot#password` — single Wi-Fi password baked
  into IoT-device firmware by Jenkins build pipelines and served
  by the `iot` chart's management UI. Physical credential; the
  named-accounts principle doesn't apply (there's one Wi-Fi
  password in the world).

For each:

1. `bao kv put kv/shared/<area>/<leaf> <key>=<value> [<key>=<value>...]`.
2. Extend `openbao_<consumer>_kv_paths` in
   `inventories/prd/group_vars/openbao.yml` for *every* consumer
   that touches the path — `iac-agent`, `eso`, `jenkins` as
   applicable. One drift converge widens all three policies.

No consumer-side ref edits at this stage — those happen in C.1,
C.2, C.3 as each consumer is swept. C.0 is purely "put values +
widen policies" so the later sweeps can reference them.

#### C.1. `iac/secrets.yaml` literals → `kv/iac` (+ refs into `kv/shared`)

Smallest surface. Audit §1 enumerates 6 movable entries (the
other 4 are bootstrap irreducibles).

**Prerequisite — mint per-consumer accounts (operator-side).**
Per the named-accounts principle:

- New Home Assistant long-lived token for iac-agent (don't reuse
  the one homeassistant-mcp will get).
- New GitHub PAT for iac-agent (don't reuse the Jenkins clone PAT;
  retire the Jenkins-shared `GIT_API_TOKEN` after this step).
- The Proxmox / DNS-reservation / Jenkins-agent / SSH-key entries
  are already per-consumer; no minting needed.

**Per-secret sweep.** For each row in audit §1 with disposition
`move`:

1. `bao kv put kv/iac/<leaf> <key>=<value>` — leaf and key names
   from `tmp/naming-review.md`. Most are
   `kv/iac/<thing>#<credential-type>` (`kv/iac/homeassistant#token`,
   `kv/iac/terraform-proxmox#password`).
2. Extend `openbao_iac_agent_kv_paths` in
   `inventories/prd/group_vars/openbao.yml`; one drift converge
   widens the policy via `approle.yml`.
3. Operator edits `/etc/iac/secrets.yaml` on srviac: literal →
   `!bao kv/iac/<leaf>#<key>` (or `!bao kv/shared/<area>/<leaf>#<key>`
   for shared values C.0 already wrote). An `iac` round-trip
   proves resolution.
4. Update `pvginkel/IaCAgent/etc/iac/secrets.example.yaml` so the
   schema stays self-documenting. (The live `secrets.yaml` is
   operator-curated and never overwritten — phase 2 lesson.)

URLs (`HA_URL`, etc.) do not move. They stay as literals in
`secrets.yaml` per the "URLs never enter Vault" decision; the
file becomes "credentials by ref, non-secret config by literal."

Repeat until the only literals left are the four irreducibles
plus the URL set.

#### C.2. Jenkins credential store → `kv/jenkins` (+ global env vars + refs into `kv/shared`)

Policy widening is already landed (commit `97ca66a`:
`openbao_jenkins_kv_paths: [jenkins/*]`). No further policy edits
in this stage.

**Step 1 — Jenkins global env vars (non-secret config out).** Per
the "Global env vars" decision, the audit-tagged `not-secret`
rows + URL credentials migrate to Manage Jenkins → System →
Global properties → Environment variables, not Vault. From audit
§2.a and the credentials dump:

- `KEYCLOAK_TEST_BASE_URL` = `http://keycloak.keycloak-dev:8080/`
- `KEYCLOAK_TEST_REALM` = `homelab-dev`
- `KEYCLOAK_KENSHO_TEST_REALM` = `kensho-dev`
- `KEYCLOAK_TEST_OIDC_TOKEN_URL` = `http://keycloak.keycloak-dev:8080/realms/homelab-dev/protocol/openid-connect/token`
- `ELASTICSEARCH_CLUSTER_URL` = `http://elasticsearch.elasticsearch.svc.cluster.local:9200`
- `S3_ENDPOINT_URL` = `http://srvceph1:7480`

(OIDC `client_id` values bundle with their `client_secret` in
`kv/jenkins/*` rather than being separated here — per "credentials
together" rule; affects `IOTSUPPORT_CLIENT_ID`, `KEYCLOAK_TEST_IOTSUPPORT_ADMIN_CLIENT_ID`,
`KEYCLOAK_TEST_DESIGN_ASSISTANT_ADMIN_CLIENT_ID`.)

Pipelines reference `env.X` exactly as they do today via
`withCredentials`. Delete the corresponding Jenkins credential
entries after the global env var is in place and a representative
pipeline run is green.

**Step 2 — mint per-consumer accounts (operator-side).** Per the
named-accounts principle:

- New Elasticsearch account for the Jenkins-pipelines-test use
  case (don't reuse the `elastic` admin).
- New OpenAI key per logical use (the audit identifies three
  distinct: `OPENAI_API_KEY_DESIGN_ASSISTANT_UAT`,
  `OPENAI_API_KEY_CI_CD`, `OPENAI_API_KEY` for DA validation;
  decide during migration whether the last two collapse).
- (GitHub PAT splits per C.1 above; the Jenkins `5f6fbd66…` stays
  as the *Jenkins controller's* clone PAT for SCM polling and
  webhook receivers — it's bootstrap-tier, like
  `jenkins-vault-approle`. The `withCredentials` references to it
  in individual pipelines collapse via the `checkout scm` refactor
  pass — see §Loose ends.)

**Step 3 — per-credential sweep.** For each audit §2.a row with
disposition `move`:

1. `bao kv put kv/jenkins/<leaf> <key>=<value>` — leaf names per
   `tmp/naming-review.md`. Credential pairs (id+secret,
   username+password) land as multi-key leaves
   (`kv/jenkins/iotsupport-pipeline-oidc#client_id,client_secret`).
2. Refactor each consuming pipeline:
   `withCredentials([...])` →
   `withVault([vaultSecrets: [[path: 'kv/jenkins/<leaf>',
   secretValues: [[envVar: 'X', vaultKey: '<key>']]]]])`. Closure
   body reads `env.X` unchanged. Some pipelines refactor into
   `withVault` + `env.X` from global env vars (Step 1) at the
   same time.
3. Once the pipeline runs green against the OpenBao-backed
   secret, delete the Jenkins credential entry. The migrated
   pipeline is now atomic with the OpenBao value.

**Audit gaps to triage during the sweep** (audit §2.a unknowns,
resolved against the credentials dump):

- `724520d1-…` = the `jenkins-vault-approle` itself. Bootstrap-
  tier; leave.
- `a3bfc14e-…` / `6ee0e2cf-…` / `82b1648c-…` = k8s ServiceAccount
  tokens and the GitHub plugin's auto-generated entry. System-
  managed; leave.
- `gmail-credentials`, `CALENDAR_BEARER_TOKEN`: no
  `withCredentials` references found in the survey. **Not
  migrated** — operator's Jenkins-credential backup covers
  restoration if alive; first pipeline failure surfaces the
  consumer. Not pre-deleted from Jenkins UI.

#### C.3. HelmCharts secrets → `kv/eso` + `ExternalSecret`

The "truckload." **Three passes**, in order. Audit §3.a is "secrets
in values files," §3.b is "extra-manifest Secrets applied via .sh,"
and §3.c is "hard-coded literals inside chart templates" — the
largest single block at 20 lines across 13 charts and the one
that makes HelmCharts publishable.

KV path shape for every leaf:
`kv/eso/<cluster>/<ns-base>/<stage>/<leaf>#<key>` per Decisions.
(Audit §5 originally proposed `kv/eso/k8s/...`; the `k8s/` segment
dropped because ESO is the Kubernetes operator — the segment was
redundant with the consumer name `eso`.)

**Chart-side helper (one-time).** Before the first chart migrates,
land the `_externalsecret.tpl` helper (per `tmp/helmcharts-new-values.md`)
in HelmCharts. Walks `.Values.externalSecrets` and emits one
`ExternalSecret` per entry. One helper, every chart uses it. The
per-env values file then carries only `storeRef` + per-entry
`remote.path` overrides, never secret values.

**First pass — charts that already template `kind: Secret`** (the
"easy" subset where pod spec doesn't change). From audit §3.b:
`dnsmasq` (`management-api-auth`), `filebeat` (`filebeat-es-credentials`),
`media` (`samba-creds`), plus the extra-manifest set
(`csi-rbd-secret-user`, `csi-cephfs-secret-user`, `storage-passwords`,
`media-passwords`, `scantopdf-passwords`, `fundachecker-passwords`,
`shell-passwords`, `infra-statistics-secrets`,
`librechat-credentials-env`, `librechat-vectordb`,
`backup-server-tokens`, `backup-server-age-key`).

Per chart:

1. `bao kv put kv/eso/<cluster>/<ns-base>/<stage>/<leaf> <key>=<value>`
   for each secret value the chart's Secret currently embeds.
2. Extend `openbao_eso_kv_paths` with
   `kv/eso/<cluster>/<ns-base>/<stage>/*` (one entry per
   ns+stage tuple); converge OpenBao.
3. In the chart, drop the `kind: Secret` template, add an
   `externalSecrets:` entry to `values.yaml` that targets the
   *same* Secret name pods already reference. The `_externalsecret.tpl`
   helper materialises an `ExternalSecret` whose `target.name`
   matches. Pod specs unchanged.
4. Remove the secret values from `configs/<env>/<chart>-values.yaml`.
5. Re-deploy the chart; ESO syncs on the next refresh; consumer
   pods restart via the chart's existing checksum annotation
   (or get a deliberate kick).

**Second pass — secrets lurking inline in `configs/<env>/*-values.yaml`**
(audit §3.a; pod spec *does* change to `valueFrom: secretKeyRef`).
The majority case. Many charts use `value: {{ .Values.X | quote }}`
in their deployment templates; this becomes
`valueFrom: { secretKeyRef: { name: ..., key: ... } }`. Per chart:

1. KV write + policy widen, as first pass.
2. Add an `externalSecrets:` block in the chart `values.yaml` that
   declares the logical Secret and its keys.
3. Promote the inline values to their own ExternalSecret-backed
   Secret via the helper. Update the deployment template's `env:`
   to `valueFrom: secretKeyRef:` referencing the materialised
   Secret. Pod spec change is *real* — not avoidable for charts
   that use `value:` directly.
4. Remove the per-env literal from `configs/<env>/*-values.yaml`.
5. Re-deploy.

**Third pass — hard-coded literals inside chart templates** (audit
§3.c; same shape as second pass but the literal isn't in
`configs/`, it's in `charts/<chart>/templates/*` or
`charts/<chart>/values.yaml` defaults). 13 charts: `design-assistant`
(POSTGRES_PASSWORD + DATABASE_URL + rabbitmq.auth.password),
`electronics-inventory` (same), `guacamole` (POSTGRESQL_PASSWORD,
likely intentional split from electronics-inventory),
`iot`, `keycloak`, `media` (samba template literal),
`open-webui`, `registry`, `terminus`, `webathome-org` (MySQL).
Pre-migration verification per audit §3.c:

- electronics-inventory vs. guacamole DB password are accidentally
  identical; use distinct values at migration.
- The `POSTGRES_PASSWORD` + `DATABASE_URL` pair within each chart
  is intentionally the same value (one DB, two consumers in the
  same template). One KV leaf, two `secretKeyRef`s.

Mechanically the third pass is the second pass shape, applied to
templates rather than values files.

**Fourth pass — secrets in chart `files/` directories loaded into
ConfigMaps** (audit §3.d). 13+ charts use the
`(.Files.Glob "files/**").AsConfig` pattern to embed files into
ConfigMaps; some of those files carry secret material. Affected
charts:

- `calendar-support` — `files/service-account-key.json` (Google
  service account, PEM private key inside), plus borderline
  `files/calendars.json` and `files/config.json` (operator decides
  KV-or-ConfigMap).
- `media` — `files/gluetun/wg0.conf` (TorGuard WireGuard
  PrivateKey + Endpoint, travel together), plus
  `files/mydownloads/config.xml` (TVDb API key, Firebase server
  key, Plex pw, two user pw hashes).
- `pgadmin` — `files/pgpass` (reuses electronics-inventory and
  guacamole DB passwords from §3.c).
- `phpmyadmin` — `files/10-webathome-org.php` (reuses webathome-org
  MySQL root password from §3.c).
- `version-poller` — `files/config.yaml` (Jenkins API token + 5
  pipeline trigger tokens).
- `elasticsearch` — `files/kibana/kibana.yml`
  (`xpack.security.encryptionKey`).

Mechanism per chart:

1. Split `files/` into a non-secret subtree (still
   `Files.Glob`'d into the ConfigMap) and a secret subtree
   (excluded from the Glob target).
2. KV write + policy widen as for the other passes.
3. ExternalSecret materialises a Secret whose `data.[].secretKey`
   matches each filename; the pod volume-mounts the Secret
   (typically `subPath: <filename>`) into the same path the app
   reads.
4. For "split a file into secret-fields + non-secret-fields"
   cases (kibana.yml, mydownloads config.xml), the chart change
   is non-trivial — either init-container templating with envsubst
   from env vars sourced from the Secret, or splitting the file
   so the secret-portion lives in a separate mountable file.

This pass is mechanically the most disruptive of the four — the
volume-mount split is more invasive than the `value:` →
`valueFrom: secretKeyRef:` change of the second/third passes. Do
chart-by-chart with one commit per chart.

**Non-trivial chart changes flagged in the audit, called out
individually:**

- `charts/mosquitto/templates/mosquitto-configmap.yaml:47` —
  `passwordEntries` interpolated into a ConfigMap, not a Secret.
  ESO can't materialise ConfigMaps. Chart change: render the
  bcrypt block as a Secret and mount as a file, or add an
  init-container that templates from a mounted Secret at pod
  start. Non-trivial; flag for its own commit.
- `storage` dev: `backup-server-age-key` ConfigMap holds an
  AGE-SECRET-KEY private key, and `backup-server-tokens`
  ConfigMap holds a `dev-token` that's meant to be secret. Flip
  both to Secrets in the same change as the migration.
- `charts/media/templates/samba-secret.yaml:11` — literal samba
  password hard-coded in the chart template itself (not values).
  Replace with ExternalSecret ref to `kv/shared/samba/users`.

**One chart per commit** — these are independent moves; review and
rollback need to be tractable.

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
  the four irreducible credentials plus the small URL set;
  an `iac` invocation resolves every ref. Removing one path from
  `openbao_iac_agent_kv_paths` and re-converging breaks `iac` at
  startup with a clear policy-denied message.
- **Jenkins** — a representative pipeline (one with multiple
  secrets *and* a global-env-var reference) runs green. The
  Jenkins credential UI no longer holds any of the migrated
  entries. Global env vars are visible in Manage Jenkins → System
  with the URLs/realm names from C.2 step 1. `withVault` token
  rotation: pull the `jenkins` AppRole `secret_id` to a fresh
  value, re-paste into the `jenkins-vault-approle` credential, the
  next pipeline run picks up the new credential.
- **ESO** — `kubectl get externalsecret -A` shows every chart's
  sync as `Ready`; `kubectl get secret -A` shows every previously
  Helm-templated Secret. Edit a KV value in OpenBao, force-sync the
  ExternalSecret, verify the k8s Secret updates within seconds; for
  envFrom-style consumers a pod restart picks it up, for
  volume-mounted secrets the file updates in-place.
- **Per-consumer accounts** — for each new account minted under the
  named-accounts principle (Elasticsearch, MQTT, HA, OpenAI,
  GitHub PAT), confirm the old shared credential is revoked / no
  longer used by anything in the live system. `grep -r` across
  HelmCharts + the Jenkinsfile fleet for the old value's literal
  catches stragglers.
- **Vault file** — `grep -rl 'ANSIBLE_VAULT\|!vault' ansible/`
  shows the same files as before (no regression in the irreducible
  set, no leftovers from migration drafts).
- **HelmCharts publishability** — `grep -rE '(password|secret|token|key)' configs/`
  shows no plaintext credential values, only path references and
  non-secret config. Same grep on `charts/*/templates/` shows no
  hard-coded literal credentials (the audit §3.c set is gone).
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
- **Per-chart Helm work is the slow part.** Don't batch; one
  chart per commit makes review and rollback tractable. CLAUDE.md
  "commit early and often" applies in HelmCharts. Expect the §3.c
  third pass to dominate effort: 13 charts × 1–2 commits each.
- **iac and ESO friction "add a new secret" remains four-touch.**
  Jenkins is two touches (`bao kv put` + pipeline edit) because
  policy is `jenkins/*`. iac and ESO are per-leaf and per
  `<cluster>/<ns-base>/<stage>` respectively — KV write +
  group_vars edit + converge + consumer-side ref. Each consumer's
  runbook paragraph reflects this.
- **No automated drift between consumer config and KV paths.** A
  pipeline that references a KV path the policy doesn't grant
  fails at runtime, not at config-edit time. A small lint script
  comparing each consumer's referenced paths against
  `openbao_*_kv_paths` would catch divergence pre-merge; not in
  v1 scope.
- **Pod spec changes for the §3.a / §3.c migration.** The first
  pass (charts already templating `kind: Secret`) keeps pod specs
  unchanged. Second and third passes — the majority — flip
  `value: {{ .Values.X }}` to `valueFrom: secretKeyRef:`. That's
  a real spec change visible in `kubectl describe`, not the
  "transparent" shape the original slice draft assumed.
- **`tmp/jenkins-credentials-dump.txt` is a transcript-visible
  dump of live credentials.** It existed for the audit; it has
  no future role. Captured in the §Loose ends rotation list —
  every credential it names rotates on slice close.

## Loose ends to settle before this slice closes

Items surfaced during the sweep that aren't blocking the migration
itself but must close before walking away. Keep this list updated
as work lands; review at end-of-slice for nothing-left-behind.

- **Per-app Ceph RGW users via HomelabTerraformProvider.** Today's
  shape: one shared `csi-prd` RGW user in `kv/shared/ceph-rgw/s3`.
  Target shape: per-app users, minted by TF at chart provision
  time, landing in each chart's own `kv/eso/...` path. Once that
  lands, retire the **`csi-prd` access_key/secret_key** (credential
  only — no storage migration; the user, its buckets, and any
  data stay put) and remove the `kv/shared/ceph-rgw/s3` entry. See
  decisions.md §Ceph RGW credentials. Tracking the `csi-dev` user
  nuke + `csi-prd` credential retirement here so neither gets
  forgotten when the TF resource lands.
- **Guacamole chart wiring for OIDC client_secret.** Chart
  currently wires only `OPENID_CLIENT_ID` (see
  `charts/guacamole/templates/guacamole-deployment.yaml:68-69`),
  implying the OIDC implicit flow. The Keycloak `guacamole`
  client has a `client_secret` regardless; the secure default
  for Guacamole + Keycloak is the authorization-code flow with
  both. Add `oidc.clientSecret` to chart values + wire
  `OPENID_CLIENT_SECRET` env var in the deployment template,
  then `kv/eso/prd/guacamole/prd/oidc#client_id,client_secret`
  becomes the canonical leaf. Sequence the chart-template change
  before guacamole's §C.3 sweep. Surfaces a broader methodology
  gap — the audit catches "secrets that *are* embedded" but not
  "secrets that *should* be wired but aren't"; see
  `tmp/further-audit-request.md`.
- **Per-app readonly DB users for pgadmin / phpmyadmin.** Today
  pgadmin's `pgpass` and phpmyadmin's `10-webathome-org.php` hold
  the *admin* DB passwords for guacamole, electronics-inventory,
  and webathome-org (same values as audit §3.c). After the §3.d
  fourth pass, pgadmin/phpmyadmin become additional consumers of
  the same KV leaves. The named-accounts answer is to mint
  readonly Postgres/MySQL users dedicated to the admin UIs; the
  KV leaf for pgadmin/phpmyadmin then becomes its own credential
  with bounded privilege. Forward work — not a precondition for
  the §3.d migration, but worth doing before considering the
  named-accounts pass closed.
- **MyDownloadsClient + ScanToPdfClient keystore rotation.**
  Audit / dump shows both `MyDownloadsClient_keystore_secret` and
  `ScanToPdfClient_keystore_secret` are set to the same value,
  `z)!+eImU3BOh`. Distinct values per keystore at migration time.
  Same value is also the operator's personal Linux password — that
  rotates too, independently of the keystore values.
- **Credential rotation on slice close.** Every credential the
  migration handled — particularly anything in
  `tmp/jenkins-credentials-dump.txt`, `tmp/secret-inventory.md`,
  and any other tmp/ scratch — has been in transcript-visible
  scope. Operator rotates each (`bao kv put` with the new value,
  then the consumer picks up on next refresh). Rotation here is
  the *point* of the named-accounts work; do it as a single
  end-of-slice pass once every consumer is migrated.
- **`tmp/` shred.** `shred -u` on `tmp/jenkins-credentials-dump.txt`,
  `tmp/secret-inventory.md`, `tmp/helmcharts-new-values.md`,
  `tmp/naming-review.md`, plus the `tmp/openbao-credentials/`
  staging dir from the AppRole-cred rework. Low-ceremony given
  rotation handles the security side, but it removes the bait.
- **Workstation `.env` files in DesignAssistant checkouts.** They
  hold prd Ceph credentials today. Vault doesn't help — plain
  text on the workstation by necessity. Resolution: per-stage
  Ceph users (above) so the workstation `.env` can carry a
  dev-only user that's harmless if leaked. Tracked here, not a
  pre-close blocker, but it's the natural follow-on to the TF
  RGW work.
- **`checkout scm` refactor in Jenkinsfiles.** Most pipelines'
  `git { branch, credentialsId, url }` blocks can collapse to
  `checkout scm`, dropping the credentialsId reference entirely.
  The Jenkins controller still needs the underlying GitHub PAT
  credential for SCM polling + webhook receivers, so the
  credential entry doesn't go away — only the in-pipeline
  references do. Co-traveler with C.2; not a precondition.
- **Mosquitto ConfigMap-to-Secret chart change.** Flagged in C.3.
  Either a templated init-container or a chart redesign that
  splits the password file into its own Secret + mount. Counts as
  one of the 13 charts but it's the most disruptive of them; do
  last in the §3.c third pass so the easy ones build the helper
  template muscle memory first.
- **step-ca bootstrap secrets — extract from HelmCharts to
  ansible-vault.** `configs/prd/step-ca.yaml` today holds the
  four bootstrap-tier Secrets (`step-ca-config`,
  `step-ca-secrets`, `step-ca-ca-password`,
  `step-ca-ssh-host-ca-password`) as base64-encoded literals.
  These cannot move into OpenBao (chicken-and-egg — OpenBao's
  own listener cert is issued by this same path; see
  decisions.md §Internal TLS). To make HelmCharts publishable
  they extract into ansible-vault'd files materialised by a
  small Ansible role at cluster bring-up; the chart consumes
  pre-existing k8s Secrets unchanged. Same tier as the seal key
  and JWK provisioner password — see decisions.md
  §Bootstrap-tier ciphertext. Public material (`step-ca-certs`:
  intermediate cert, root cert, SSH host CA pub) can stay in
  HelmCharts as-is. Work shape: new `step_ca_bootstrap` Ansible
  role (or fold into an existing role) + drop the four Secret
  manifests from `configs/prd/step-ca.yaml` + update
  `docs/runbooks/step-ca-bootstrap.md` with the bring-up order.
  Independent of the main sweep — schedule alongside or after
  the C.3 publishability pass.
- **Decision on duplicate OpenAI keys.** Audit §2.a notes
  `OPENAI_API_KEY_CI_CD` and `OPENAI_API_KEY` (DA validation)
  may be the same value. Decide during C.2 whether to collapse to
  one KV leaf or keep distinct per-pipeline.
- **Further audit passes (DockerImages / AnsibleSpecs / Ansible
  repo).** Three downstream audit passes captured in
  `tmp/further-audit-request.md`. None blocking; fold findings
  into per-chart C.3 sweeps as they touch each chart, or into a
  follow-up slice if a finding is sufficiently distinct (e.g. a
  DockerImages-side image rebuild that's its own piece of work).
- **`custom_metadata` convention — ADOPTED (2026-06-02).** Every kv
  leaf carries:
  - `notes` — freeform sourcing/rotation context.
  - `rotated_at=<ISO date>` — present once minted fresh; absence means
    transcript-exposed / still needs rotation.
  - `rotation` — trust class: `unrestricted` (we mint, no other party),
    `coordinated` (we mint but must register in a system we run),
    `external` (a third party mints it).
  - `rotation_mechanism` — the system/handler used to mint the
    replacement (`random`, `postgres`, `rabbitmq`, `keycloak`, `mqtt`,
    `elasticsearch`, `kibana`, `ceph-rgw`, `ceph-cephx`, `samba`,
    `jenkins`, `home-assistant`, `proxmox`, `ssh`, `wifi`, `dnsmasq`,
    `backup-server`, `android-keystore`, `mysql`, `openai`, `google`,
    `github`, `mouser`, `twitter`, `torguard`, `third-party-blob`).

  `rotation` is the trust axis; `rotation_mechanism` is what a rotation
  job dispatches on. Tooling in the Ansible repo: `scripts/openbao-
  annotate-rotation.sh` (classify + stamp, idempotent), `scripts/
  openbao-rotation-audit.sh` (checklist of leaves still needing
  rotation, grouped by mechanism), `scripts/openbao-rotate-
  unrestricted.sh` (the `random` handler). Future per-mechanism
  rotation cronjobs key off `rotation_mechanism`, each scoped to one
  system's admin creds + an OpenBao policy over just that mechanism's
  leaves (avoid one god-job with admin to everything).
- **Strays in kv (not real secrets).** Two leaves are excluded from
  the rotation tooling (`is_stray` in the scripts) and want cleanup:
  `test/nested/leaf` (test data — delete) and `eso/jenkins-approle`
  (sits outside the `eso/<cluster>/…` grammar — looks like a misplaced
  write of the Jenkins Vault AppRole secret_id; investigate before
  deleting/relocating). Operator-owned.
- **Q6 naming aesthetics — accepted as-is.** Operator's review
  pass produced one rename (`home-assistant` → `homeassistant`
  because the HelmCharts chart is `homeassistant-mcp`); other
  proposed names (`dns-reservation`, `dhcp-app`,
  `iotsupport-pipeline-oidc`, `mydownloads-android-keystore`,
  `keycloak-iotsupport-admin`, `keycloak-da-admin`) stand. Final;
  no re-litigation needed during the sweeps.
- **calendar-support borderline files.** `calendars.json`
  (calendar IDs + emails) and `config.json` (RIVM `servicekey`
  in URL) — operator decides KV vs. leave-in-ConfigMap during
  calendar-support's §C.3 sweep. Default = KV both unless the
  operator opts out.
- **mydownloads keystore.password verification.** Audit §3.d
  flagged `<password>password</password>` in
  `charts/media/files/mydownloads/config.xml:8`. Verify whether
  it's a placeholder (in which case strip from the migration set)
  or a real value (in which case move to KV).
- **version-poller pipeline-tokens grouping.** Bundle five
  pipeline trigger tokens (`helmcharts`, `dockerimages`, `home`,
  `newsfilter`, `webathome`) into one
  `kv/eso/prd/version-poller/prd/pipelines` leaf (default), or
  split per-pipeline. No rotation-cadence reason to split;
  bundle unless operator prefers granularity.

## Commits

This slice produces commits across multiple repos. Suggested cadence:

1. **/work/AnsibleSpecs** — slice rewrite (this change) + the
   matching decisions.md additions, single commit. Further
   tweaks during execution land as additional small commits
   rather than slice rewrites.
2. **/work/Ansible** — `openbao_<consumer>_kv_paths` grow
   per-consumer in `group_vars/openbao.yml`; one commit per
   migration batch, same drift cycle reconverges the AppRole
   policies. C.0 widens for shared paths (one commit covering
   all three consumers); C.1/C.2/C.3 widen as their sweeps
   progress. The iac-agent and openbao runbooks gain their
   cold-boot + global-env-var sections — separate commit late in
   the slice.
3. **/work/HelmCharts** — `_externalsecret.tpl` helper, single
   commit, lands before the first chart migration. Then **one
   commit per migrated chart** (the "truckload" individual moves).
   The mosquitto chart change is its own commit set, last.
4. **Jenkins pipeline repos** — out of scope for this repo; commits
   live alongside the HelmCharts commits since most pipelines live
   in chart-adjacent CI definitions. The `checkout scm` refactor
   is a co-traveler (§Loose ends) — each pipeline's commit can
   bundle the refactor with the `withCredentials → withVault`
   migration if convenient, or split it.
5. **/work/HomelabTerraformProvider** — out of scope for this
   slice; the per-app RGW user resource lands in its own slice
   (see decisions.md §Ceph RGW credentials). When it lands, a
   follow-up sweep in this repo retires `kv/shared/ceph-rgw/s3`.
6. **/work/IaCAgent** — `etc/iac/secrets.example.yaml` schema
   updates, one commit per batch of refs added in C.1.
