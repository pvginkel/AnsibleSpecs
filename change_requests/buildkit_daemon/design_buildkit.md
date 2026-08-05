# Design: Shared in-cluster BuildKit daemon (Triage #113)

> **⚠ PARTIALLY SUPERSEDED — read [`buildkit-and-mtls-authz.md`](buildkit-and-mtls-authz.md) first.**
>
> That later doc is authoritative where the two disagree. It announces only the
> privileged→rootless reversal, but it in fact overrides this document in four
> places. Do not author a slice from the sections below without applying these:
>
> | Topic | This doc says | Superseded by |
> |---|---|---|
> | Worker mode | Req. #1: privileged OCI worker; Decision 5 `[worker.oci]` privileged, cache at the root path | **Rootless** via `rootlesskit`, non-root `securityContext`, cache at `~/.local/share/buildkit` |
> | Connection authz | Decision 3A: NetworkPolicy on `buildkit-prd`, "strong preference", the cluster's first | **No NetworkPolicy.** mTLS is the only access control, deliberately — rootless removes the node-escape exposure the policy existed to contain |
> | Endpoint | ClusterIP + a CoreDNS bare-name pin (an Ansible change) | **LoadBalancer + `buildkit.home`** via the `dns.webathome.org/hostname` annotation, mirroring step-ca. The CoreDNS pin is dropped |
> | Trust anchor | — | One homelab CA; no per-service CA. **The dedicated buildkit-scoped *provisioner* (Decision 3B) survives** — it bounds issuance blast radius for the in-cluster JWK password and is not the "per-service CA hack" that was rejected |
>
> **Consequences not yet written into the body below:**
> - **The Ansible surface nearly vanishes.** Dropping the CoreDNS pin leaves only
>   node-prep for rootless userns plus the `decisions.md` correction; the endpoint
>   is a chart annotation. This may be a HelmCharts-led change, not an Ansible-led one.
> - **The Risks register is stale.** "Privileged container (HIGH)" is moot under
>   rootless. "Broad mTLS trust (MEDIUM)" is written as mitigated *by the
>   NetworkPolicy that no longer exists* — under rootless + open access the residual
>   risk is different in kind: any homelab participant can saturate the shared cache
>   dataset and the daemon's memory limit (DoS), but cannot reach the node.
> - **The resource numbers are stale.** Sizing below assumes srvk8s4 at "~9.3 Gi
>   allocatable". As of 2026-08-05 the node is 20 GB with ~1.0 Gi *requested* across
>   14 pods and ~7.7 Gi genuinely free, and `kube-reserved` has since been set to
>   2432Mi. Re-derive the memory limit against current allocatable.
>
> **Status: parked.** See the gating spike and the operator's current lean in the
> other doc's *Status* section.

Pre-slice design material. This precedes `/write-slice` — it scopes the
architecture and records the decisions so a slice (or slices) can be authored
from it. Cross-repo: HelmCharts (new chart + ESO + static-zfs-pv + step-ca
`ca.json`), Ansible (node-prep + a stale-doc correction), DockerImages
(`buildctl` client image), and two **out-of-tree** repos — JenkinsPipelineUtils
(the client helper) and the KubeCoder controller (env-pod injection + RBAC).

## Question

How should we deploy a shared BuildKit daemon on the prd k8s cluster, integrate
its gRPC/TCP mTLS endpoint with the homelab step-ca, and let two client classes
(Jenkins build pods + KubeCoder dev-env pods) build and push images through it?

## Current state

**Build pipeline today (Kaniko).** There is *no* Kaniko Helm chart. Kaniko is a
Jenkins Kubernetes-plugin pod template (`kaniko` / `jenkins-agent`) that lives in
`JENKINS_HOME` on the Jenkins PVC — **not version-controlled in any repo under
`/work`** — plus the `helmCharts.kaniko()` / `kaniko2()` helpers in the
out-of-tree **JenkinsPipelineUtils** shared library. Push semantics are plain
HTTP, insecure, no auth: `--insecure --insecure-registry=registry:5000
--skip-tls-verify` (verbatim in the `kaniko2` source reproduced at
`DockerImages/docs/version-poller-redesign.md:207-216`). Call sites:
`DockerImages/Jenkinsfile:11,88-106` and `Ansible/Jenkinsfile.iac-image:3,11-14`.
The helper also stamps `org.webathome.poller.*` OCI labels (tracking-tag,
rebuild-at, pipeline, params) that the version-poller depends on. The local-dev
path is a plain `docker build` + `docker push` (`DockerImages/scripts/build.sh:7`,
`push.sh:9-10`) — separate from the Jenkins flow and the likely first thing the
KubeCoder build story replaces.

**Registry.** Upstream `registry:2`, Service `registry` port `5000` (pinned
clusterIP `172.17.0.3`), DNS `registry.home`, namespace `registry-prd`, **plain
HTTP, no TLS, no auth** (`HelmCharts/charts/registry/templates/registry-service.yaml:3-23`,
`HelmCharts/configs/prd/registry/prd/values.yaml:1-6`).

**DNS / reachability.** Bare-name `registry:5000` resolves cross-namespace *only*
because of a CoreDNS hosts pin in the Ansible microk8s role
(`Ansible/ansible/inventories/prd/group_vars/k8s_prd.yml:105-116`, rendered by
`Ansible/ansible/roles/microk8s/templates/coredns-corefile.j2:6-13`). A new
`buildkit` Service gets **no** bare-name resolution for free. There are **no
NetworkPolicies anywhere** in the charts, so cross-namespace ClusterIP traffic is
currently unrestricted (microk8s ships Calico, which *does* enforce policy once
one exists).

**Jenkins.** Runs in-cluster in `jenkins-prd`; controller SA `jenkins-admin`,
homelab root CA injected into the controller JVM cacerts via an init-container
(`HelmCharts/charts/jenkins/templates/jenkins-deployment.yaml:22-54`). **Build
pods run in `jenkins-prd` under that namespace's `default` SA**
(`HelmCharts/charts/jenkins/templates/jenkins-agent-jobs-rolebinding.yaml:5-10`),
with only Job/pod-introspection verbs — nothing cross-namespace.

**KubeCoder.** The KubeCoder repo is **not** on this machine; the chart references
`KubeCoderSpecs/...` which is absent. The dev-env pod shape is owned by an
**out-of-tree controller** (`registry:5000/kubecoder-controller`). The chart
(`HelmCharts/charts/kubecoder/`) deploys only the long-lived controller + bot
Deployments + RBAC + ESO; env pods are created imperatively by the controller at
runtime (no Job/PodTemplate in the chart). `KUBECODER_ENVIRONMENT_ID` appears
nowhere in HelmCharts — it is injected controller-side. Env pods run in
`kubecoder-prd`; their SA is minted per-env by the controller and scoped to
`create pods/exec` **on their own pod only** (chart comment D077,
`controller-role.yaml`). Secrets reach env pods by the controller projecting
leaves of the `kubecoder-secret-catalog` Secret (chart `values.yaml` `controllerConfig.secretCatalog`,
`controller-deployment.yaml:36-37`). Env-pod placement to srvk8s4 is stamped from
`controllerConfig.placement` (`HelmCharts/charts/kubecoder/values.yaml:196-203`);
the controller itself is pinned by mounting the zpool5 static PVC.

**step-ca.** Smallstep step-ca in `step-ca-prd`, endpoint `https://ca.home:443`
(→ `10.2.1.15`), values-only against the upstream chart. Three provisioners in
`ca.json` (base64 in `HelmCharts/configs/prd/step-ca/prd/manifests.yaml`):
`admin` (JWK, bootstrap), `acme` (ACME, **no X.509 name policy** — signs anything
that passes a challenge; this is what every in-cluster HTTP service uses), and
`ansible-jwk` (JWK, with a **fully-enumerated DNS allowlist** covering pve / ceph
/ kubernetes-api SANs — **no buildkit SAN, no wildcard**). Global validity:
`maxTLSCertDuration` = `1128h` (47 days). Five step-ca Secrets are committed as
base64 in that manifests file (a documented stopgap).

**internal_tls (the VM cert pattern).** `Ansible/ansible/roles/internal_tls/`.
Split issuance: the controller mints a JWK token with the fleet provisioner
password held in a `/dev/shm` tempfile (`tasks/issue.yml:85-122`, `delegate_to:
localhost`, `become: false`), then the target runs `step ca certificate <cn> <crt>
<key> --token <tok> --ca-url https://ca.home --force` so the keypair never leaves
the host (`tasks/issue.yml:137-152`). The split exists *solely* to keep the
fleet-wide provisioner password (`internal_tls_jwk_provisioner_password`, vaulted
in `Ansible/ansible/inventories/prd/group_vars/all/vips.yml`) off consumers.
"Renewal" is not `step ca renew`: it is detect-and-re-mint —
`step certificate needs-renewal --expires-in <N>h` (rc 0/1) gating a fresh mint,
plus a SAN-drift check (`tasks/issue.yml:21-73`). Default threshold 14 days. The
homelab root is distributed to hosts by `baseline`
(`Ansible/ansible/roles/baseline/tasks/main.yml:292-373`,
`Ansible/ansible/roles/baseline/files/homelab-root.crt`).

**Closest non-HTTP precedent.** microk8s serves its homelab leaf *additively* via
`--tls-sni-cert-key` (`Ansible/ansible/roles/microk8s/tasks/internal_tls.yml:25-37`),
issued through the **JWK** path — precisely because an apiserver is not an HTTP
service that can answer ACME HTTP-01. buildkitd (gRPC mTLS) is the same shape.

**Storage.** The `static-zfs-pv` Terraform module
(`HelmCharts/terraform-modules/static-zfs-pv/main.tf`) creates a
`homelab_zfs_dataset` with a `quota` (the real bound) + a pre-bound `local`
PV whose `node_affinity` pins it to the pool's node via `kubernetes.io/hostname`.
zpool5 → srvk8s4 (`HelmCharts/_providers/clusters.yaml:33-37`). **There is no
`node-affinity.require-storage-zpool5` helper** — only `require-storage-zpool2`
and `require-performance-high` exist (`HelmCharts/charts/shared/_helpers.tpl:5-27`).
Placement to srvk8s4 is achieved by *mounting the zpool5 PVC* (the local-PV
hostname affinity does the pinning), exactly as KubeCoder does. srvk8s4 carries a
`homelab.local/performance=high:NoSchedule` taint and is ballooned to roughly
~9.3 Gi allocatable; KubeCoder caps it at 5 concurrent env pods and zeroes memory
requests via a LimitRange so scheduling is count-gated.

**ESO.** Charts pull from OpenBao via `External Secrets`. ClusterSecretStore
`openbao-prd`, server `https://secrets.home`, KV mount `kv`
(`HelmCharts/configs/prd/external-secrets/prd/clustersecretstore.yaml`); charts
declare leaves under `externalSecrets.secrets` with path convention
`eso/prd/<chart>/<stage>/<leaf>` and emit one `ExternalSecret` each via the
one-line `{{- include "shared.externalsecrets" . -}}` helper
(`HelmCharts/charts/shared/_helpers.tpl:198-221`; example
`HelmCharts/configs/prd/kubecoder/prd/values.yaml:17-40`). `refreshInterval`
defaults to 1h.

## Requirements (from operator) — fixed

These are design targets, not options. Each is feasible; risks are under **Risks**.

1. **One daemon, privileged mode.** Rootless evaluated and rejected. *No precedent
   for an in-cluster privileged workload exists in these charts* — privileged
   pods are new here. Feasible; blast radius flagged under Risks.
2. **Runs on srvk8s4, cache PVC on zpool5 via `static-zfs-pv`.** Quota **starts at
   60 Gi**, grows later; the cache deliberately includes pulled base images (a
   wanted local image cache). GC `keepstorage` must sit **safely below** the ZFS
   quota. Precedent: KubeCoder's 80 Gi zpool5 share
   (`HelmCharts/configs/prd/kubecoder/_shared/infrastructure.tf:14-25`). Feasible.
3. **Additive, not a replacement.** BuildKit is a **new** entrypoint in the
   `JenkinsPipelineUtils` shared library, alongside `kaniko()`/`kaniko2()`. Kaniko
   stays. Feasible (the helper repo is out-of-tree — see Risks/Open questions).
4. **Pushes to `registry:5000`** — plain HTTP, insecure, no auth.
   `buildkitd.toml` needs `http = true` for that registry. Mirrors Kaniko's
   `--insecure-registry=registry:5000`. Feasible.
5. **Concurrency bounded by a Jenkins-side semaphore** (lockable resources /
   throttle), **not** a daemon-level cap. Jenkins is the heaviest but not the only
   user. Feasible; the KubeCoder-side concurrency gap is flagged under Risks.
6. **Primary driver is KubeCoder**, not Jenkins: build an image from inside a
   KubeCoder dev-env pod and run it via a Kubernetes Job. Detection via
   `KUBECODER_ENVIRONMENT_ID`; clients need the daemon endpoint + client creds
   injected. Feasible for the *build* path; the *"run via a Job"* capability is an
   **out-of-tree KubeCoder controller dependency** (see Risks) — the buildkit
   daemon itself is indifferent to how a client uses the image it builds.

## Constraints (from codebase / doctrine)

- **Operator runs all applies.** Claude prepares; the operator runs every
  `terraform apply` / `helm`-deploy / `ansible-playbook` and reports back
  (CLAUDE.md). This design names the changes, not the keystrokes.
- **Hostnames, not IPs; `.home` search domain.** The buildkit endpoint is a
  hostname (`buildkit.home` / bare `buildkit`), not an IP (CLAUDE.md Conventions).
- **Secrets via OpenBao → ESO for in-cluster workloads**, path
  `eso/prd/<chart>/<stage>/<leaf>`, store `openbao-prd`
  (`clustersecretstore.yaml`). step-ca's *own* bootstrap secrets stay out of
  OpenBao (chicken-and-egg, `decisions.md:143`) — but a *consumer's* provisioner
  credential is not bootstrap-tier and may live in OpenBao→ESO.
- **Homelab CA, JWK provisioner pattern.** New homelab certs come from step-ca via
  the JWK provisioner (VMs) or the ACME provisioner (in-cluster HTTP). A new SAN
  must be allowed by the issuing provisioner's name policy *before* first issuance
  or step-ca returns "not authorized" (`docs/runbooks/step-ca-bootstrap.md`).
- **cert-manager is NOT deployed.** `decisions.md:139` and `:152` are **stale** —
  they describe a planned cert-manager + ClusterIssuer path that was rejected. The
  as-built in-cluster path is certbot + nginx-configurator HTTP-01 against the
  `acme` provisioner (`AnsibleSpecs/slices/completed/internal-tls-step-ca.md:48-49,114-116`;
  no `ClusterIssuer`/`cert-manager.io` anywhere in HelmCharts). **This design must
  not assume cert-manager**, and the stale lines should be corrected via
  `/update-docs` (noted in Open questions).
- **`registry:5000` is plain HTTP** and reachable in-cluster via the CoreDNS pin —
  fixed; buildkitd pushes to it as-is.
- **Bare-name service resolution requires an explicit CoreDNS pin** (Ansible),
  or callers use the FQDN. Not free.
- **Commit cadence / no dormant config.** Don't ship config that isn't exercised
  (MEMORY: no-unexercised-config). Every piece below is wired to a live consumer
  or omitted.

## Risks

- **Privileged container on srvk8s4 (HIGH).** A privileged buildkitd can escape to
  the node; it is the first in-cluster privileged workload. *Operator-chosen over
  rootless — not relitigated.* Mitigation: confine to the dedicated node (already
  the case via the PVC pin), default-deny-style NetworkPolicy on its namespace
  (Decision 3), no extra capabilities beyond what the OCI worker needs, and treat
  the daemon as a trust boundary — anyone who can submit a build to it runs
  privileged code on srvk8s4. Document this in the chart README and decisions.md.
- **OOM / memory contention on srvk8s4 (HIGH).** The node is ballooned to ~9.3 Gi
  allocatable and already runs up to 5 KubeCoder env pods + Playwright/bursty
  work. A large build (or several concurrent ones) can balloon RSS and OOM
  neighbours. Mitigation: a hard memory **limit** on the buildkit pod (Decision 5)
  as the backstop, plus the Jenkins semaphore (req. 5). Precedent for count-gating
  this node: KubeCoder's LimitRange + `maxEnvironments: 5`.
- **Unbounded KubeCoder-initiated concurrency (MEDIUM).** The Jenkins semaphore
  (req. 5) only governs Jenkins. KubeCoder env pods can dial the daemon
  concurrently with Jenkins and with each other, with no shared cap — so the
  daemon can see more parallel work than the semaphore implies. *No daemon cap is
  an operator decision — not relitigated.* Mitigation: the memory limit is the
  real backstop; optionally a KubeCoder-side throttle later. Flagged so the
  operator sizes the limit with KubeCoder concurrency in mind.
- **GC vs ZFS quota (MEDIUM).** If `keepstorage` ≥ quota, GC never trims before
  the dataset hits the quota and writes hard-stop mid-build (corrupt/failed
  builds, not data loss — the dataset has `Retain` + `prevent_destroy`).
  Mitigation: `keepstorage` set well below quota with headroom for in-flight
  layers between GC sweeps (Decision 5). Because the base-image cache lives in the
  same dataset, `keepstorage` governs total cache footprint — size it, then set
  quota above it.
- **Broad mTLS trust (MEDIUM).** buildkitd's mTLS verifies only that the client
  cert chains to `--tlscacert`. With the homelab root as the CA, **any** homelab
  cert (every VM, every ACME-issued in-cluster cert) can open a session — the
  daemon has no SAN/OU/identity authz. A privileged builder reachable by the whole
  fleet is a real exposure. Mitigation: NetworkPolicy is the actual connection
  gate (Decision 3); the dedicated provisioner bounds *issuance* blast radius but
  not connections.
- **Insecure registry exposure (LOW, pre-existing).** `registry:5000` plain HTTP
  is the established posture (Kaniko already pushes this way). BuildKit inherits
  it; no new exposure. Noted for completeness.
- **Out-of-tree coupling (MEDIUM, delivery risk).** Three load-bearing pieces live
  outside `/work`: the `buildkit()` helper (JenkinsPipelineUtils), the Jenkins
  `buildkit` pod template (JENKINS_HOME on the PVC, unversioned), and the KubeCoder
  controller's env-pod injection + Job RBAC. The HelmCharts/Ansible slice can land
  a working daemon, but end-to-end client use depends on changes the
  Ansible-led slice cannot make in-tree. Sequence accordingly (Impact summary).

## Decisions

### 1. How buildkitd obtains and renews its gRPC mTLS **server** cert

buildkitd terminates mTLS itself (`[grpc.tls]` cert/key/ca). It needs a homelab
leaf with the SANs clients dial (`buildkit.home`, bare `buildkit`), renewed before
the 47-day expiry. This is the **first in-cluster non-HTTP TLS consumer** — the
certbot/nginx-configurator HTTP-01 path does not fit (see Option B).

**Option A — in-pod `step-cli` sidecar, JWK provisioner (recommended).**
A `smallstep/step-cli`-based init container mints the leaf at pod start and a
sidecar (or the same container in a loop / `step ca renew --daemon`) re-mints on
the repo's detect-and-re-mint cadence, writing cert+key to an `emptyDir` shared
with buildkitd. It mirrors `internal_tls` commands almost verbatim
(`step ca token … --provisioner <p> --provisioner-password-file <f> --ca-url
https://ca.home --root <homelab-root> --san=buildkit.home --san=buildkit`, then
`step ca certificate buildkit.home <crt> <key> --token <tok> --force`), and mirrors
the microk8s "serve a homelab leaf on a non-HTTP daemon via JWK" precedent.
- *Trade-off:* unlike the VM split, the provisioner credential must be present
  pod-side (ESO Secret). Acceptable **only** when paired with a dedicated,
  buildkit-scoped provisioner (Decision 3) so the in-cluster credential cannot
  mint pve/ceph/kubernetes-api certs.
- *Impact:* new `buildkit` chart (sidecar + emptyDir + ESO Secret mount); the
  provisioner's name policy must allow the buildkit SAN before first mint
  (`ca.json` edit, Decision 3); no HTTP-01 responder, no nginx fronting.

**Option B — ACME with a standalone HTTP-01 responder.**
Run a step-cli/lego/certbot ACME client in standalone mode against step-ca's
`acme` provisioner (credential-free), serving the HTTP-01 challenge on :80 in the
pod, writing the cert to a shared volume buildkitd reads.
- *Trade-off:* credential-free is genuinely attractive for blast radius and is the
  dominant in-cluster pattern. **But** buildkitd is gRPC and cannot answer
  HTTP-01, so we must run a separate challenge responder reachable by step-ca; the
  existing certbot+nginx-configurator path **cannot be reused** because nginx
  would terminate TLS and defeat mTLS-at-the-daemon. The `acme` provisioner has no
  name policy, so it does not help authz either. Net: more moving parts (a new
  challenge-responder shape) for a server cert, with no authz benefit.
- *Impact:* a challenge-responder sidecar + :80 Service reachable by step-ca; no
  provisioner credential in-cluster.

**Recommendation: Option A (in-pod step-cli sidecar, JWK), paired with the
dedicated provisioner from Decision 3.** It mirrors the established `internal_tls`
flow and the microk8s non-HTTP precedent, needs no HTTP-01 gymnastics for a gRPC
service, and uses the repo's detect-and-re-mint renewal. The lone downside — a
provisioner credential in-cluster — is neutralised by scoping that provisioner to
buildkit SANs only. Strong preference.

### 2. Client certs + CA trust for the two consumer classes

Each client (`buildctl`) needs: a client cert+key to present, and the homelab root
to verify the server (`--tlscacert`). The root is already available in-cluster
(committed `HelmCharts/homelab-root.crt`; ConfigMap `homelab-root-ca` in
`external-secrets-prd`) and in pod images via `baseline`/image bakes — trust is a
solved problem; the cert is the open part. The two classes differ in lifecycle.

**Option A — per-pod / per-build mint.**
An init-container in each client pod mints a short-lived client cert at start
(JWK token or ACME), like a miniature `internal_tls`.
- *Trade-off:* no stored client key; certs are ephemeral. **But** it spreads the
  provisioner credential into *every* ephemeral Jenkins build pod and into
  KubeCoder env pods, and requires init-container edits to the out-of-tree Jenkins
  pod template and the out-of-tree KubeCoder controller. Widest credential spread,
  most out-of-tree surface.

**Option B — shared renewed client-cert Secret (recommended).**
A single client-cert issuer (a `step-cli` CronJob, or a second loop in the
buildkit pod's cert sidecar) mints a client cert with the **dedicated provisioner**
and publishes it as a Secret to each consumer namespace; consumers only *consume*
the Secret, never the provisioner credential.
- *Jenkins:* build pods mount the client-cert Secret in `jenkins-prd` + the
  homelab root, and `buildctl --addr tcp://buildkit.home:1234 --tlscacert <root>
  --tlscert … --tlskey … --tlsservername buildkit.home`. No provisioner credential
  in build pods.
- *KubeCoder:* the client cert is a **new `kubecoder-secret-catalog` leaf** the
  controller projects into env pods (the established catalog pattern,
  `values.yaml controllerConfig.secretCatalog`), alongside an env var carrying the
  endpoint. Injection is **controller-side** (out-of-tree) — the chart only
  supplies the catalog leaf + ESO.
- *Distribution sub-choice* (how the Secret reaches the two namespaces):
  - **B1 — central issuer + cross-namespace Secret write (preferred):** the
    issuer runs in `buildkit-prd`, holds the provisioner credential (one place),
    and writes the client-cert Secret into `jenkins-prd` and `kubecoder-prd` via a
    narrow Role/RoleBinding (`create/update` on one named Secret each). Confines
    the credential to one namespace; adds a small cross-namespace RBAC grant (new
    pattern, but tightly scoped).
  - **B2 — per-namespace renewer:** a `step-cli` CronJob in each consumer
    namespace mints locally from an ESO-synced provisioner credential. Simpler and
    fully namespace-local, but the (scoped) provisioner credential then lives in
    3 namespaces.
- *Trade-off vs A:* a long-lived client key exists at rest (in Secrets), but it
  only buys access to a daemon already gated by NetworkPolicy, and the scoped
  provisioner bounds what that key's issuer can mint. Far less out-of-tree churn
  (no Jenkins pod-template init-container; KubeCoder change is a catalog leaf, not
  a mint flow).

**Recommendation: Option B, distribution B1.** Confine the provisioner credential
to `buildkit-prd`, mint centrally, and push client-cert Secrets into the two
consumer namespaces; KubeCoder consumes via the catalog-projection it already
has. B2 is the acceptable fallback if cross-namespace writes are unwanted. CA
trust is the homelab root in all cases (already present). Moderate-to-strong
preference for B over A on credential-containment and out-of-tree-surface grounds.

### 3. mTLS client authz scope — who may actually reach the daemon

buildkitd enforces only that the client cert **chains to `--tlscacert`**. There is
no built-in SAN/OU/identity authz. With the homelab root as `--tlscacert`, every
homelab cert in the fleet can open a session against a *privileged* builder — too
broad. step-ca is a single two-tier CA (one intermediate under one root); all
provisioners issue under the same chain, so a dedicated provisioner does **not**
produce a distinct CA that `--tlscacert` could pin to. Three levers:

**Option A — NetworkPolicy (the real connection gate; recommended, primary).**
A NetworkPolicy on `buildkit-prd` admitting ingress to the daemon port only from
`jenkins-prd` and `kubecoder-prd` (namespace/pod selectors). This is the only
mechanism that actually restricts *who connects*.
- *Trade-off:* it would be the **first NetworkPolicy in the cluster** — a new
  pattern; must confirm Calico enforcement is on (microk8s default) before relying
  on it, and remember that adding the first policy to a namespace flips it to
  default-deny for unmatched ingress, so the policy must also admit the cert
  sidecar's path to `ca.home` and the daemon's egress to `registry:5000`.
- *Impact:* a `NetworkPolicy` template in the buildkit chart; a deliberate
  doctrine addition (note in decisions.md).

**Option B — dedicated, buildkit-scoped step-ca provisioner (recommended,
complementary — bounds issuance, not connections).**
Add a new provisioner to `ca.json` whose name policy allows only the buildkit
server + client SANs. This does **not** stop a foreign homelab cert from
connecting (same root), but it means the *credential that lives in-cluster*
(Decisions 1/2) can only mint buildkit certs — never pve/ceph/kubernetes-api. This
is the blast-radius mitigation for putting an issuance credential in the cluster.
- *Impact:* a base64 `ca.json` edit in
  `HelmCharts/configs/prd/step-ca/prd/manifests.yaml` + step-ca redeploy; a new
  provisioner password generated and stored in OpenBao (Decision 4). Cheaper than
  reusing `ansible-jwk` *and* far safer (reusing `ansible-jwk` would put a password
  that mints pve/ceph/k8s-api certs into the cluster — rejected).

**Option C — SAN/OU enforcement (not viable in buildkitd).**
buildkitd cannot filter on client SAN/OU. A fronting proxy that does would break
the simple model and re-introduce a TLS-terminating hop. Rejected.

**Recommendation: A + B together.** NetworkPolicy is the connection authz
(Option A); the dedicated scoped provisioner is the issuance blast-radius control
(Option B). Be explicit in the slice that these solve *different* problems — the
provisioner does not gate connections, the NetworkPolicy does. Do **not** reuse
`ansible-jwk`. Strong preference.

### 4. Where the provisioner credential lives in-cluster

The dedicated provisioner is a JWK provisioner, so its password unlocks signing.
That password is a *consumer* credential, not step-ca bootstrap material, so it
belongs in OpenBao→ESO (not the ansible-vault bootstrap tier).

- **Recommended:** generate the password at provisioner-creation time, store it in
  OpenBao at `eso/prd/buildkit/prd/<leaf>` (e.g. `provisioner-password`), and pull
  it via an `ExternalSecret` declared with the one-line `shared.externalsecrets`
  helper + `externalSecrets.secrets` values, store `openbao-prd`, KV mount `kv` —
  mirroring `HelmCharts/configs/prd/kubecoder/prd/values.yaml:17-40`. The cert
  sidecar mounts the resulting Secret and feeds it to `--provisioner-password-file`.
- This is a straightforward decision (established pattern); the only nuance is that
  the *same* password value must also be embedded (as the encrypted-key/JWK pair)
  in `ca.json` when the provisioner is added — i.e. step-ca and OpenBao hold two
  ends of the same provisioner, and a rotation touches both in one window.

### 5. Workload shape — Deployment vs StatefulSet, `buildkitd.toml`, resources

**Deployment vs StatefulSet.** The PV is a *static, pre-bound* local volume
(`static-zfs-pv`), so there are no `volumeClaimTemplates` and no need for
StatefulSet identity. Mirror the KubeCoder controller: a **Deployment, `replicas:
1`, `strategy: Recreate`** (RWO PVC on one node can't be double-mounted during a
RollingUpdate), mounting the zpool5 PVC (which pins it to srvk8s4) and tolerating
the perf taint (`homelab.local/performance=high:NoSchedule`, or `operator: Exists`
as the KubeCoder controller does). No `require-storage-zpool5` helper exists — the
PVC mount is the pin; add the perf toleration explicitly.
- *Recommendation:* Deployment + Recreate. StatefulSet adds nothing here.

**Storage.** `module "zfs"` in `HelmCharts/configs/prd/buildkit/_shared/infrastructure.tf`
using `static-zfs-pv` with `pool="zpool5"`, `node_hostname = var.zfs_pools["zpool5"]`,
`dataset="buildkit"`, `quota="60G"`, `size="60Gi"`, `namespace =
module.namespace.name` — mirroring KubeCoder's invocation
(`HelmCharts/configs/prd/kubecoder/_shared/infrastructure.tf:14-25`). Chart-side
PVC sets `storageClassName: ""` + `volumeName: <name>-pv` to complete the static
bind. The dataset is `Retain` + `prevent_destroy`.

**`buildkitd.toml` shape** (responsibilities, not literal config):
- `[grpc]` listen on `tcp://0.0.0.0:1234` (gRPC); `[grpc.tls]` cert/key/ca pointing
  at the sidecar-written paths (`--tlscacert` = homelab root → enables mTLS).
- `[registry."registry:5000"]` `http = true` (plain-HTTP insecure registry,
  matching Kaniko's `--insecure-registry=registry:5000`). The daemon does the push
  (`buildctl … --output type=image,name=registry:5000/<img>:<tag>,push=true`), so
  registry reachability + `http=true` live on the daemon, not the client.
- `[worker.oci]` enabled (privileged OCI worker), `gc = true`, with a
  `[[worker.oci.gcpolicy]]` whose **`keepBytes` (`keepstorage`) sits well below the
  60 Gi quota** — start ~45 Gi (≈75% of quota), leaving ~15 Gi headroom for
  in-flight layers between sweeps. Because the wanted base-image cache shares the
  dataset, `keepstorage` governs total cache footprint; when the quota grows
  later, raise `keepstorage` in proportion and keep the headroom.
- *Don't* set a daemon concurrency cap (req. 5 — concurrency is Jenkins-side).

**Resources.** Given srvk8s4 (~9.3 Gi allocatable, ballooned, shared with ≤5
KubeCoder env pods + Playwright), set a **hard memory limit** as the OOM backstop
(start conservative, e.g. 4 Gi, and tune from observed build RSS) and a CPU limit;
keep the memory *request* small to fit the node's count-gated scheduling posture
(KubeCoder zeroes requests via a LimitRange — confirm whether the buildkit
namespace inherits any LimitRange or needs its own). The Jenkins semaphore bounds
Jenkins-side parallelism; the memory limit is the backstop for everything else
(including KubeCoder, which the semaphore does not cover — see Risks).
- *Recommendation:* Deployment + Recreate, single replica, PVC-pinned to srvk8s4,
  perf toleration, hard memory + CPU limits, `keepstorage` ≈ 45 Gi for a 60 Gi
  quota. Resource numbers are starting points the operator tunes (and the chart
  exposes via `recommend-resources`, as KubeCoder does).

## Recommended architecture

**Components and where each lives:**

| Component | Repo / location | Notes |
|---|---|---|
| `buildkit` Helm chart (Deployment, Service, PVC, cert sidecar, ESO, NetworkPolicy) | **HelmCharts** `charts/buildkit/` + `configs/prd/buildkit/prd/` | privileged buildkitd + step-cli sidecar; single replica |
| zpool5 cache dataset + static PV | **HelmCharts** `configs/prd/buildkit/_shared/infrastructure.tf` | `static-zfs-pv`, 60 Gi quota, pinned srvk8s4 |
| Dedicated buildkit step-ca provisioner | **HelmCharts** `configs/prd/step-ca/prd/manifests.yaml` (`ca.json` base64) | name policy = buildkit SANs only |
| Provisioner password (OpenBao→ESO) | **OpenBao** `eso/prd/buildkit/prd/*` + chart `externalSecrets` | mirrors kubecoder ESO |
| Client-cert Secret distribution | **HelmCharts** buildkit chart (issuer + cross-ns RBAC) | Decision 2/B1 |
| CoreDNS pin for `buildkit`/`buildkit.home` | **Ansible** `inventories/prd/group_vars/k8s_prd.yml` (`microk8s_coredns_hosts`) | if bare-name addressing chosen; mirrors `registry` |
| `buildctl` client image | **DockerImages** new image (or bake into agent images) | client cert mount + homelab root trust |
| `buildkit()` pipeline helper | **JenkinsPipelineUtils (out-of-tree)** | new entrypoint; emit `org.webathome.poller.*` labels |
| Jenkins `buildkit` pod template | **JENKINS_HOME PVC (unversioned)** | `buildctl` container + client-cert Secret mount |
| KubeCoder env-pod endpoint+cert injection (+ Job RBAC) | **KubeCoder controller (out-of-tree)** | new catalog leaf + env var; Job-creation RBAC if needed |
| Doctrine correction (cert-manager stale lines) | **AnsibleSpecs** `decisions.md:139,152` via `/update-docs` | + record privileged-pod + first-NetworkPolicy decisions |

**Endpoint:** ClusterIP Service `buildkit` port `1234`; address it as
`buildkit.home` (server-cert SAN) via a CoreDNS pin mirroring `registry`
(`k8s_prd.yml`), or by FQDN `buildkit.buildkit-prd.svc.cluster.local` if the pin
is unwanted. The pinned-name route keeps client config shaped like the existing
`registry:5000` references.

**Cert / trust flow (sequence):**

1. **Provision (one-time):** add the dedicated provisioner to `ca.json` (name
   policy = `buildkit.home`, `buildkit`, + the client SAN/OU); store its password
   in OpenBao `eso/prd/buildkit/prd/provisioner-password`; redeploy step-ca.
2. **Server cert (pod start + renewal):** ESO syncs the provisioner password into
   `buildkit-prd`; the step-cli init container mints `buildkit.home` via the
   dedicated provisioner against `https://ca.home` (anchored to the committed
   homelab root); writes cert+key to an emptyDir; buildkitd starts with
   `[grpc.tls]` over those + `--tlscacert` = homelab root. The sidecar re-mints on
   the 14-day detect-and-re-mint cadence (or `step ca renew --daemon`).
3. **Client cert (issued + distributed):** the same issuer mints a client cert via
   the dedicated provisioner and writes it as a Secret into `jenkins-prd` and
   `kubecoder-prd` (Decision 2/B1).
4. **Jenkins build:** a `buildkit` pod template mounts the client-cert Secret +
   homelab root; the `buildkit()` helper runs `buildctl --addr tcp://buildkit.home:1234`
   with mTLS flags, builds with `org.webathome.poller.*` labels, outputs
   `push=true` to `registry:5000`. Jenkins-side semaphore bounds concurrency.
5. **KubeCoder build:** the controller projects the client-cert catalog leaf +
   `buildkit.home` endpoint env var into the env pod (gated on
   `KUBECODER_ENVIRONMENT_ID`); the env pod runs `buildctl` over mTLS, pushes to
   `registry:5000`, then (separately, via controller-granted RBAC) runs the image
   as a Job.
6. **Connection authz:** the `buildkit-prd` NetworkPolicy admits the daemon port
   only from `jenkins-prd` + `kubecoder-prd`; buildkitd verifies each client cert
   chains to the homelab root.

## Impact summary

- **HelmCharts (largest in-tree surface):** one new chart (`charts/buildkit/` +
  `configs/prd/buildkit/{_shared,prd}/`) — Deployment + Service + static-zfs-pv +
  PVC + step-cli cert sidecar + ESO + the cluster's first NetworkPolicy + the
  client-cert issuer & cross-namespace RBAC; plus a base64 `ca.json` edit in the
  step-ca config to add the dedicated provisioner. Net new namespace `buildkit-prd`.
- **Ansible:** a CoreDNS hosts pin for `buildkit`/`buildkit.home`
  (`k8s_prd.yml`) if bare-name addressing is chosen (one-line change, mirrors
  `registry`); plus the `decisions.md` cert-manager correction and a decisions
  entry recording the privileged-pod + first-NetworkPolicy posture.
- **DockerImages:** a `buildctl` client image (or bake `buildctl` into existing
  agent images); possibly augment `scripts/build.sh` for the local/KubeCoder path.
- **OpenBao:** one new leaf (`eso/prd/buildkit/prd/provisioner-password`),
  operator-written.
- **Out-of-tree (gated, sequence-after):** JenkinsPipelineUtils `buildkit()`
  helper; the Jenkins `buildkit` pod template on the PVC; the KubeCoder
  controller's env-pod endpoint+cert injection and (if pursued) Job-creation RBAC.
- **Hosts/infra affected:** srvk8s4 only (the daemon + its dataset); the daemon is
  reachable from `jenkins-prd` and `kubecoder-prd`. Applying it adds a privileged
  workload to srvk8s4 and the cluster's first NetworkPolicy — both new postures.
  Nothing existing is removed (Kaniko untouched), so rollback is "don't deploy /
  delete the chart"; the dataset is `Retain`.
- **Sizing:** roughly two slices — an **Ansible-led HelmCharts+Ansible slice**
  standing up the daemon + cert flow + endpoint + NetworkPolicy (verifiable by a
  `buildctl` smoke build from a throwaway pod with a client cert), and a
  **client-enablement slice** spanning the out-of-tree helper / pod template /
  KubeCoder controller. They can be split because the daemon is independently
  testable before any client helper exists.

## Open questions for the operator

1. **Endpoint addressing:** CoreDNS-pinned bare name `buildkit.home` (Ansible
   change, mirrors `registry`) vs in-cluster FQDN (no infra change)? Affects the
   server-cert SAN and client config. *Lean: pinned name, for consistency with
   `registry:5000`.*
2. **Client-cert distribution (Decision 2):** central issuer + cross-namespace
   Secret write (B1, credential in one namespace) vs per-namespace renewer (B2,
   scoped credential in 3 namespaces)? *Lean: B1.*
3. **KubeCoder "run via a Job":** the in-tree evidence shows env-pod SAs scoped to
   `pods/exec` on their own pod — creating a Job needs a **controller-side RBAC
   grant** (out-of-tree). Confirm this is in scope for the KubeCoder controller
   work, since the daemon design assumes the client decides what to do with the
   built image. *This is a dependency, not a blocker for the daemon slice.*
4. **NetworkPolicy as a new doctrine:** OK to introduce the cluster's first
   NetworkPolicy here (and confirm Calico enforcement is on)? Adding one flips the
   namespace to default-deny for unmatched ingress — the policy must also permit
   the cert sidecar → `ca.home` and daemon → `registry:5000` paths.
5. **Memory limit starting point:** confirm a conservative hard limit (≈4 Gi?) on
   the privileged builder given srvk8s4's ~9.3 Gi allocatable shared with ≤5
   KubeCoder env pods + Playwright; and whether `buildkit-prd` should carry its own
   LimitRange.
6. **Doc correction:** approve a `/update-docs` pass to fix `decisions.md:139,152`
   (cert-manager was rejected; in-cluster TLS is certbot + nginx-configurator) so
   this design isn't read against a stale doctrine.
