# Decision record

> **End-of-push handling.** This document is transitional scaffolding for the initial homelab build-out. When the initial push closes, every section here needs to be either:
>
- **executed upon** — the decision is implemented in code and the section retired, or
> - **absorbed** — the text moves to a permanent home (project README, role README, runbook, or inline comment at the right code site).
> Don't treat this as a long-lived constitution. It expires.
>

> Source of truth for design decisions on this repo. When a decision changes, update this file — don't leave stale notes elsewhere.

## Scope

- **Ansible manages**: Proxmox hosts (100%), k8s VMs + cluster (100%), Ceph VMs + cluster (100%), Linux dev box base setup (partial — home-folder bits TBD).
- **Out of scope**: Home Assistant, Windows VMs, end-user devices, IoT.
- **Deferred**: UDM Pro + managed switch.
- Proxmox cluster is a real cluster (3 physical nodes, one PVE cluster).
- Ubuntu-only for Linux VMs.

## Design principles

Load-bearing rules. Specific decisions in this doc are consequences; if a principle changes, expect downstream decisions to need revisiting.

- **Terraform owns infrastructure state; Ansible owns OS/application state.** Disk geometry is Terraform; the filesystem on the disk is Ansible. VM existence is Terraform; packages on the VM are Ansible.
- **All roles are idempotent and safe to re-run.** Convergence is the model; drift is the trigger. Expensive work runs only on drift; a no-drift run is a fast no-op.
- **Cluster changes are serialized.** No parallel mutations of k8s or Ceph nodes. `serial: 1` plus drain/cordon hooks. Never two nodes at once.
- **The orchestrator cannot orchestrate its own replacement.** The Jenkins agent VM is mutated from the operator workstation, never from a pipeline running on itself. Self-reboot during orchestration is avoided.
- **Critical infrastructure sits outside the blast radius of what it depends on.** OpenBao does not run inside the k8s cluster that needs its secrets. The Jenkins agent does not run inside the k8s cluster it deploys to. Hosts that the dnsmasq pod depends on must not depend on it for DNS.

## Tool split

Three tiers, each with its own ownership tool. The line between tiers is unit lifecycle.

- **Ansible — bring-up tier.** Lifecycle == the host's. Proxmox host config, VM OS baseline, microk8s/microceph install + upgrade, cluster infrastructure that exists before any application does (CNI mode + autodetect, MetalLB IP pool, kernel modules, addon enablement, registry mirror config, CSI driver install).
- **Terraform — declarative resource tier.** Lifecycle decoupled from any single host, declarative API available. VM existence (`bpg/proxmox` provider, lives in this repo's `terraform/`). Per-application durable resources via the homelab provider (Ceph RBD images, CephFS subvolumes, ZFS datasets), the kubernetes provider (namespaces, static PersistentVolumes), and the Keycloak provider (realms, clients, roles). The per-application TF lives alongside the Helm chart in `/work/HelmCharts`, not in this repo.
- **Helm — runtime tier.** Lifecycle == an application release. Deployments, StatefulSets, Services, Ingress, ConfigMaps, application Secrets, PVCs (claimed against TF-owned PVs), HPAs, PDBs. Per-stage values files. Continues to deploy via Jenkins.

Worked examples:

- A Ceph RBD image outlives every pod that mounts it. TF owns the image; Helm owns the pod that mounts the PVC.
- A Kubernetes namespace outlives any single chart in it (reinstalls, multiple subcharts). TF owns the namespace; Helm deploys into it.
- A static PersistentVolume holds data. TF owns it with `claimRef` pre-binding and `Retain` reclaim policy. The PVC that binds it is templated by Helm.
- A Keycloak realm represents identity, not application code. TF owns it. Helm charts consume it.
- microk8s itself, microceph itself, the CSI drivers — all cluster bring-up, all Ansible.

Why three tiers, not two: Ansible at the resource layer is a thin wrapper around shell-outs with no state model. Terraform's resource graph, plan-time drift detection, and explicit destroy semantics match what Ceph / Kubernetes / Keycloak expose as declarative APIs. Helm's job — application runtime — doesn't change.

**Per-application TF lives in `/work/HelmCharts`.** Each release directory carries an optional `infrastructure.tf` (resources the chart depends on — namespace, PVs, Ceph images, ZFS datasets) and an optional `configuration.tf` (resources that depend on the chart being deployed — Keycloak realm config). The deploy CLI runs `terraform apply infra` → `helm upgrade --install` → `terraform apply config`. Per-release TF state, separate from this repo's VM-tier state. Design: [`docs/plans/09-helm-tf-deploy-harness.md`](plans/09-helm-tf-deploy-harness.md). Provider extensions for Ceph + ZFS resources: [`docs/plans/08-tf-provider-resource-extensions.md`](plans/08-tf-provider-resource-extensions.md).

**TODO — chart lifecycle in the HelmCharts refactor.** The refactor must cover the full chart lifecycle, not just updates to existing charts: deploying a brand-new chart and deleting a chart both need first-class support. Today `resolve-helm-args.py` fails for new charts, and deletion isn't handled at all. Mechanism is open — tracked here so the refactor design closes both gaps.

**Terraform and Ansible never invoke each other** — peer tools sequenced by the operator (or by Jenkins for the application monorepo). A composite operation that needs both — drain via Ansible, `terraform apply -replace`, reattach + re-converge via Ansible — is documented in the relevant runbook as a sequence of operator commands, never a single playbook that shells out to `terraform`. Keeps responsibility boundaries clean: TF changes are auditable in `terraform plan`; Ansible changes are auditable in `--check --diff`; mixing them blurs both, and a TF failure halfway through an Ansible play is harder to recover from than a TF failure between two playbook invocations.

**Operator-runs-TF rule** (CLAUDE.md) governs this repo's `terraform/` (VMs, host wiring) — those applies happen at the operator's keystroke. The application monorepo's per-release TF runs through Jenkins alongside Helm; Jenkins is the orchestrator for the application deploy, just as it has been for `helm upgrade --install`.

The pre-Ansible `/work/KubernetesConfig` repo predates this split: it codified bring-up steps (`.microk8s.yaml`, MetalLB IPAddressPools, registry mirror config, procedural install docs) in a third location that today belongs on the Ansible side. Phase 4 absorbs its contents into the `microk8s` role and inventory; after Phase 4 lands, KubernetesConfig is archived. The operator runs their own ingress controller and own container registry from HelmCharts — `core/ingress` and `core/registry` are not enabled.

## Secrets — OpenBao

- **OpenBao**, not HashiCorp Vault proper. Linux Foundation fork, MPL 2.0, API-compatible with Vault. All Vault integrations work unchanged: `community.hashi_vault` (Ansible), External Secrets Operator (Helm), HashiCorp Vault Jenkins plugin.
- Runs as a **3-node cluster** of dedicated VMs on Proxmox — `srvvault1` / `srvvault2` / `srvvault3`, one per PVE host (VMIDs `913–915`). Not in Kubernetes, to avoid the chicken-and-egg where k8s needs secrets that live in k8s. **Integrated Raft** for replication and leader election; same application-layer HA shape as the existing k8s and Ceph clusters. PVE-level HA was rejected — ZFS replication needs ZFS on each node, and shared storage either reintroduces the Ceph chicken-and-egg or requires hardware investment.
- **Static seal** with the key at `/etc/openbao/seal/static.key` (`openbao:openbao 0400` — the slice's `root:openbao 0440` would drift on every dpkg upgrade because the .deb postinst runs `chown -R openbao:openbao /etc/openbao`), the same file on all three nodes. Auto-unseal on every boot from local disk. The seal key is distributed via **ansible-vault** — encrypted file in the repo, passphrase in Roboform; a fresh node receives the key from `ansible-playbook --ask-vault-pass` on first apply. Azure Key Vault auto-unseal was the previous design and is dropped — no cloud dependency, no service principal, no Azure firewall.
- **Recovery keys**: Shamir 3-of-5, stored in Roboform. Used only for admin ops (rekey, re-seal, new root token) — never during boot.
- **Endpoint**: clients hit `https://secrets.home:8200`, a VIP managed by Keepalived on all three nodes. A `vrrp_script` polls `/v1/sys/leader` every two seconds; only the current Raft leader's check succeeds, raising its VRRP priority above the followers and pulling the VIP to it. Failover on a leadership change is typically ~4–6 s. No HAProxy, no nginx, no manual DNS flips.
- **TLS**: per-node leaf cert; SANs cover the node's short hostname, FQDN, and `secrets.home` (the VIP). Issued by the homelab `step-ca` via the JWK provisioner, driven by the `internal_tls` Ansible role; 47-day validity, re-issued by the role on every iac-scheduled-drift cycle once remaining validity drops below threshold. See "Internal TLS / homelab CA" below for the broader CA design.
- **Network boundary**: ufw on each srvvaultN. Default-deny inbound. Allow `8200/tcp` from k8s node IPs and from the Jenkins agent VM; `8201/tcp` (Raft) and VRRP (IP proto 112) from the other two srvvaultN; `22/tcp` from the Jenkins agent VM only. No management VLAN; vmbr0 only.
- **Admin path**: operator reaches OpenBao via VSCode Remote-SSH from `wrkdevwin` into the Jenkins agent VM, then `bao` / port-forwarded UI from there. `wrkdevwin` holds the personal SSH key for that one hop; the Jenkins agent VM holds the OpenBao admin token, automation SSH keys for the fleet, and any other privileged material.
- **Wife runbook**: points at Roboform emergency access + recovery-key procedure. Lives in `docs/runbooks/`.
- **Future direction**: peer-unseal between two sites (cheap USB-attached HSM at a friend's house unsealing ours; ours unsealing theirs) remains available — it would restore a three-domain isolation model. Lower priority now that Azure is out of the picture.

### Secret rotation — TODO codify

Rotation of AppRole `secret_id`s and of application secrets lives in the operator's head today; the `runtime-secrets-sweep` slice exercises the flow but doesn't formalise it. Four distinct patterns to capture:

- **AppRole `secret_id` whose value lives in OpenBao KV** (`iac-agent`): `bao write -force auth/approle/role/<name>/secret-id` mints a new one without invalidating the old; `bao kv put kv/<consumer>/...-approle role_id=… secret_id=…` updates the canonical copy. The resolver picks it up on next refresh. Old `secret_id`s are explicitly destroyed via `auth/approle/role/<name>/secret-id-destroy` after the new one is in use.
- **AppRole `secret_id` whose value lives in the consumer's UI credential store** (`jenkins`): `bao write -force` to mint, paste the new `secret_id` into the existing credential in Jenkins → Manage Credentials, then `bao write auth/approle/role/jenkins/secret-id-destroy accessor=<old-accessor>` once pipelines have picked up the new value. The Jenkins case sits in this category because the HashiCorp Vault plugin doesn't bridge to `kubernetes-credentials-provider` (no `SecretToCredentialConverter` extensions), so the credential is operator-typed into the UI rather than ESO-materialised — and JCasC was rejected as over-machinery for a rotation that's operator-initiated, not TTL-driven.
- **AppRole `secret_id` whose value lives in a hand-staged k8s Secret** (`eso` — bootstrap-tier): same `bao write -force`, but the new value is written via `kubectl create secret … --dry-run=client | kubectl apply -f -` into the `openbao-eso-approle` Secret in the `external-secrets` namespace, followed by `kubectl rollout restart deployment/external-secrets` because ESO reads the AppRole material on pod startup only.
- **Application secrets** (everything under `kv/iac`, `kv/jenkins`, `kv/eso/<chart>`): `bao kv put` to the new value; consumer picks up on next resolution. No restarts.

TODOs:
- Capture all three patterns in `docs/runbooks/openbao.md` (per-consumer cold-boot sections already planned by the slice — fold rotation into the same per-consumer subsections).
- Decide whether a `scripts/bao-rotate-approle.sh` helper is worth shipping. Two-liners don't strictly need one, but a helper makes "is it time to rotate?" cadence work easier.
- Decide the rotation cadence policy itself (calendar-driven? incident-driven only?) — not codified anywhere yet.

## Ceph RGW credentials — per-app, minted by TF

Today's posture: a single Ceph RGW user, `csi-prd`, holds the production S3 credentials used by every chart that talks to S3 (design-assistant per stage, electronics-inventory, iot, librechat, etc.) and by the Jenkins artifact-publishing pipelines. A second user, `csi-dev`, exists for the workstation cluster (`srvk8sdev`) but is unused — every prd-cluster deployment, across all chart stages (`@prd`, `@uat`, `@tst`, `@dev`), authenticates as `csi-prd`. The runtime-secrets-sweep slice migrates this shape into `kv/shared/ceph-rgw/s3` as a *transitional* shared bucket and flags retirement here.

- **The "dev" in `csi-dev` maps to cluster, not app stage.** All storage in all namespaces on the prd cluster goes to `csi-prd`, regardless of which app stage the chart is at. The `csi-dev` user has no production traffic; it can be nuked.
- **Per-app RGW users are the right shape, minted by the HomelabTerraformProvider.** Each chart deployment owns its own RGW user, keyed to its namespace and stage. The TF provider gains a `homelab_ceph_rgw_user` (or similar) resource; chart provisioning writes the minted access_key/secret_key into the chart's own `kv/eso/<cluster>/<ns-base>/<stage>/s3#access_key_id,secret_access_key` path. Rotation is per-app; blast radius bounds itself.
- **Once per-app minting lands, retire the `csi-prd` credential.** Just the access_key/secret_key pair — the user, its buckets, and any data stay put; no storage migration. The shared credential exists today only because there was no other available access pair; per-app users make it redundant. The `kv/shared/ceph-rgw/s3` entry the runtime-secrets-sweep slice writes is explicitly transitional and retires in the same pass (delete the KV path, `radosgw-admin key rm` to invalidate the old access key, or rotate it to a value no consumer has).
- **Workstation `.env` consequence.** DesignAssistant local-dev `.env` files hold prd Ceph credentials today, because `csi-prd` was the only available account. Per-app minting plus a dedicated dev-workstation account (per checkout, or one shared workstation user) breaks the prd-creds-on-workstation leak without changing the workstation workflow. Tracked in the runtime-secrets-sweep slice's §Loose ends as a follow-on.

Forward-looking; the runtime-secrets-sweep slice does not block on this. It captures today's shape in `kv/shared/`, flags it transitional, and hands off to the slice that adds the TF resource.

## OpenBao backup / DR

- **Canonical backup**: a daily `.tgz` bundling a native Raft snapshot (`bao operator raft snapshot save`) and a plaintext JSON export of the KV secrets + policies + auth/mount config. The snapshot is the restore artifact — atomic, complete, and the supported recovery path. The JSON export is break-glass: it lets a secret be read with `age` + `jq` and no running OpenBao, and is not itself a restore mechanism.
- **Runs on all three nodes; leader-only execution.** Each srvvaultN has a systemd timer (daily, randomised delay) that fires the same wrapper script; the script guards on `/v1/sys/leader`'s `is_self` flag, so the two followers exit in milliseconds and only the leader writes. If a leadership election is in flight when the timers fire, all three skip — the next cycle picks it up.
- **Backup path**: the wrapper authenticates via an AppRole with a read-only export policy — `list`/`read` on the policy catalogue, auth methods, mounts, and the KV-v2 tree, plus `read` on `sys/storage/raft/snapshot` for the snapshot — assembles the `.tgz`, and POSTs it to the in-cluster `backup-server` (a small Go service in `/work/DockerImages/backup-server/`, deployed by the `storage` chart in `/work/HelmCharts`). The bearer token authorising the upload lives on each srvvaultN as a file (mode 0400, owner openbao), materialised there by the `openbao` role.
- **Server-side encryption.** `backup-server` holds the operator's age public key (single recipient, in the `backup-server-age-key` ConfigMap), encrypts each upload with it, and streams the ciphertext via `rclone` to the existing cloud-storage path. The age **private** key lives only in Roboform; without it, no backup is recoverable. **OpenBao itself never holds the age key, public or private** — encryption happens server-side.
- **Retention** is enforced server-side by `backup-server` (per-scope `tokens.yaml` entry — keeps the N most recent objects, prunes the rest after each successful upload). The OpenBao timer is fire-and-forget; it does not manage retention.
- **All three srvvaultN are excluded from the cluster vzdump job.** The seal key and Raft data live on the same rootfs; bundling them in a PVE backup would defeat the seal. The `backup-server` upload is the only backup; this also forces drills to exercise the path that actually matters.
- **Recovery paths**:
  - *Single-node loss* (PVE host down, VM corruption, disk failure): Terraform recreates the affected srvvaultN; `bootstrap` + `baseline` + `openbao` roles converge; static seal key arrives via ansible-vault; the role's join task points the new node at the existing cluster; OpenBao Raft pulls the snapshot from the leader. VIP is unaffected throughout — it lives on whichever surviving node is leader.
  - *Whole-cluster loss* (all three down simultaneously, the extreme case): Terraform recreates all three; roles converge into a fresh empty cluster — first node initialises with the same seal key, the others Raft-join. The latest `.tgz` is pulled from cloud storage with `rclone` and decrypted with the age private key from Roboform; `bao operator raft snapshot restore` replays the snapshot into the fresh cluster. The restore replaces cluster state with the snapshot's, so the AppRole credentials and the Shamir recovery-key configuration come back intact — consumers need no credential redistribution, and the Roboform-held recovery keys still work. ESO resyncs Kubernetes Secrets; consumers reconnect.
- **Failure domains**: two — Roboform (Shamir recovery shards + age private key + ansible-vault passphrase) and the cluster-plus-its-backups (Raft data + live seal key on each srvvaultN + age public key on `backup-server` in k8s + the cloud-storage path with the encrypted backups). Both must leak for full secret compromise. Three-domain isolation existed under the Azure design; one domain was deliberately given up to remove the cloud dependency.
- **Bootstrap dependency**: the daily backup requires k8s + the `storage` chart's `backup-server` to be up. OpenBao itself does not depend on either for booting or serving secrets — only the daily backup write does. A k8s outage longer than one cycle means one or more missed daily backups; recoverability falls back to the previous successful dump.
- **Recovery drill** is a Phase 2 deliverable: exercise the single-node-loss path on the live cluster (rebuild one VM, watch the Raft snapshot stream from the leader); exercise the whole-cluster path on the real srvvault VMs (rebuild all three, fresh init, snapshot restore). Document timings in the runbook.
- **Whole-site recovery (new hardware) is bring-up-ordered — master runbook is a TODO.** A fire/theft rebuild is not OpenBao-first: the homelab CA (`step-ca`) runs on Kubernetes and OpenBao's listener leaf depends on it. Forced order — bare metal → core VMs → k8s control plane + Ceph → `step-ca` → OpenBao (converge + snapshot-restore) → ESO and the OpenBao-dependent workloads. It is not a deadlock: `step-ca` deliberately needs nothing from OpenBao (JWK provisioner password in ansible-vault, root key in Roboform, its k8s Secret hand-created — the step-ca slice's "no ESO in v1, chicken-and-egg"). Component runbooks exist — `step-ca-bootstrap.md`, `k8s-rebuild.md`, `openbao.md` §3, `iac-cold-boot.md` — but **no master site-DR runbook sequences them; that is the TODO.** Card #14's whole-cluster drill only covers OpenBao loss against an otherwise-healthy homelab; the new-hardware path is a distinct, larger drill. Related robustness gap: `internal_tls` hard-fails first leaf issuance when `step-ca` is unreachable (no retry, no self-signed bootstrap), so the recovery order is currently load-bearing rather than self-correcting.

## Runtime secrets — IaC agent resolver

Once OpenBao is up, runtime secrets are resolved at IaC-container startup by an extended `iac-impl`. The pattern lives in one place — the IaC agent — and downstream consumers (Ansible, Terraform, Jenkins agent launcher, `send_message.py`) see exactly the same environment variables and on-disk files as today.

- **`/etc/iac/secrets.yaml` is an override layer over OpenBao.** Each `env:` value and each `files:` `content:` is either a literal or a `!bao <mount>/<path>#<key>` reference. `iac-impl` parses with a custom YAML constructor; literals win unmodified, refs are resolved against OpenBao before any clone / state-sync / user command runs.
- **`iac-impl` is rewritten from bash to Python** in `pvginkel/IaCAgent`. Python deps land in `pvginkel/Ansible`'s `pyproject.toml` because the iac container bakes its venv from there. One language, one entry point, room for future drift checks.
- **AppRole auth.** The IaC container's OpenBao identity is an AppRole named `iac-agent`. `role_id` + `secret_id` live in `secrets.yaml` as literals (the irreducible-literal set). Rotation is operator-driven: generate a fresh `secret_id` in OpenBao, paste into srviac's `secrets.yaml`, restart the container.
- **Least-privilege policy.** The `iac-agent` AppRole's OpenBao policy grants `read` only on the KV paths `secrets.yaml` references. New refs require both a file edit and a policy widening; mismatches surface as hard-fail at next container start.
- **Hard-fail on miss.** Unresolvable ref, AppRole rejection, or network failure terminates `iac-impl` before any clone / state / exec runs. The container is short-lived per `iac` invocation; running with stale or missing values is unsafe.
- **Irreducible literals (the bootstrap-tier secret set):**
  - `OPENBAO_URL`, `OPENBAO_ROLE_ID`, `OPENBAO_SECRET_ID` — gate the path that fetches everything else.
  - `GIT_API_TOKEN` — needed to clone the Ansible + TerraformState repos before any further resolution can happen.
  - JWK provisioner password (from the step-ca slice) — stays in ansible-vault, not in `secrets.yaml`, but conceptually the same tier.
  - Static seal key passphrase (ansible-vault) — same tier.
  - Age private key — never in `secrets.yaml`; lives only in Roboform.
- **Cold boot.** Operator pulls each ref's value from Roboform, substitutes literals into `secrets.yaml`, runs the IaC container until OpenBao is restored, flips refs back. Documented as `docs/runbooks/iac-cold-boot.md`. Same shape and mental model as the wife runbook.
- **What does *not* get its own AppRole.** Ansible-via-iac-impl consumes env + files materialised by the resolver before it ever runs, so it does not need an AppRole of its own. Jenkins (for pipeline secrets) and ESO (for in-cluster secret sync) each retain their own AppRoles + policies; Ansible does not.
- **Operational consequence.** OpenBao becomes a hard runtime dependency of every `iac` invocation — Jenkins post-stages, ad-hoc operator runs, scheduled drift. Outages above the seal-key + clone window manifest as IaC-paralysis until OpenBao is back or the operator runs the cold-boot procedure.
- **TerraformState repository sync.** There's currently a full daily sync of all my GitHub repos into a site that gives unauthenticated access to all my code from my local network. This includes the TerraformState repository. The scripts must be changed to specifically exclude this repository.

## Internal TLS / homelab CA

Homelab-wide CA for internal-DNS TLS. Stands up in its own phase ahead of OpenBao so the CA is proven against four consumers (PVE, microk8s API, DNS management API, `backup-server`) before any OpenBao role-apply touches it. OpenBao's three listener certs follow in the next phase using the same role.

- **`step-ca`** (Smallstep), Helm-deployed from `HelmCharts`.
- **Two issuance paths from a single CA, by consumer location**:
  - **In-cluster consumers** use cert-manager driven by step-ca's **ACME** provisioner, replicating the existing public-cert flow (cert-manager + Let's Encrypt) with a different directory URL. A step-ca `ClusterIssuer` lands in HelmCharts; consumers opt in by annotation on their Ingress. No bespoke Ansible plumbing.
  - **VM consumers** use a reusable Ansible role, `internal_tls`, driving step-ca's **JWK** provisioner via `step ca certificate` / `step ca renew`. The role installs `step-cli`, pulls the JWK provisioner password from ansible-vault into a `mktemp` file for the duration of the task, issues or renews, installs the cert with the caller-specified path / mode / owner, and notifies the caller's reload handler. Threshold-gated re-issue (default 14 days remaining) runs on every iac-scheduled-drift cycle.
- **JWK provisioner password is bootstrap-tier**: a single fleet-wide password, encrypted in the Ansible repo via ansible-vault, passphrase in Roboform. Lives alongside the OpenBao seal key, ansible-vault passphrase, and the IaC agent's AppRole credentials in the irreducible-literal set — never moves into OpenBao, because OpenBao's own listener cert is issued by this same path. Scoping comes from the provisioner's `allowedSANs` regex (`*.home` plus the kube-apiserver internal names) rather than per-consumer credentials.
- **Two-tier hierarchy**. `step ca init` produces root + intermediate. **Root key goes offline to Roboform immediately after init**; only the intermediate runs in the pod. Cluster compromise forges leaves until the next intermediate rotation; rotation is a one-shot from `wrkdev` and does not touch any client trust store.
- **Intermediate key + passphrase: regular Kubernetes Secret**, not delivered via ESO from OpenBao. The chicken-and-egg of OpenBao-needs-cert-from-step-ca-needs-passphrase-from-OpenBao is not worth the marginal security gain when short leaf validity already bounds blast radius. **Materialised at cluster bring-up via a small Ansible role from ansible-vault'd source files**, not committed as plaintext-base64 manifests in HelmCharts — same bootstrap-tier posture as the JWK provisioner password and the OpenBao seal key. Covers all four `step-ca-*` Secrets that currently live in `configs/prd/step-ca.yaml` (`step-ca-config`, `step-ca-secrets`, `step-ca-ca-password`, `step-ca-ssh-host-ca-password`); the only non-secret entry in that file is `step-ca-certs` (public certs + SSH host CA pub), which can stay in HelmCharts or move to a ConfigMap. Extraction tracked in the runtime-secrets-sweep slice's §Loose ends; this is what makes `configs/prd/step-ca.yaml` publishable.
- **Leaf cert validity: 47 days**, all consumers. The `internal_tls` role re-issues a VM leaf when remaining validity drops below 14 days; in-cluster leaves are re-issued by the monthly `certificate-renewer` CronJob. Each leaf's absolute expiry is published as the Prometheus gauge `internal_tls_cert_not_after_seconds` — written by the `internal_tls` role to a node-exporter textfile collector for VM consumers, and by an equivalent in-cluster collector for the certbot path. A single Prometheus alert fires on a stalled renewer at `<10` days remaining — below both the 14-day VM renewal threshold and the in-cluster monthly path's ~17-day steady-state floor, so it signals a real failure rather than flapping every renewal cycle. The alert rule and the in-cluster metric are **deferred** (observability is not a current priority); design parked in [`slices/deferred/internal-tls-monitoring.md`](slices/deferred/internal-tls-monitoring.md).
- **Trust-store distribution**:
  - **Managed Linux hosts**: the `baseline` role places the root cert in `/usr/local/share/ca-certificates/homelab-root.crt` and runs `update-ca-certificates`. Picked up automatically by openssl, curl, Python, Go, and most other Linux TLS clients. Root rotation = role edit + apply.
  - **Windows hosts** (`wrkdevwin` and similar): one-time manual import via `certutil -addstore -f "ROOT" homelab-root.crt` from an elevated shell. Covers Chrome / Edge / curl-on-Windows / most of the Microsoft stack. Firefox keeps a separate NSS trust store — either import there too or set `security.enterprise_roots.enabled=true` to make Firefox consult the Windows store.
  - **Phones and other end-user devices**: out of scope. iOS profile install + Android-7+ user-root restrictions make this not worth the friction. Anything that must be reachable from a phone with TLS validation stays on a public Let's Encrypt cert via an externally-resolvable hostname.
- **OpenBao bootstrap**: srvvaultN's first cert is issued by the same `internal_tls` role at role-apply time, no self-signed bootstrap step. Cold-boot of an existing srvvaultN uses the cert from disk; only renewal needs step-ca, so a step-ca / k8s outage shorter than ~33 days (47 − 14) is invisible to OpenBao consumers. Beyond that, the role's next attempted re-issue fails, and the cert eventually expires; OpenBao becomes unreachable until either step-ca returns or a cert is replaced manually.
- **Initial scope (v1)**:
  - VMs (`internal_tls` role): PVE Web UI / API (3 hosts), Kubernetes API server (3 microk8s nodes). OpenBao listener certs (3 srvvaultN) follow in the next phase via the same role.
  - In-cluster (cert-manager + step-ca ClusterIssuer): the DNS management API, `backup-server`.
  - Everything else (dnsmasq UI, other in-cluster service endpoints, IoT, printers) stays on snakeoil / self-signed until later sweeps; in-cluster services migrate by flipping their Ingress annotation when they get touched anyway.
- **Root rotation**: planned as a single event in year 9 (root cert validity 10 years from init). Yearly rotation rejected — the operational cost of touching every Linux trust store and every Windows machine annually outweighs the blast-radius benefit when the root key sits offline in Roboform.
- **SSH CA is a deferred follow-up.** step-ca can also issue SSH host and user certificates, which would replace the static `known_hosts.d/` + `authorized_keys` pattern in `bootstrap` / `adopt.yml`. Intentionally out of scope for the TLS slice — same CA instance gets a new SSH provisioner pair in a later slice, paired with a parallel `ssh_host_cert` role and sshd / ssh_config changes. The TLS slice doesn't need to anticipate it; the SSH slice can lean on the CA that's already running.

### Root rotation mechanism

The "year 9" rotation event needs both the outgoing and the incoming root trusted simultaneously for a transition window — every consumer pinned to either root must validate during the cutover. Mechanism:

- **In-repo shape: a single PEM bundle, `ansible/roles/baseline/files/homelab-root.crt`.** Holds 1..N concatenated PEM blocks. One file to review in PRs, one file the drift pipeline fetches from `https://ca.home/roots.pem` and compares against. Steady state is one cert; rotation windows are two.
- **Drift comparison is by fingerprint set, not byte diff.** Once the bundle carries two roots, `/roots.pem`'s ordering is no longer pinned to the repo's. The `iac-scheduled-drift` "Homelab CA root drift" stage parses both sides and asserts the SHA-256 fingerprint sets are equal.
- **On-host shape: one file per cert.** Debian's `update-ca-certificates` walks `/usr/local/share/ca-certificates/` and processes only one PEM block per `.crt` file; a multi-cert bundle dropped there is silently truncated. The `baseline` ca-trust task splits the bundle and writes each cert as `/usr/local/share/ca-certificates/homelab-root-<fp8>.crt`, where `<fp8>` is the first 8 hex chars of the cert's SHA-256 fingerprint. Naming by fingerprint (not by position-in-bundle) keeps filenames stable across bundle reordering and across removal of a root post-rotation, so neither churns `update-ca-certificates -f` runs.
- **The install task reconciles, not just writes.** baseline enumerates desired certs (from the bundle) against present `homelab-root-*.crt` files on disk and `state: absent`s the diff. Without this, the retired root lingers on every host past the cutover and is trusted forever. The existing self-heal grep against `/etc/ssl/certs/ca-certificates.crt` generalises to a loop over the desired set.
- **HelmCharts holds two copies of the same file** — `/work/HelmCharts/homelab-root.crt` and `/work/HelmCharts/charts/nginx/files/ca/homelab-root.crt`. A rotation that updates the in-repo bundle here must update both files there in the same change window, ordered *before* the new root starts appearing in step-ca's `/roots.pem` (otherwise the drift pipeline fires until HelmCharts catches up). Eventual fix is to collapse the duplication — single source via submodule, build-time fetch from this repo, or moving the canonical copy under HelmCharts and having Ansible read from there — recorded as a follow-up rather than blocking the next rotation.
- **Runbook**: `docs/runbooks/step-ca-root-rotation.md`. Documents the cutover sequence — generate new root offline, install in step-ca alongside the old, add to the bundle in both repos, confirm the drift pipeline goes green, fleet-wide `baseline` apply to land the second cert, soak, then remove the old root from step-ca + both repos + apply again to drop it from hosts. Parallels the existing "Intermediate rotation" section in `step-ca-bootstrap.md` but at a different scope and cadence.

TODOs gating the next rotation:
- Write `docs/runbooks/step-ca-root-rotation.md`.
- Update the `baseline` ca-trust task to read the bundle, split by cert, name by fingerprint, reconcile against `/usr/local/share/ca-certificates/homelab-root-*.crt`. Generalise the self-heal grep over the desired set.
- Update the `iac-scheduled-drift` "Homelab CA root drift" stage from byte diff to fingerprint-set comparison.
- Decide and implement the HelmCharts deduplication mechanism, or accept the two-copy maintenance burden by documenting both paths in the runbook.

## Bootstrap-tier ciphertext — public repo posture

The Ansible repo is public; ansible-vault'd files in it are too. The OpenBao seal key, the JWK provisioner password, the IaC agent's AppRole credentials, and (after the runtime-secrets-sweep slice) the step-ca chart bootstrap secrets all live in this tier. The security boundary collapses to **the strength of the ansible-vault passphrase + the fact that the passphrase lives only in Roboform behind 2FA**. This is a deliberate trade, not an accident.

- **What the boundary really is.** Public repo + private passphrase = "passphrase strength forever, against offline brute force." Realistic compromise vector at homelab threat-model strength isn't brute force — it's passphrase leak (workstation compromise, screen capture, Roboform compromise). The latter dominates risk; ciphertext-in-public moves the needle very little relative to ciphertext-in-private-repo when the passphrase is the actual gate.
- **Why this tier exists.** Pulling these out of ansible-vault breaks convergence-driven recovery: a fresh srvvaultN / step-ca pod / IaC container needs the bootstrap credential available to the Ansible apply, with no operator typing session. Hand-staging at every rebuild loses that. A separate private repo achieves it but adds a parallel-repo sync discipline the operator has explicitly rejected for HelmCharts and would reject for Ansible at the same logic.
- **Why this is acceptable.** The OpenBao seal key is the highest-value secret in the homelab and already sits at this tier. If that posture is acceptable for the seal key, it is strictly more acceptable for derived bootstrap-tier credentials (provisioner passwords, intermediate-CA passphrases, AppRole `secret_id`s for the IaC agent). New bootstrap-tier additions extend the existing posture without re-debating it.
- **Minimum passphrase entropy.** ≥20 random chars, or ≥8 diceware words. Ansible-vault's PBKDF2 + AES-256-CTR has meaningful margin against modern GPU brute-force at that bar. If the current passphrase is below this, rotation is more load-bearing than any other tightening here.
- **Rotation cadence.** Annual, or on suspicion of workstation / Roboform compromise. Mechanism is `ansible-vault rekey` against every vaulted file in the repo; one-shot, no node-side change. New tier additions don't change cadence.
- **Periodic review gate.** Each new bootstrap-tier addition is a chance to re-ask "still acceptable?" If the set grows past ~10 entries or if the homelab gains public-facing surface, re-evaluate. Until then, the posture is settled.
- **What this is NOT a license for.** Application secrets, runtime credentials, anything OpenBao can hold — do not slip into ansible-vault on the grounds of convenience. The tier exists for the irreducible bootstrap set; growth happens by genuine necessity, not by laziness.

## Workflow + learning

- "Bob Ross" mode: Claude builds and annotates, user reads, reviews, and tweaks. No step-by-step hand-holding.
- Design artifacts live in this repo (`docs/`, READMEs). Not in Claude's memory.
- Throwaway VMs on Proxmox are used for learning. No sacrificial Proxmox host is available.
- The existing procedural runbook in `/work/Obsidian/` is the source material for role content. Ported topic-by-topic as roles are built.
- microk8s/microceph setup is "scripted textually" — scripts still need to be located on disk.

## Transitional cleanup tasks age out

When a role removes a thing that won't naturally come back — an orphaned authorized_keys entry, a UI tag from a now-defunct workflow, scratch scripts left over from troubleshooting — the cleanup task is a one-shot. Once it has converged on every host that needed it, the task is dead weight: it runs on every future apply, finds nothing to do, and adds noise to the role.

**Policy**: remove transitional cleanup tasks from roles after they've successfully converged. The convergence is the proof the cleanup did its job; what's gone won't come back without an external regression. Schedule the removal as a separate commit a couple of weeks after the cleanup landed so the soak window is visible in git history.

If the cleanup target *can* recur (drift the operator might re-introduce — a value the UI lets you set, a file someone might re-create), keep the task. The bar for keeping is "this could come back without an unrelated bug introducing it."

## Adoption is a waypoint; rebuild is the parity event

Hosts brought under management without being built from scratch will never be byte-for-byte identical to a from-scratch role apply. Retroactively reconciling them is a pipedream; **rebuild is the only parity mechanism that actually works**.

Adoption is therefore a transitional state. Every adopted VM has a planned rebuild that ends the transition. Trigger per host class:

| Host class | Rebuild trigger          | Notes                                                                                                          |
|------------|--------------------------|----------------------------------------------------------------------------------------------------------------|
| k8s VMs    | As part of Phase 4       | microk8s state lives in `/var/snap/microk8s`; nothing OS-side worth preserving. `serial: 1` with drain/cordon. |
| Ceph VMs   | As part of Phase 5       | OSD disks reattached to fresh OS, not reformatted (see "Ceph rebuild path" below).                             |
| `wrkdev`   | Operator-scheduled       | Operator-managed; rebuild on operator's cadence.                                                               |
| pve hosts  | **No scheduled rebuild** | Bare metal, no shadow-clone, no destroy-and-recreate. Fidelity-only.                                           |

### Pre-rebuild sanity check (option)

For any rebuildable host, **file-based comparison against a shadow VM** is available as a per-host pre-rebuild check: spin up a from-scratch build via the role, rsync-diff against the live host with obvious exclusions (`/var`, `/proc`, `/sys`, machine-id, generated caches), inspect the residue. Not a routine workflow — the work only earns its keep right before a rebuild — but kept as a documented option because it's the only way to see exactly what was hand-modified outside the role.

### Fidelity for unrebuildable hosts (pve)

For the three pve hosts, fidelity to the role definitions is the only reachable goal. Mechanisms:

- `apt-mark showmanual` diff against the role's package list — highest signal.
- One-shot `/etc` snapshot (or `etckeeper`) → surfaces hand-edits since install.
- `systemctl list-unit-files --state=enabled` and `crontab -l` per user → catches scheduled side-channels.
- `ansible-playbook --check --diff` against the live host → anything `changed` is drift to either codify or consciously accept.

### Ceph rebuild path

Specifics deferred to Phase 5; the preferred shape is recorded here so the phase doc inherits the constraint:

1. **Upgrade first** — bring the cluster to its target microceph LTS channel via `snap refresh`, mons before OSDs, `serial: 1`. Soak under real workload for several days; confirm `HEALTH_OK` and that HelmCharts consumers are unaffected.
2. **Then rebuild** — drain a node, TF-replace the VM, apply baseline + microceph role, reattach the existing OSD disks (BlueStore OSDs carry their identity on-disk). Repeat one node at a time.
3. **Fallback if microceph won't adopt existing OSDs**: stand up a single-node temp cluster on `pve`'s spare `/dev/sda`, mirror data over (`rbd mirror` for RBD; rsync of a snapshot for CephFS), cut consumers over, rebuild the original nodes, migrate back, decommission the temp cluster, reclaim the spare.

Sequencing rationale: rebuild has no real rollback (once the rootfs is destroyed, you can't go back); upgrade does (`snap revert`). Doing the well-understood step first means the harder step starts from a verified baseline. If rebuild fails and we end up on the migration path, we're already on the target version — no double-handling.

### Ceph version policy

**LTS channels only.** Ceph is infrastructure the operator does not want to think about; chasing latest costs small surprises for negligible benefit on this workload. Track the current Ceph LTS, upgrade when the previous one goes EOL or sooner if a security fix forces it. Phase 5 picks the initial target channel against current state.

### Ceph daemon memory targets

10 GiB per-VM is the operating envelope for the microceph fleet (`srvceph1/2/3`). Microceph defaults — `osd_memory_target=4 GiB`, `mds_cache_memory_limit=4 GiB` — over-spec bluestore and metadata caches for this workload by ~2×: they fit fine on a node carrying only OSD+MON, but spill once a node also picks up the active MDS, MGR, and RGW. Symptom observed before tuning: srvceph1 sat at 8 GiB used / 1.5 GiB available with 4 GiB swap 100% full.

**Targets**:
- `osd_memory_target = 2684354560` (2.5 GiB) on the `osd` section. 2 GiB is the documented floor (`osd_memory_target_min`); 2.5 keeps a margin.
- `mds_cache_memory_limit = 1073741824` (1 GiB) on the `mds` section.

**Application**: cluster config DB via `microceph.ceph config set <section> <key> <value>`. The microceph phase encodes both as role variables (`group_vars/ceph_prd.yml` — e.g. `microceph_osd_memory_target`, `microceph_mds_cache_memory_limit`) and applies them through the same interface. Values stay tunable per-environment rather than hardcoded.

**Restart-on-change is mandatory.** Microceph's snap is not built with tcmalloc; the daemons use glibc malloc, which doesn't return fragmented arenas to the OS. Lowering the caps shrinks the daemons' internal caches but RSS stays put until the daemon restarts — a write-only task is silently ineffective. The role must restart the affected daemon (or, on first roll-out, reboot the VM) when these values change. Reboot fits the existing `serial: 1` cluster-changes pattern and reclaims any stale swap in the same step.

Deferred / revisit:
- **Initial roll-out, srvceph2/3.** srvceph1 was rebooted to apply the new targets and lands at ~2 GiB used / ~7.4 GiB available. srvceph2/3 still hold their pre-tuning OSD RSS (~3.7 GiB each) plus stale partial swap (~400 / 630 MiB) from the same prior pressure. Both have ample available RAM today, so the cleanup is symmetry, not urgency: drain (`microceph.ceph osd set noout` → `snap restart microceph.osd` → wait for HEALTH_OK → `unset noout`), then `swapoff -a && swapon -a`. Land before the microceph role lands so the role's first apply finds a clean baseline.
- **`MALLOC_ARENA_MAX=2` systemd override** on the microceph snap units. Caps glibc's per-thread arena count and limits long-run heap drift. Worth folding into the microceph role only if RSS climbs back over the targets in steady state; premature otherwise.
- **RGW placement: all three nodes.** RGW originally ran as a placed singleton on whichever node happened to be chosen at install (srvceph1, by install order). It now runs on srvceph1/2/3 so the `ceph.home` Keepalived VIP — which already follows the active mgr — also fronts S3, and any node failure leaves a working S3 endpoint behind. Per-node RGW is ~130 MiB and fits inside the existing memory envelope. The future microceph role should declare this placement explicitly rather than re-inheriting install order. **S3 endpoint convention:** in-cluster clients, future per-app TF (`infrastructure.tf` resources that provision buckets/users via the homelab provider), and the Helm → TF migration use `https://ceph.home` (the VIP) as the S3 endpoint — never a per-node hostname or backplane IP. Hardcoding a node makes the client lose access on a failover and silently couples to install order again.

### Ceph VIP migration

`ceph.home` (10.1.0.38) is a leader-tracking Keepalived VIP on srvceph1/2/3 — design captured in [`slices/internal-ha-vips.md`](slices/internal-ha-vips.md). Because srvceph1/2/3 are not Ansible-managed today, v1 of that slice configures Keepalived **by hand** on each node, with the exact `keepalived.conf` + mgr-tracking script recorded in `docs/runbooks/ceph-vip.md`.

**When Ceph moves to Ansible (Phase 5 — see [`phases/README.md`](phases/README.md))**, the `microceph` role takes over the VIP: it includes the shared `keepalived` role with the same VRID, VIP, password, and mgr-tracking script, and the hand-rolled config on srvcephN is retired in the same change. The manual runbook becomes a backstop for disaster recovery rather than the day-to-day path. Skipping this step would leave two sources of truth for the Ceph VIP config and silently drift on the next Phase 5 apply.

### k8s version policy

**Track a recent `stable` channel — not pre-release.** Same low-surprise logic as Ceph, but k8s moves fast enough that pinning to the previous LTS strands us behind the addon/CNI and HelmCharts ecosystem, so we track a current `stable` minor instead. Never `candidate`/`beta`/`edge` except for a brief, deliberate upgrade soak. Channel pinned per cluster in `group_vars/k8s_{prd,dev}.yml` so dev runs a minor ahead of prd and soaks it before prd moves. Upgrade when the running minor nears EOL, a security fix forces it, or a fix we need lands upstream.

Today: prd `1.35/stable`, dev `1.36/stable`, scratch `1.32/stable`. The strict-confinement variants (`*-strict/stable`) are rejected — extra surface for limited benefit on this workload.

**Known hazard on 1.35.** The `k8s-dqlite` watch poll loop can die on a transient and freeze the apiserver watch cache until the daemon is restarted ([k8s-dqlite#364](https://github.com/canonical/k8s-dqlite/issues/364) / [microk8s#5386](https://github.com/canonical/microk8s/issues/5386)) — controllers stop reconciling while `kubectl get` still reads fine, so it hides. The fix (k8s-dqlite PR #365) is unmerged, so it ships in no released build; only ≤1.32 predates the regression. Mitigated, not cured, by the `iac-dqlite-watchdog` job running `ansible/playbooks/recover-dqlite-watch.yml` (auto-restarts `k8s-dqlite` on a frozen node — see `docs/runbooks/dqlite-watch-freeze.md`). Take the upstream fix when it lands in a 1.35.x.

**A cluster upgrade also has to bump the `kubernetes` Python client in the other repos.** Several consumers reach the cluster API through the `kubernetes` Python client (all via the same `load_incluster_config()` + `get_default_copy()` pattern) and must pin it to the cluster's minor (`kubernetes~=32.0` for 1.32): the DockerImages images `dnsmasq-config-generator`, `nginx-configurator`, `infra-statistics`, `certbot` (each in its `requirements.txt` / `Dockerfile`); the `ZigbeeControl` app (`pyproject.toml` — currently lagging at `>=28,<29`, realign to `~=32.0`); and the Helm deploy tooling in `HelmCharts/tools/requirements.txt`. The client tolerates n±1 skew, so the safe order is: bump every pin to the new minor (e.g. `~=33.0`), rebuild + redeploy the affected images, *then* upgrade the cluster. Noted here because the sequencing is an upgrade-procedure concern even though the pins live outside this repo. Origin: a rebuild with an unpinned client pulled `kubernetes` 36.0.0, whose `auth_settings()` had regressed out of step with `load_incluster_config()`, sent every request unauthenticated, and broke service-annotation DNS.

### k8s node capability labels

Per-node capability labels reconciled by the `microk8s` role from `host_vars/<node>.yml`. Today's set:

- `homelab.local/performance=high` — node has materially more CPU than peers (today: `srvk8s1`, 8 cores vs. 3 on the smalls). Workloads that want fast cores opt in via required nodeAffinity (Jenkins agent template, Plex).
- `homelab.local/storage=zpool2` — node has the ZFS passthrough disk surfaced as `zpool2` (today: `srvk8s1`). hostPath workloads (storage chart, Prometheus) opt in via required nodeAffinity. The pool name in the label leaves room for `storage=zpool3` if a second pool ever lands.

Labels are operator intent, not auto-derived from facts. The TF-side facts (`cpu_cores`, `passthrough_disks`) are inputs to a deliberate decision about which nodes earn which capability label; host_vars carries the label declarations alongside the other per-node inventory data with inline comments back to the TF source. Auto-derivation is rejected — bumping a small node from 3 cores to 6 should not silently retag it as a Plex target.

No taints. Affinity is opt-in: workloads that need a capability declare `requiredDuringSchedulingIgnoredDuringExecution`; everything else schedules freely. The legacy `size=large/small` labels and the `size=large:PreferNoSchedule` taint are removed during Phase 4.

### Dashboard tooling

Today: microk8s's `dashboard` addon (the upstream `kubernetes/dashboard` project bundled with the snap). The operator depends on the web UI day-to-day; codified into `microk8s_addons` for prd and dev.

**Revisit after the plan**: [Headlamp](https://headlamp.dev/) (CNCF, modern UI, plugin system) deployed as a Helm chart in `HelmCharts`. Same web-UI workflow, version ownership shifts off microk8s's release cadence onto the operator's Helm flow. `k9s` (terminal UI) and OpenLens / desktop apps are off the table — operator wants browser-based.

## Environment mapping

Two Ansible inventories: `prd` and `scratch`. The split is **production-grade vs deliberately disposable**, not a risk gradient.

- **`prd`** holds every host that must keep working: the PVE cluster, the 3-node prod k8s cluster (`k8s_prd`), the dev k8s node (`k8s_dev` — `srvk8sdev`), the Ceph cluster, the 3-node OpenBao cluster (`srvvault1/2/3`), the operator workstation (`wrkdev`). All production-grade. CI's default path runs against this inventory.
- **`scratch`** holds the disposable Terraform-provisioned scratch fleet — today, two microk8s scratch nodes (`wrkscratchk8s1`, `wrkscratchk8s2`) used in Phase 4 to exercise the role install + idempotent join paths. The only hosts where breakage is free.

When a procedure says "test it on a scratch VM first," that means a host in the `scratch` inventory — never `wrkdev` or `srvk8sdev`. `wrkdev` is the operator's workstation; `srvk8sdev` is the single-node cluster used to develop HelmCharts against.

HelmCharts uses its own `configs/dev` and `configs/prd` folders. That split is independent of Ansible's inventories: Helm's `configs/dev` is for iterating on Helm charts themselves against `srvk8sdev`; `configs/prd` is for the production cluster. Don't conflate the two repos' uses of "dev."

The user's application has four deployment stages: `dev`, `test`, `uat`, `prd`. **All four run on the production Kubernetes cluster**, as separate namespaces named `<chart>-<stage>` — every namespace carries its stage suffix, including prd. These stages are the application monorepo's concern (Helm + per-release Terraform); Ansible does not see or manage them.

## DNS and hostnames

- DNS search domain is `.home`. Configured on the operator workstation directly; pushed to every managed Ubuntu VM as DHCP option 15 by dnsmasq, so the `baseline` role does not have to set it.
- All managed hosts **must** have forward DNS entries (`hostname.home`) resolvable from the operator workstation and from each other.
- Ansible inventories use **short hostnames**; the `.home` search domain fills in the FQDN. Never hard-code IPs.
- For Terraform-provisioned VMs, the per-VM module declares a `homelab_dns_reservation` resource that registers the (hostname, MAC) pair with the dnsmasq sidecar API; the API allocates the IPv4 from `10.1.3.0/24`. `depends_on` on the VM resource orders the reservation before VM create, so the VM's first DHCP request lands on a known reservation. See "MAC addressing" below for the resource shape.
- **Bootstrap-critical hosts do not resolve through the dnsmasq pod.** dnsmasq runs as a Kubernetes pod, so the k8s nodes themselves and the OpenBao cluster cannot depend on it: the cluster could not boot from cold if its nodes resolved through a service hosted on the cluster, and OpenBao must be reachable to deliver secrets to the cluster that hosts dnsmasq. These hosts carry static resolver configuration — `/etc/hosts` for the names they need at boot, plus an upstream resolver (LAN router or public DNS) reached directly. The configuration is not standard Ubuntu defaults; the `baseline` role applies it based on host class.
- **The operator workstation needs a secondary resolver too**, for the same reason. The dnsmasq pod runs as a 2-replica StatefulSet pinned to different k8s nodes, so a single node reboot is invisible to it — but if the workstation only knows about one of the two replicas, a roll that touches the node hosting that replica blacks out resolution from the workstation mid-run. DHCP option 6 advertising both replicas covers it; configuring both resolvers statically on the workstation works too. Either way, list both — never one.
- **Public DNS upstreams imply a `~home` routing domain.** Hosts configured with public DNS upstreams are configured at the same time with a systemd-resolved `~home` routing domain pointing at the two in-cluster dnsmasq LB IPs. The two pieces are a single decision, applied together by the `baseline` role from the same trigger (`network_devices[*].nameservers` defined). `registry` and `registry-dev` remain pinned in `/etc/hosts` (in-cluster dnsmasq depends on the registry to start); on the OpenBao nodes the three `srvvault{1,2,3}.home` peer triples also remain pinned (Raft `cluster_addr` re-resolves on every restart and a whole-cluster cold-boot must not depend on dnsmasq). No other `.home` names belong in `baseline_etc_hosts_entries`. Full-cluster outage slow-fails the rest at ~5 s; link DNS (and any non-`.home` query) is unaffected. See [`slices/completed/home-dns-routing.md`](slices/completed/home-dns-routing.md).

## Ingress isolation — TODO split public from internal

Today a single in-cluster NGINX ingress (chart: `nginx`,
`charts/nginx`) terminates **both** public sites (`is_public: yes`,
`*.webathome.org` / `*.ginbov.nl`, Let's Encrypt) and internal sites
(`*.home`, step-ca). Whether a request to an internal site is
rejected from the public internet depends on a per-vhost `allow
192.168.0.0/16; allow 10.0.0.0/8; allow 172.16.0.0/12; deny all;`
block emitted by the nginx-configurator template
(`/work/DockerImages/nginx-configurator/app/template.j2:14`).

History: the `{% if not a.is_public %}` guard around that block was
missing for a stretch. Every internal site got a public-resolvable
Let's Encrypt cert (because Certbot proves over the same listener
and the names are resolvable externally for cert issuance), and the
filter never fired. A single `/etc/hosts` entry on an attacker's
machine routed straight through. No log line, no error — the cert
validated, the site loaded.

The guard is in place now. The architectural problem isn't: the
model is still "every vhost gets the filter right, forever." One
typo (`is_public: yes` on the wrong site), one template regression,
one new annotation that bypasses `location /` — and the door
re-opens silently.

**Target shape**: two separate ingress Deployments + LB IPs, each
configured from a disjoint subset of `external-services.yaml`.

- **Public NGINX**: own Service + MetalLB LB IP, own upstream pool.
  Knows only `is_public: yes` sites. No `allow` rules anywhere —
  everything it serves is meant to be reachable. Let's Encrypt
  renewal lives here.
- **Internal NGINX**: existing behavior, internal LB IP, no path
  from the public internet (router NAT does not forward to this
  IP). step-ca renewal lives here. Filter rules become defense in
  depth, not the primary gate.

The hard property: the public ingress has **no upstream config for
internal sites**. Compromising the public NGINX exposes the public
set only — a network-level guarantee, not a template-correctness
guarantee.

Cost: one extra LB IP, `nginx-configurator` filters its view twice,
two cert renewal flows (public LE + internal step-ca — already
separate concerns), `dns.webathome.org/hostname` annotations become
class-aware so internal hostnames resolve to the internal LB IP and
public hostnames to the public one.

Not in scope for `runtime-secrets-sweep`. Belongs in the same broader
"HelmCharts publishable" arc — file a separate slice when the secrets
sweep settles. Captured here so future-self doesn't re-discover the
gap by reading the template comment and assuming "we always had this
right."

## Network topology for managed VMs

The Proxmox cluster has two physical bridges plus a workload VLAN on the first:

- **`vmbr0`** — 1 Gb house network. Internet-facing. Default route, DNS, DHCP (dnsmasq) all live here. Each managed VM's `network_devices[0]` lives on this bridge with `vlan_id=0`; the per-VM module's `homelab_dns_reservation` keys off that NIC's MAC.
- **`vmbr1`** — 10 Gb backplane between the PVE/Ceph/k8s nodes. Separate subnet, not reachable from the house LAN. Carries inter-node Ceph and Kubernetes traffic. Per-VM static address declared in `vms.tf` (or rendered guest-side at provision time); no IPAM, no reservation resource. Addresses are stable across rebuilds — the backplane is a shared subnet across PVE/Ceph/k8s/etc., so they're hand-curated.
- **`vmbr0` tag 2** — Kubernetes workload network. Same physical 1 Gb fabric as vmbr0, separate VLAN and subnet (`10.2.0.0/16`). Reserved for k8s services. MetalLB runs in **L2 mode** today — IPv4 in practice; the pool config carries an IPv6 CIDR but v6 is not the operational focus. BGP via MetalLB was partly set up and abandoned; the `10.2.0.0/16` allocation is preserved against re-enabling it — a backlog item, see Deferred below. Per-VM static address declared in `vms.tf`, sequential within `10.2.0.0/16`. No IPAM.

Per-host-class shape:

| Class                                                            | NICs                        |
|------------------------------------------------------------------|-----------------------------|
| Ceph nodes (`srvceph1/2/3`)                                      | vmbr0 + vmbr1               |
| k8s nodes (`srvk8s1/2/3`)                                        | vmbr0 + vmbr0 tag=2 + vmbr1 |
| Everything else (operator workstation, OpenBao cluster, scratch) | vmbr0 only                  |

Deferred / revisit:

- **Audit that vmbr1 actually carries the traffic it's meant to.** The 10 Gb backplane was built up incrementally; the operator is not confident every Ceph/k8s node is steering traffic over it as designed. Verify once Phase 3a is done and Terraform is the source of truth for VM network config — the audit is much cheaper against a known-declarative baseline.
- **Re-enable BGP mode for MetalLB.** Backlog item. MetalLB's BGP mode runs a speaker on each node that peers with one or more external BGP-capable routers (`BGPPeer` + `BGPAdvertisement` CRs; native BGP or FRR mode). The homelab has no BGP-speaking router today — standing one up is the gating dependency and the bulk of the work. The MetalLB pool's IPv6 side (dual-stack in config, not relied on) gets sorted as part of the same rework rather than as a separate effort. Distinct from Calico's BGP, which is separately tabled — the `microk8s` role runs Calico in VXLAN mode and strips the `k8s,bgp` CLUSTER_TYPE suffix.

## VMID convention

- **Operator-created VMs (legacy)** keep their existing VMIDs in the 100–199 range. Today: `103` (srvk8sl1), `104` (srvk8ss1), `107` (srvk8ss2), `113` (srvceph1), `114` (srvceph2), `115` (srvceph3), plus the unmanaged VMs.
- **Terraform-owned VMs** use the **900-and-up range**. VMIDs `900–909` are reserved for the scratch fleet (today: `wrkscratchk8s1=901`, `wrkscratchk8s2=902`); `910` and up belong to the persistent fleet. The convention extends to every TF-managed VM going forward.
- Phase 3a imports the six existing managed VMs under their legacy VMIDs — no live mutation, just modeling what's there. Phase 4 (k8s) and Phase 5 (Ceph) rebuilds reassign them to VMIDs in the 900-and-up range as a side-effect of the rebuild. This also rotates each NIC to the deterministic-MAC scheme below (the locally-administered MAC is derived from the VMID), and prompts a one-time dnsmasq reservation update per VM.
- Phase 2's `srvvault1`/`srvvault2`/`srvvault3` (OpenBao cluster, VMIDs `913–915`) and the (now-completed) iac-agent phase's Jenkins agent VM are greenfield in the 900-and-up range from creation.

## MAC addressing for managed VMs

- **New / rebuilt VMs**: NICs use deterministic MACs in the locally-administered range, computed from the Proxmox VMID. Pinned in Terraform so a rebuild keeps the same MAC.
- Format: `02:A7:F3:VV:VV:EE` — fixed locally-administered prefix `02:A7:F3`, then the VMID as two big-endian bytes (`VV:VV`), then the NIC index (`EE`). Example: VMID 900, NIC 0 → `02:A7:F3:03:84:00`.
- Constrains VMIDs to `[100, 65535]`. Validated at plan time by the `vm_id` variable.
- **Default**: VMs run DHCP on the NIC; cloud-init carries no IP/gateway/DNS config. dnsmasq is the single source of truth for IP and DNS, keyed off the pinned MAC.
- **Bring-up-tier hosts** (Ceph nodes, prd k8s nodes): cloud-init renders a static netplan from `vms.tf`'s per-NIC `addresses`/`gateway`/`nameservers` fields. `static_ip = true` on the `managed-vm` module suppresses the `homelab_dns_reservation` resource and tells the cloud-init template to write `/etc/netplan/50-cloud-init.yaml` directly. See "Ceph nodes / k8s nodes are static infrastructure" below for rationale. `srvk8sdev` is dev-tier and uses the dynamic-reservation default — it doesn't host registry/dnsmasq pods, so the cycle doesn't apply.
- **Legacy (pre-rebuild) VMs**: keep their existing Proxmox-generated `BC:24:11:...` MACs pinned verbatim in their TF modules. The deterministic scheme applies after the Phase 4/5 rebuild, at which point the dnsmasq reservation is updated in lockstep with the new MAC.
- **dnsmasq reservation as a Terraform resource**: managed VMs register their (hostname, MAC) pair with the dnsmasq sidecar API via a `homelab_dns_reservation` resource inside each per-VM module; the API allocates the IPv4. One apply registers the reservation and creates the VM, in that order; destroy reverses it. The sidecar is Helm-deployed; the static `static-hosts.yaml` continues to hold operator-curated entries (printers, IoT, network gear) in a separate namespace, and is overridden by API entries on hostname collision. Specs: [`specs/dns-reservation-api.md`](specs/dns-reservation-api.md), [`specs/dns-reservation-terraform.md`](specs/dns-reservation-terraform.md).
- **Ceph nodes and prd k8s nodes are static infrastructure, not dynamic reservations**: `srvceph1/2/3` and `srvk8s1/2/3` opt out of the `homelab_dns_reservation` resource via `static_ip = true` on the `managed-vm` module. Their hostname → IP triples live exclusively in HelmCharts `configs/prd/dnsmasq.yaml`'s static-hosts section, hand-curated alongside printers/IoT/network gear. Rationale: the dnsmasq sidecar runs in-cluster behind the registry; the registry container itself depends on Ceph storage to boot, and the cluster nodes that host both the registry and dnsmasq cannot get their own addresses or DNS from a service they themselves are required to bring up. Any chain that puts bring-up-tier addressing behind the dynamic API creates a cold-boot ordering failure. Static IPs (declared per-NIC in `vms.tf`, rendered into the cloud-init template's netplan section) sidestep the cycle entirely. External nameservers (`8.8.8.8` / `8.8.4.4`) are pinned at the host so containerd's image-pull DNS path on these nodes never depends on the cluster being healthy. `srvk8sdev` is dev-tier and stays on the dynamic reservation — it doesn't host registry/dnsmasq pods (dev pulls from external `registry-dev`), so the bring-up cycle doesn't apply.
- **Cloud-init is a first-boot artefact.** Its scope: ansible user, ansible SSH pubkey, pinned ed25519 host key, qemu-guest-agent, and (for hosts with static addresses on any NIC) the initial netplan render. After first boot, Ansible owns drift detection and convergence on these surfaces — the `static_netplan` task in the baseline role re-asserts `/etc/netplan/50-cloud-init.yaml` from inventory data (`static_netplan` host_var) so a static-IP change in `vms.tf` plus a matching host_var update lands on the running host without a rebuild. The `managed-vm` module pins `lifecycle.ignore_changes = [initialization]` on the VM resource so a template edit re-renders the snippet but does not recreate the VM. To pick up a template change on first boot of an existing host, rebuild via `terraform apply -replace='module.vm["<name>"]'`.

## OS image channels (cloud image canary)

`terraform/prd/main.tf` declares `local.os_image_channels` — a map from channel name to `{ url, file_name }` pointing at an Ubuntu cloud image. Each VM in `vms.tf` selects one via `image_channel = "<channel>"`; the default is `stable`. `proxmox_download_file.ubuntu_cloud_image` is keyed by `(pve_node, channel)` so a channel is downloaded to a PVE node only when at least one from-scratch VM on that node selects it.

Two channels today:

- **`stable`** — current LTS (today: noble / 24.04). Every from-scratch VM defaults here.
- **`testing`** — next LTS (today: resolute / 26.04). Single opt-in slot for canary work; `srvk8sdev` is the live canary.

Promoting `testing` → `stable` is a one-line edit in the channels map. Both URLs typically point at upstream's `/<series>/current/` symlinks; pinning to a dated build is allowed but not the default.

Each role's `meta/main.yml` lists every Ubuntu series the role is expected to support (today: `noble`, `resolute`) so ansible-lint reflects intent. The listing is informational — roles install via `apt` + `snap` + `netplan`, which work the same across LTS releases.

## SSH host keys for managed VMs

The homelab step-ca is also an SSH host CA. Every managed host serves a step-ca-signed SSH host certificate; Ansible verifies hosts through one committed `@cert-authority` line in `ansible/files/known_hosts.d/homelab`. Issuance and renewal are owned by the `ssh_host_cert` role, the SSH-side counterpart of `internal_tls`. Slice: [`slices/completed/ssh-host-ca.md`](slices/completed/ssh-host-ca.md). Ceremony: `docs/runbooks/step-ca-bootstrap.md` "Enabling the SSH host CA".

- **One provisioner, both cert types.** `ansible-jwk` issues the X.509 leaves and the SSH host certs — same fleet-wide vaulted password (`internal_tls_jwk_provisioner_password` in `group_vars/all/vips.yml`). Controller-side split issuance: the token is minted on the iac container, the host key never leaves the target.
- **47-day certs, 14-day renewal threshold.** Same shape as the TLS leaves; `ssh_host_cert` re-signs on each `iac-scheduled-drift` cycle when the cert is within the threshold, otherwise no-op.
- **No principal scoping in the SSH host policy.** The `@cert-authority` line is loaded only by Ansible's `UserKnownHostsFile` and Ansible only connects to homelab hostnames, so ssh's own principal-vs-connect-target check already rejects a forged cert with a non-homelab principal. Adding a host needs no CA change.
- **Terraform no longer writes the repo for host identity.** It still generates a per-VM ed25519 keypair (`tls_private_key.host_ed25519`, persisted in tfstate) and embeds the private half via cloud-init so the VM boots with a stable identity. The public half is surfaced as the `host_pubkeys` Terraform output and consumed only by the bootstrap playbook's transient known_hosts under `tmp/`, for the single pre-certificate connection to a brand-new VM.
- **sshd serves the ed25519 host key plus its certificate.** The role installs `/etc/ssh/sshd_config.d/10-homelab-host-cert.conf` with `HostKey` + `HostCertificate`. rsa/ecdsa stay off — sshd auto-generates them non-deterministically. `HostKeyAlgorithms` in `ansible.cfg` accepts the ed25519 host certificate (steady state) and plain ed25519 (the pre-cert bootstrap window).
- **Trust boundary.** The `@cert-authority` line is loaded only by Ansible's `UserKnownHostsFile`. The operator's personal `~/.ssh/known_hosts` is untouched.
- **Cold-boot envelope ~33 days.** A managed host's cert lives on its own disk, so step-ca outages shorter than 47 − 14 days are invisible. Beyond that, renewals fail and certs eventually expire; verification breaks until step-ca returns or a cert is replaced manually.
- **SSH user CA stays deferred.** This slice covers host certs only (replacing `known_hosts.d/`). Replacing `authorized_keys` with a user CA is a separate, lower-priority sweep.

## OS updates

Three policies, one per host class. The class is a property of the host, recorded in inventory.

| Class                      | Members                                               | Update policy                                                                                                                                                              |
|----------------------------|-------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Cluster members**        | k8s nodes, ceph nodes                                 | Ansible-controlled. `update.yml` plays drain → `apt full-upgrade` → conditional reboot → uncordon, with `serial: 1`. Operator-triggered for now; CI-scheduled in Phase 10. |
| **Standalone service VMs** | Jenkins agent VM, `srvvault1`/`srvvault2`/`srvvault3` | `unattended-upgrades` + auto-reboot in a quiet window. Ansible installs and configures the package, then steps back.                                                       |
| **Self-managed**           | Home Assistant, Windows VMs, IoT, end-user devices    | Outside this update system entirely. Documented but not managed.                                                                                                           |

Why the split:
- The Jenkins agent cannot run a pipeline that reboots itself — the orchestrator must not be what is being mutated. Letting the OS handle its own updates avoids this.
- OpenBao with static seal re-engages its seal automatically on reboot (key read from local disk), so it no longer needs the operator-triggered cadence the original "Ansible owns updates everywhere" rule assumed. With three nodes in a Raft cluster the cadence also matters less — quorum survives one node rebooting.

**OpenBao package exception.** The `srvvault1/2/3` policy above covers the OS — kernel, openssl, everything `unattended-upgrades` would normally pick up. The **`openbao` package itself** is the exception: OpenBao does not maintain an apt repository today (verified during card #8 — only `.deb` assets on GitHub releases and a community-maintained snap), so `unattended-upgrades` has no source to pull from. The `openbao` role downloads the pinned `.deb`, sha256-verifies it, and `apt install`s it; upgrades happen by bumping `openbao_version` + `openbao_deb_sha256` in role defaults, with `iac-scheduled-drift` picking the change up on the next cycle. Mirrors the microk8s snap-channel pin on k8s nodes: the cluster-critical daemon is version-pinned by Ansible, the rest of the box is `unattended-upgrades`.

Concrete behaviour:
- **`baseline` enforces the package state per host class.** On cluster members it purges `unattended-upgrades` (no silent fallback to Ubuntu defaults). On standalone VMs it installs and configures it. Observable state is "package state matches host class."
- **Stop-gap until `update.yml` lands**: `baseline_apt_dist_upgrade: true` on a cluster-member host forces a dist-upgrade through baseline. Manual but adequate for a homelab on a private network.
- **Drift pipeline ignores patch posture.** The apt cache refresh + dist-upgrade tasks in `baseline` are tagged `os_update`, and `iac-scheduled-drift` runs with `--skip-tags os_update`. Pending upstream packages are patch posture (owned by the update pipelines: `update-k8s.yml` today, future plays for ceph/etc.), not infrastructure drift. **Rework when a real cluster-wide update path supersedes the stop-gap**: once every cluster class has its own `update-*.yml` driving apt, the apt cache + dist-upgrade tasks should probably leave `site.yml` entirely (and the `baseline_apt_dist_upgrade` knob with them) rather than continuing to live in `baseline` behind a tag.

Operational guards (to be folded into runbooks/playbooks at the relevant phase):
- **Stagger reboot windows across the four standalone service VMs.** Jenkins agent + `srvvault1/2/3` must not reboot in the same window. For the OpenBao cluster specifically, no two srvvaultN should be in the same window — quorum survives one node rebooting, not two.
- **Post-boot health check on OpenBao.** After each srvvaultN's reboot window, confirm the node came back unsealed and Raft-joined within N minutes; alert otherwise. Catches silent static-seal failure (key file missing, wrong permissions, service did not start, disk corruption) and rejoin failure (Raft can't reach a peer, TLS expired) early instead of when the next consumer fails to fetch a secret.

## Proxmox VM CPU affinity

- **`pve` core zoning**: cores `0-11` are reserved for interactive workloads (operator dev box, jump box, scratch VMs); cores `12-19` are for background workloads (Ceph, Kubernetes, Home Assistant). `pve1` and `pve2` are different machines and not zoned — affinity does not apply to VMs running there.
- **Owner**: Terraform. The bpg/proxmox provider authenticates as `root@pam` (see `docs/runbooks/proxmox-credentials.md`), which lifts PVE's restriction on writing the `affinity` config field. The per-VM module's `cpu_affinity` input maps to `cpu.affinity` on the VM resource.
- **Source of truth**: the workload-class → core-range map lives in `terraform/prd/vms.tf` (mirrored in `terraform/scratch/vms.tf`). Each VM entry declares `workload_class = "interactive" | "background"`; the module call site computes `cpu_affinity = each.value.pve_node == "pve" ? local.workload_affinity_cores[each.value.workload_class] : null`. Pinning applies only on `pve`; VMs on `pve1`/`pve2` pass `null`.

## Terraform applies on cluster members never reboot directly

Generalization of "Cluster changes are serialized." A TF apply that triggers a VM reboot on a k8s or Ceph node disrupts workloads — no different from `apt-get install -y kernel-upgrade && reboot`. Cordon/drain (k8s) or `noout` + osd-down handling (Ceph) must precede the reboot, and that flow is owned by Ansible, not Terraform.

**Implementation**: the `terraform/modules/managed-vm/` child module sets `reboot_after_update = false` on the VM resource. Any config change applied through TF is written to PVE but does not take effect until the VM next reboots — and that reboot is operator-triggered through Ansible's update playbook (Phase 4/5), which performs the drain.

For changes that genuinely cannot wait — a BIOS mode flip, a CPU topology change — the path is: drain via Ansible → run TF apply → reboot via Ansible → uncordon. Never apply-then-reboot in one step on a live cluster member.

`reboot_after_update = false` applies to *all* managed VMs, not just cluster members — there is no harm in deferring reboots on standalone VMs either, and a uniform default keeps the module simple. Override per-VM only if the operator deliberately wants TF to reboot on apply.

## Disk passthrough on managed VMs

Passthrough disks are **first-class Terraform resources**. The per-VM module accepts a `passthrough_disks` input — a list of `{ interface, path_in_datastore }` — and declares them as additional `disk` blocks alongside the managed disks. TF creates and attaches them in the same apply as the VM, using the `root@pam` provider auth. There is no staged TF-then-Ansible flow.

Backups are always `backup = false` on passthrough blocks: the stacks on top (Ceph BlueStore on the OSD volumes, ZFS on the NVMe) own redundancy, and a vzdump of a multi-TB raw passthrough is neither crash-consistent nor cheap.

The disk identity (the `/dev/disk/by-id/<serial>` path) lives in the VM's `terraform/prd/vms.tf` entry. When a physical disk is swapped, edit that path and run a targeted `terraform refresh` + `terraform apply` — see `docs/runbooks/vm-rebuild.md`.

## Production execution model (Jenkins-driven)

How Terraform and Ansible run in production once Phase 10 lands. The operator workstation is reserved for changes that mutate the Jenkins agent VM itself; everything else flows through CI.

- **Dedicated Jenkins agent VM** for Terraform and Ansible runs. Not shared with other build workloads.
- **All logic lives in a Docker image.** The CI job pulls and runs the container on every execution; the agent VM holds no tool versions, no clone, no credentials cache. VM stays fully stateless and disposable.
- **tfstate is a local file inside a dedicated Git repo.** The container clones the state repo at job start, runs `terraform`, then commits and pushes any changes before exit. No remote-state backend (S3, Terraform Cloud, etc.).
- **Concurrency control at the Jenkins level.** A job-level lock prevents two TF/Ansible runs from racing — this is what makes the file-based state safe. No `terraform force-unlock` workflow because there is no remote lock to hold.

Path split — what runs where:

- **Through CI (the default path)**: every routine change. Bootstrap of new hosts, role applies, disk resize, OS updates on cluster nodes, scheduled drift checks. The Jenkins agent SSHes into the target host like any other Ansible run.
- **From the operator workstation (the carve-out)**: only changes that mutate the Jenkins agent VM itself — first-time bootstrap of the agent, agent VM disk resize, agent VM replace/destroy, break-glass when CI is down. The orchestrator cannot orchestrate its own replacement.

Guards against accidental self-mutation:

- **Terraform `lifecycle { prevent_destroy = true }`** on the Jenkins agent VM and on each `srvvaultN` resource. Hard stop at apply on a destroy.
- **CI plan-stage check** that fails the pipeline if `terraform plan` proposes `replace` or `destroy` on any of these. Belt-and-braces with `prevent_destroy` — the lifecycle block stops apply, the plan check stops the run before it ever reaches apply.

Implications:
- The state repo is a sensitive artifact (host private keys, API tokens). Same protections as any other secret-bearing repo.
- Rebuilding the agent VM is a no-op operationally; everything reproducible from the image + the state repo + Jenkins job config — but only via the workstation path.
- Image build and tagging are part of the CI surface — pin versions in the image, not on the VM.

Deferred / revisit:

- **Operator runbook sweep.** `docs/runbooks/adoption.md`, `disk-resize.md`, `k8s-rebuild.md`, `k8s-upgrade.md`, `vm-rebuild.md`, and `scratch-vm.md` describe their procedures as `wrkdev` running TF/Ansible directly. After Phase 1 (iac-agent), the routine path goes through `iac` on srviac instead; `wrkdev` is reserved for srviac mutation + break-glass. Each runbook needs either a "for routine use, run via `iac` on srviac; this runbook documents the operator-workstation path" header, or a rewrite of the steps to use `iac -c '…'`. Mechanical sweep, non-urgent — both paths still work today.

## Backup

- **Cluster vzdump job** — Ansible-managed via the `proxmox_host` role from Phase 2. Daily snapshot-mode dump of every VM to the `local-backup` storage on `pve`, mail-on-failure to the operator, retain three. The job lives in `/etc/pve/jobs.cfg` (cluster-shared via pmxcfs); the role writes it from `pve` only and the cluster propagates.
- **Per-VM `backup` flag follows the node, not the VM**. A PVE host either has a backup datastore or it doesn't; today only `pve` does. Rule: every managed disk on a VM hosted on a backup-capable node is `backup=true`; everything else (VMs on `pve1`/`pve2`, plus all passthrough disks regardless of node) is `backup=false`. Passthrough disks (Ceph OSD volumes, ZFS-passthrough drives) are always `backup=false` because the stacks on top of them own redundancy and a vzdump of a multi-TB raw passthrough is neither crash-consistent nor cheap. Encoded as a per-node `pve_node_backup_datastore` attribute (Phase 3); read by the per-VM Terraform modules to set the `backup` flag on each disk.
- **Daily cloud sync across providers** — operator workflow, not Ansible. Untouched.
- **Git** — covers everything in this repo.
- **Offsite for production** is a later item.

Deferred / revisit:

- **Ansible-side assertion of the backup-flag policy.** Today the rule is enforced at Terraform time. A drift-detection step in `proxmox_host` could `qm config` each VM and flag any disk whose `backup=` does not match what its node attribute says. Worth folding into Phase 10's drift detection rather than building now — there is no second authoritative source today.
- **Wire the vzdump job's `node` to the same attribute.** `proxmox_host_backup_node` and `proxmox_host_backup_storage` are hardcoded in the role's defaults today. Both should be derived from `pve_node_backup_datastore` so adding a backup datastore to `pve1` (hypothetically) does not require a second edit. Mechanical change; not urgent.

## First-week plan

1. Repo skeleton committed — `ansible/`, `terraform/`, `docs/`, pre-commit with yamllint + ansible-lint, pinned tool versions.
2. SSH + passwordless-sudo sanity check from `wrkdev`.
3. Throwaway VM created via Terraform (exercise that path first).
4. `bootstrap` + `baseline` Ansible roles applied to the scratch VM.
5. Full inventory built out with all real hosts listed but none touched (only `--check` runs).
6. OpenBao stand-up deferred to week 2 — one new tool at a time.
