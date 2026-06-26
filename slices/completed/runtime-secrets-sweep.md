# Runtime secrets sweep — consumer migration into OpenBao + rotation

> **Completed.** Consumer migration is done — all production charts read from
> OpenBao. The remaining rotation + slice-close cleanup is deferred and tracked
> on the **Triage** board (cards #49 rotate transcript-exposed secrets, #50
> review/drop unused Jenkins credentials), not here.

## Goal

Every runtime secret in the homelab lives in OpenBao KV and is read through
the consumer's provisioned mechanism — ESO for in-cluster, the HashiCorp Vault
plugin for Jenkins, `iac-impl`'s `!bao` resolver for everything that runs
through the IaC agent. On top of that the slice now owns two finishing goals:

- **HelmCharts is publishable** — no plaintext credential anywhere in the repo
  (values, templates, or `files/`), only path references and non-secret config.
- **Every secret rotates automatically** — not just minted-once. A per-mechanism
  rotation system keyed off `rotation_mechanism` metadata replaces values on a
  schedule with no operator keystrokes for the self-rotatable classes.

Adding a new secret is then a one-path operation: `bao kv put kv/<consumer>/<name>`
+ a consumer-side ref (+ a policy widening if the path is new).

## Current state (2026-06-14)

The migration itself is essentially complete. What remains is rotation
automation, the publishability cleanup, and a cross-repo secret scrub.

**Done:**

- **Consumer infrastructure** — ESO `ClusterSecretStore openbao-prd`
  (auth via the `eso` AppRole, `caProvider` → `homelab-root-ca`); Jenkins
  HashiCorp Vault plugin + JVM-truststore init-container; `iac-impl` `!bao`
  resolver. Token-self capabilities + hard-fail-on-miss on every consumer.
- **Per-consumer sweeps** — `iac/secrets.yaml` literals → `kv/iac/*`; the
  Jenkins credential store → `kv/jenkins/*` (with non-secret config moved to
  Jenkins Global env vars); HelmCharts charts → `kv/eso/<cluster>/<ns>/<stage>/*`
  via the shared `externalsecrets` helper (~28 of 45 charts carry an
  `externalSecrets:` block). Policies are globbed per principal
  (`jenkins/*`, `eso/prd/*`, `eso/dev/*`, `iac/*`).
- **Per-app Ceph RGW users** — `homelab_s3_storage` (provider) + the
  `s3-storage` TF module mint a scoped per-release RGW user into each release's
  `s3-credentials` Secret. The old shared-`csi-prd`-for-every-chart pattern is
  gone (`csi-prd`/`csi-dev` users and pools deleted); the only residual
  `kv/shared/<env>/ceph-rgw/s3` entry is the **admin** key the module uses to
  mint per-release users.
- **DB / RabbitMQ connection strings split** — KV leaves carry only `password`;
  the chart composes the URL at deploy time via Kubernetes `$(VAR)`
  interpolation (`…:$(DB_PASSWORD)@…`). Minted passwords are URL-safe
  (`[A-Za-z0-9]`) so the composed string can't break.
- **Cold-boot runbook** — per-consumer sections (Jenkins, ESO, iac) in
  `docs/runbooks/openbao.md`.
- **Rotation scaffolding** — the `custom_metadata` taxonomy (`rotation` trust
  class + `rotation_mechanism`) is stamped on every leaf; `scripts/rotation/`
  (`annotate.sh`, `audit.sh`, `rotate-unrestricted.sh`) is shipped and the
  `random` handler rotates every `rotation=unrestricted` leaf. See
  [`scripts/rotation/README.md`](../../Ansible/scripts/rotation/README.md).

## KV path grammar (reference)

```
kv/iac/<leaf>#<key>                                       (iac-agent)
kv/jenkins/<leaf>#<key>                                   (jenkins)
kv/eso/<cluster>/<ns-base>/<stage>/<leaf>#<key>           (eso)
kv/shared/<area>/<leaf>#<key>                             (cross-consumer)
```

Consumer-rooted (policy is per-consumer); `<cluster>` is `prd`/`dev` and
`<stage>` is always present; `<leaf>` is one hyphen-compound segment grouping
co-rotated keys (`oidc#client_id`+`oidc#client_secret`). URLs never enter
Vault — they live in chart values or Jenkins Global env vars. Per-consumer
named accounts over shared accounts of convenience; `kv/shared/` is reserved
for values that are genuinely one principal in many places.

## Remaining deliverables

### 1. Automatic secret rotation

The headline remaining work. The taxonomy and the `random` handler exist;
build the rest so every self-rotatable secret rotates on a schedule. Roadmap
and constraints are in [`scripts/rotation/README.md`](../../Ansible/scripts/rotation/README.md);
the deliverables here:

- **Per-mechanism handlers**, one job per `rotation_mechanism`. Each is scoped
  to one system's admin creds + an OpenBao policy that can write **only** that
  mechanism's leaves (`rotation_mechanism=<x>` makes the query trivial). No
  single job with admin to everything.
  - `random` — **done** (`rotate-unrestricted.sh`).
  - `coordinated` (a system we run): `keycloak`, `postgres`, `rabbitmq`,
    `elasticsearch`, `kibana`, `mqtt`, `ceph-rgw`, `ceph-cephx`, `samba`,
    `jenkins`, `home-assistant`, `proxmox`, `ssh`, `dnsmasq`, `backup-server`,
    `wifi`, `android-keystore`. Suggested order: `keycloak` (largest clean
    chunk) → `postgres`/`rabbitmq` last (stateful — `ALTER` + verify the app
    reconnects + roll back on failure).
  - `external` (third party mints — `openai`, `google`, `github`, `mouser`,
    `twitter`, `torguard`, `third-party-blob`): not self-rotatable. The system
    surfaces them on a checklist for operator fetch-and-paste, not silent skip.
- **Whole-file blobs** (`pgpass`, `kibana-config`, `version-poller/config`,
  `mydownloads-config`, `webathome-org-config`, `gluetun-wg`) need a handler
  that rebuilds the file, not a blind random replace.
- **Co-rotation** — leaves that share a value rotate together (`audit.sh`
  already flags these).
- **Scheduling** — run the handlers on a schedule (k8s CronJob or the
  `iac-scheduled-*` Jenkins pattern); each restarts/notifies the affected
  consumers. Decide the cadence per trust class.
- **Subsumes slice-close rotation** — the first automated pass mints a fresh
  value for every leaf still missing `rotated_at` (i.e. still transcript-
  exposed), including the `jenkins` AppRole `secret_id` (see §5).

### 2. HelmCharts publishability finish

- **Chart-template plaintext fallbacks** — the ESO-migrated stateful charts
  still carry real plaintext in their `else` branches (DATABASE_URL,
  POSTGRES_PASSWORD, rabbitmq defaults) plus the `configs/dev/*` dev-cluster
  secrets. Finish by deploying ESO to the dev cluster, populating its
  `externalSecrets`, then dropping the `else` literals + `configs/dev/*` secret
  values. Pairs naturally with the `postgres`/`rabbitmq` handlers in §1.
- **step-ca bootstrap secrets** — extract the four `step-ca-*` Secrets from
  `configs/prd/step-ca.yaml` to ansible-vault, materialised by a small Ansible
  role at cluster bring-up (these can't move to OpenBao — chicken-and-egg with
  OpenBao's own listener cert; see decisions.md §Internal TLS). Independent;
  schedulable any time.
- **Guacamole OIDC `client_secret`** — chart wires only `OPENID_CLIENT_ID`
  today (implicit flow). Add `OPENID_CLIENT_SECRET` + authorization-code flow,
  then `kv/eso/prd/guacamole/prd/oidc#client_id,client_secret` is the leaf.

### 3. Cross-repo secret scan

New. A valid Jenkins token was found sitting in DockerImages **test data** —
the migration cleared the known surfaces but never swept the repos
exhaustively. Stand up a repeatable secret scanner and run it across:

- **HelmCharts, Ansible, AnsibleSpecs, DockerImages** — working-tree scan, plus
  a git-history pass (the DockerImages token shows literals hide in test
  fixtures and old commits, not just live config).
- **TerraformState** — now sops-encrypted. The current tree is fine; the point
  here is to **verify the unencrypted history is gone** (history rewrite /
  confirm the pre-sops plaintext state is unreachable), not just that HEAD is
  clean.

Deliverable: a documented scanner (e.g. gitleaks/trufflehog) + an allowlist for
known-safe matches, ideally wired into CI so regressions are caught. Every
finding gets rotated via §1 and the literal removed.

### 4. Delete the KubernetesConfig repo

`/work/KubernetesConfig` is superseded — its bring-up contents
(`.microk8s.yaml`, MetalLB pools, registry config, install docs) folded into
the `microk8s` role + inventory during the build-out. It also holds secrets.
**Mark for deletion and delete the repo** (no scan — it's going away wholesale).
decisions.md previously said "archived after Phase 4"; the disposition is now
deletion because of the secret content.

### 5. Slice-close loose ends

- **`jenkins` AppRole `secret_id` rotation** — the no-TTL `secret_id` was
  briefly copied into KV, so it stays valid until rotated. Fold into §1's
  `jenkins` handler or do as a one-off (mint fresh + re-paste the
  `jenkins-vault-approle` credential + destroy old accessors). Operator-owned.
- **pgadmin** — secret handling deferred; the chart will be **deleted** when
  [`postgres-cluster-substrate`](postgres-cluster-substrate.md) lands. No work
  here.
- **phpmyadmin** — **drop from scope**; operator no longer uses it and the
  chart will be deleted. (Removes the webathome-org MySQL admin-creds leak with
  it.)
- **Keystore values** — give MyDownloads / ScanToPdf keystores distinct values;
  the shared value is also the operator's personal Linux password, rotated
  independently.
- **Optional / non-blocking** — a KV-path lint script (referenced-path vs.
  policy divergence at config-edit time); the `checkout scm` Jenkinsfile
  refactor (drops in-pipeline `credentialsId` refs; the controller PAT stays).

## The irreducible vault set (won't change)

After this slice the ansible-vault still holds exactly these bootstrap-tier
entries — none can move to OpenBao by definition:

- `openbao_admin_role_id` / `_secret_id` — authenticates to OpenBao itself.
- `internal_tls_jwk_provisioner_password` — OpenBao's listener cert is issued
  by this same step-ca path.
- `roles/openbao/files/static.key` — the OpenBao seal key.
- `vrrp_auth_password` — the `keepalived` role runs inside the `openbao` role
  on srvvaultN; the VIP must come up before OpenBao is reachable.

## Verification

- **Migration** — `grep -rE '(password|secret|token|key)' configs/` and the
  same over `charts/*/templates/` show no plaintext credential, only refs +
  non-secret config. `kubectl get externalsecret -A` is all `Ready`; an `iac`
  round-trip resolves every `!bao` ref; a representative Jenkins pipeline runs
  green against OpenBao-backed secrets.
- **Rotation** — after the first automated pass, every non-`external` leaf
  carries `rotated_at`; `audit.sh` reports an empty checklist for the
  self-rotatable mechanisms. Rotating a `coordinated` leaf (e.g. a Keycloak
  client secret) and forcing a sync leaves the consumer working.
- **Cross-repo scan** — the scanner runs clean (modulo allowlist) across all
  five repos, history included; TerraformState has no recoverable pre-sops
  plaintext.
- **KubernetesConfig** — repo deleted.
- **Vault file** — `grep -rl 'ANSIBLE_VAULT\|!vault' ansible/` shows only the
  four irreducibles above.
- **Drift cycle** — a full `iac-scheduled-drift` cycle is green end-to-end.
