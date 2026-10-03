# Slice 040 — Prometheus alerts for the 2026-09-25 DHCP-outage failure modes, an out-of-cluster dead-man's switch through healthchecks.io, and a read-only Elasticsearch user for `filebeat-*` stored in OpenBao

## Requirements / rulings

- R1. **ANS-127 — alerting for the 2026-09-25 failure modes.** The card's missing signals, verbatim:
  - "A LoadBalancer Service with no ready endpoints, or no MetalLB `ServiceL2Status` (the DHCP
    failure itself)."
  - "Whether DHCP answers at all: a DISCOVER from outside the pod network. A relay-style probe
    from a node got an OFFER on 2026-09-25, so the probe shape works."
  - "OIDC discovery at auth.ginbov.nl failing."
  - "CrashLoopBackOff or ImagePullBackOff, a node NotReady, an Argo app not Healthy. Slice 028
    (ANS-118) covers Argo's sync-failed and degraded alerts; check the overlap."
- R2. **ANS-127 — a dead-man's switch outside the cluster.** "Whole-cluster loss. Prometheus and
  Alertmanager run in the cluster, so a failed cold boot makes no noise. An out-of-cluster
  heartbeat closes that: ANS-15's healthchecks.io leg, or a probe from srviac once srviac has a
  static address."
- R3. **ANS-185 — a read-only Elasticsearch user for `filebeat-*`, stored in OpenBao.** "create a
  read-only Elasticsearch user that can only read the `filebeat-*` indices, and store its
  credential in OpenBao, so a KubeCoder card can expose it to every environment (as
  ELASTIC_URL/ELASTIC_USER/ELASTIC_PASSWORD, next to the Jenkins variables). Then the Kibana route
  ANS-164 put in docs/runbooks/argocd.md for a replaced hook's log can be checked, and it becomes
  a real answer." Operator's ruling on the card: "yes".
- Ruling (triage, 2026-10-02): exposing the credential to every environment is the KubeCoder
  card's (KC-124), not this slice's.
- Ruling D1 (2026-10-03, "agree"): **the dead-man's switch is healthchecks.io.** Prometheus carries
  an always-firing heartbeat alert; Alertmanager sends it to a healthchecks.io check through a
  webhook receiver, repeating every few minutes; when pings stop, healthchecks.io notifies the
  operator. No srviac heartbeat probe. The ping URL is a secret: it lives in OpenBao and reaches
  Alertmanager the way the Telegram credentials already do (ESO-materialised Secret
  `alertmanager-telegram` in `prometheus-prd`, from OpenBao).
- Ruling F1 (2026-10-03): "I just created an account. Telegram is fine." The operator has a
  healthchecks.io account; its notification goes to Telegram through healthchecks.io's own
  Telegram integration (@HealthchecksBot), configured in healthchecks.io by the operator. The plan
  gives the operator one step: create the check with the period/grace that match the heartbeat's
  repeat interval, and `bao kv put` the ping URL at the path the plan names.
- Ruling D2 (2026-10-03, "agree"): **CrashLoopBackOff/ImagePullBackOff alerts cover every
  namespace on the production cluster, severity warning, after the condition holds 15 minutes,
  one alert per pod.** Node NotReady and a LoadBalancer Service with no ready endpoints / not
  announced by MetalLB are critical, unscoped.
- Settled (refinement, operator saw it): the **DHCP probe runs on srviac** (outside the cluster,
  static address 10.1.0.45, does not depend on the DHCP it tests) as a systemd timer writing its
  result to srviac's node-exporter (textfile collector), which in-cluster Prometheus already
  scrapes; an alert fires on probe failure and on the result going stale. The operator runs the
  srviac Ansible playbook.
- Settled: **OIDC discovery is probed by a blackbox exporter added to the Prometheus deploy**, on
  `https://auth.ginbov.nl/realms/homelab/.well-known/openid-configuration` (the URL that failed
  in the outage and the one `docs/runbooks/cold-boot.md` checks).
- Settled: **the read-only user is created by the Elasticsearch setup Job** (DockerImages
  `elasticsearch-setup`), with a role granting read on `filebeat-*` only; the operator generates
  its password and writes it to OpenBao with one `bao kv put` at a path both the setup Job (via
  ESO) and the later KubeCoder card can read; the Job takes it from there. Not created by hand in
  Kibana.
- Settled: **no new Argo rule** — slice 028's rules and Argo's own notifications cover sync-failed
  and degraded; the pod-level rules catch the outage's Keycloak image-pull and DHCP crash loop.
- Settled: **the Kibana check uses a current Argo CD hook pod's log**, not the one the runbook
  names (`tf-presync-fieldnotes-prd-sx956`, harvested 2026-10-01, which leaves the 7-day index
  around 2026-10-08). Once a query with the new credential returns a hook pod's lines, the
  runbook route in `docs/runbooks/argocd.md` drops "unconfirmed".
- Settled: the plaintext elastic superuser password in ElasticsearchDeploy's
  `config/prd/values.yaml` is **out of scope**; ANS-200 tracks moving it to OpenBao and rotating
  it.

#### Grounding (verified 2026-10-03; binds the plan)

- **Premise correction — rule count.** The card's "Prometheus has 8 rules" is stale: prd has 10
  alert rules in 6 groups (node-memory-pressure ×3, node-reservation, s3-mirror, backup-freshness
  ×2, argocd ×3 from slice 028 — ArgoCDSyncStillFailed, ArgoCDHealthStillDegraded,
  ArgoCDAlertsBlind). Argo's own `ArgoCDSyncFailed`/`ArgoCDHealthDegraded` notification events
  route to the `*-no-resolve` Telegram receivers. This answers R1's "check the overlap".
- **Prometheus deploy.** Upstream `prometheus` chart 29.33.0 (not kube-prometheus-stack, no
  Prometheus Operator, no PrometheusRule CRD) from `PrometheusDeploy`, Argo CD app
  `prometheus-prd`, namespace `prometheus-prd`. Rules are `serverFiles` `alerting_rules.yml` and
  Alertmanager config in `config/prd/values.yaml`. Alertmanager has 4 Telegram receivers
  (critical/warning × with/without `send_resolved`), default `telegram-warning`,
  `severity=critical` → `telegram-critical`. Tests: `tests/alert-rules.sh` (promtool, one test
  file per rule group) and `tests/alert-routing.py` (every alert reaches a Telegram receiver —
  the heartbeat alert is the deliberate exception this slice introduces). Repo has
  `.kubecoder/project.yaml`.
- **kube-state-metrics** runs in `prometheus-prd` with an explicit `--resources` list including
  `endpointslices`, `nodes`, `pods` but not `endpoints` (so `kube_endpoint_*` does not exist;
  `kube_endpointslice_*` does). `kube_pod_container_status_waiting_reason` returned empty on
  2026-10-03 — nothing on prd was crash-looping or image-pull-stuck then; the plan must confirm
  the series is emitted when a container waits (not filtered out by the metric allow-list) before
  relying on it.
- **MetalLB** v0.15.2, L2 only; `servicel2statuses.metallb.io` CRD present; controller and speaker
  scraped on :7472; `metallb_speaker_announced` present (23 series). No blackbox exporter exists;
  no Service carries `prometheus.io/probe`.
- **DHCP.** Deployment `dhcp` in `dnsmasq-prd` (DnsmasqDeploy), Service `dhcp` LoadBalancer
  10.2.1.10, 67/UDP, fixed `loadBalancerIP` since the outage. The router relays to 10.2.1.10.
  Outage mechanism (`AnsibleSpecs/handovers/dhcp-outage-2026-09-25/report.md`): Keycloak in
  ImagePullBackOff → auth.ginbov.nl 502 → the DHCP app sidecar crash-looped on OIDC discovery →
  pod not Ready → EndpointSlice not ready → MetalLB never announced → no ServiceL2Status → zero
  DISCOVERs reached dnsmasq for 2h45m.
- **The 2026-09-25 probe was never recorded as a command** — only its shape
  (`handovers/dhcp-outage-2026-09-25/plan.md`: "A relay-style DISCOVER to 10.2.1.10 (giaddr
  10.1.0.1) got an Intranet OFFER"). The plan designs the probe and must prove how the OFFER
  reaches a probe host that is not the relay (a relay-addressed reply goes to giaddr).
- **srviac**: VM 920, static 10.1.0.45/16 (`ansible/inventories/prd/host_vars/srviac.yml`,
  `terraform/prd/vms.tf`), role `iac_agent` (tree `support/iac-agent/`), resolvers 8.8.8.8/8.8.4.4
  with a `~home` routing drop-in, node-exporter :9100 scraped by Prometheus's `homelab-nodes` job as
  `srviac.home:9100`. Holds the OpenBao AppRole `iac-agent`. Per decisions.md, srviac is bring-up
  infrastructure and must not depend on in-cluster DHCP/DNS.
- **healthchecks.io** is used nowhere in code today; ANS-15 (the Telegram bot that was to carry it)
  is Later and unbuilt — this slice does not build it.
- **Elasticsearch**: plain Deployment `elasticsearch` in `elasticsearch-prd` (ElasticsearchDeploy,
  Argo CD), single node, `xpack.security.enabled=true`, URL
  `http://elasticsearch.elasticsearch-prd.svc:9200`; Kibana at `kibana.home`. Users are created by
  the setup Job (`registry:5000/elasticsearch-setup`, source
  `/work/DockerImages/elasticsearch-setup/app/main.py`), which today sets `kibana_system`'s
  password and creates `logstash_internal` (role `logstash_writer`); the Job name derives from the
  image pin, so it reruns only on an image change. The chart already has an `externalSecrets`
  values section. Filebeat (FilebeatDeploy) writes `filebeat-*` with a 7-day delete ILM; its
  credential comes from OpenBao `eso/prd/filebeat/prd/elastic-credentials`. OpenBao runtime
  secrets live in the `kv` mount under `eso/<cluster>/<app>/<stage>/<leaf>`; no automation mints
  a service user and writes its credential to OpenBao — the operator writes it
  (`docs/live-infra-access.md`, "writing OpenBao secrets").
- **Runbook route**: `docs/runbooks/argocd.md` "A replaced hook's log: Kibana" ends "Until it
  returns that pod's lines, treat this route as unconfirmed."

## Ordering constraints

- The setup-image phase (DockerImages) lands before the ElasticsearchDeploy phase that pins the
  new image.
- The runbook confirmation comes last: it needs the user live and a query run with it.

## Not in scope

- Exposing ELASTIC_URL/ELASTIC_USER/ELASTIC_PASSWORD to KubeCoder environments (KC-124).
- The ANS-15 Telegram bot; a srviac heartbeat probe (D1 chose healthchecks.io).
- New Argo CD alert rules (covered by slice 028).
- Moving or rotating the plaintext elastic superuser password (ANS-200).
- Alerting on the dev cluster.
