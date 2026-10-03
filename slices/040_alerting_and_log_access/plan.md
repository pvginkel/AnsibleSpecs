# Slice 040 — Prometheus alerts for the 2026-09-25 DHCP-outage failure modes, an out-of-cluster dead-man's switch through healthchecks.io, and a read-only Elasticsearch user (all data, Kibana login) stored in OpenBao

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
  repeat interval, and `bao kv put` the ping URL at the path the plan names. Later on 2026-10-03
  (EPIC-6): @HealthchecksBot posts into the homelab alerts group, where every alerting bot posts
  under its own name. ANS-201 creates the group, so that step adds the bot to it.
- Ruling D2 (2026-10-03, "agree"): **CrashLoopBackOff/ImagePullBackOff alerts cover every
  namespace on the production cluster, severity warning, after the condition holds 15 minutes,
  one alert per pod.** Node NotReady is critical, unscoped.
- Ruling D3 (2026-10-03, "Agreed"): **a LoadBalancer Service with no ready endpoints / not
  announced by MetalLB is critical, and skips KubeCoder environments' Services** (stopped
  environments keep an unannounced LoadBalancer Service by design — 42 of them on prd on
  2026-10-03); every other LoadBalancer Service stays in scope. Namespace or label match is the
  plan's call.
- Ruling D4 (2026-10-03, "Agreed"): **the test phase may read
  `kv/eso/prd/elasticsearch/prd/filebeat-reader`, property `password`, once, to run the
  query confirming the runbook's Kibana route** against a current Argo CD hook pod's log — and
  (review-A3, agreed 2026-10-03) to witness the user's read-only limits live with that same read
  (a write refused, an administrative call refused). The runbook edit is written as confirmed;
  the Ansible repo is pushed only after that query returns the pod's lines; a failed query is a
  blocking finding. This is the operator's per-path permission for that one OpenBao value — no
  other path.
- Fact (2026-10-03, operator: "yes, both are in"): both OpenBao leaves exist before the run —
  `kv/eso/prd/prometheus/prd/healthchecks` (`ping_url`) and
  `kv/eso/prd/elasticsearch/prd/filebeat-reader` (`password`). The reader's path keeps its name
  (the operator asked for the path and wrote it there), so Ruling D4's permission stands as written.
- Ruling review-A1 (2026-10-03, agreed): **healthchecks.io is modelled in the architecture
  artifact** — declared as an external service in the Architecture repo the way Telegram's Bot
  API is, and named in Alertmanager's `served_by` in PrometheusDeploy's judgment layer.
- Ruling review-A2 (2026-10-03, agreed): **the plan names the reader-password rotation path** —
  `bao kv put` the new value, then make the setup Job rerun (delete it; Argo CD recreates it) —
  documented in ElasticsearchDeploy's README. No automatic re-apply.
- Settled (refinement, operator saw it): the **DHCP probe runs on srviac** (outside the cluster,
  static address 10.1.0.45, does not depend on the DHCP it tests) as a systemd timer writing its
  result to srviac's node-exporter (textfile collector), which in-cluster Prometheus already
  scrapes; an alert fires on probe failure and on the result going stale. The operator runs the
  srviac Ansible playbook.
- Settled: **OIDC discovery is probed by a blackbox exporter added to the Prometheus deploy**, on
  `https://auth.ginbov.nl/realms/homelab/.well-known/openid-configuration` (the URL that failed
  in the outage and the one `docs/runbooks/cold-boot.md` checks).
- Ruling review-Q1 (2026-10-03), on which surface the reader serves — supersedes R3's "only read
  the `filebeat-*` indices": "I would prefer access is not limited to specific data sets. I would
  like it to be able to read all data. If Kibana adds value (it sounds like it does), and this
  allows logging into Kibana, that's a plus." So the user is **read-only over all data** (every
  index; no write, no cluster or index management, no Kibana edits) **and can log into Kibana**
  (Discover etc., read-only), and serves the Elasticsearch API as well. Elasticsearch's built-in
  `viewer` role matches this shape; the plan may use it or an equivalent custom role. The
  runbook route is confirmed through Kibana, and the runbook also gains the equivalent API query
  (agents hold ELASTIC_URL/USER/PASSWORD, not a browser).
- Settled: **the read-only user is created by the Elasticsearch setup Job** (DockerImages
  `elasticsearch-setup`), with the read-only role of Ruling review-Q1; the operator generates
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

## Task shape

cross-cutting — the rulings land work in five repos (PrometheusDeploy rules, blackbox exporter
and heartbeat receiver; Ansible's srviac DHCP probe and runbook; Architecture's external-service
catalogue; DockerImages' setup image; ElasticsearchDeploy's credential wiring) and set a new
pattern: an out-of-cluster probe feeding in-cluster Prometheus through node-exporter's textfile
collector.

## Ordering constraints

- **Two operator steps come before the run** (both are close-out actions headed `Before
  /dev:run-slice`). One: the healthchecks.io check, with the ping URL written to
  `kv/eso/prd/prometheus/prd/healthchecks`. Two: the reader's password, written to
  `kv/eso/prd/elasticsearch/prd/filebeat-reader`, property `password`. The test phase pushes P4
  and P6 to prd, and Argo CD syncs them at once. Without the leaf behind it, the Alertmanager pod
  waits on its Secret mount (`chart/templates/stage-manifests.yaml:6-7` in PrometheusDeploy says
  so of the Telegram Secret), so all alerting stops. Without its leaf, the setup Job waits on its
  Secret.
- **The test phase's push order:**
  - ElasticsearchDeploy and DockerImages go in the order P6's done-record names. CI writes the
    setup image's pin into ElasticsearchDeploy after a DockerImages push
    (`DockerImages/elasticsearch-setup/deploy-pins.json`), so the slice reaches that repo as two
    commits that land separately.
  - The Ansible repo goes last, after both of P7's queries have returned a current hook pod's
    lines (Ruling D4).
  - Architecture goes before PrometheusDeploy, so the collector never meets Alertmanager's
    healthchecks.io edge before its target exists. It would tolerate it: the collector runs
    `--relaxed` (`Architecture/Jenkinsfile:91-103`), and `arch-validate` skips cross-producer
    references (`Architecture/service/src/validate.ts:171-192`).
  - PrometheusDeploy may go before the operator applies srviac's play. Until that apply, P3's
    warning for a stale or missing DHCP-probe result fires. That is expected: the apply resolves
    it.
- P5 precedes P6 because the environment variable that carries the reader's password is P5's to
  name, and P6 wires it. No phase writes the image pin by hand.

### P1 — srviac probes DHCP the way the relay does ✅ DONE 2026-10-03

Target: ansible

srviac gets the DHCP probe the settled ruling describes. It is a systemd timer. Every few minutes
it sends a relay-style DISCOVER to the production DHCP service and records the result through
node-exporter's textfile collector. srviac runs the Debian `prometheus-node-exporter` package
through baseline (`ansible/roles/baseline/tasks/main.yml:119-132`), so the directory is
`/var/lib/prometheus/node-exporter` (`ansible/roles/internal_tls/defaults/main.yml:38`; it
exists on srviac today). The record says whether an OFFER came back and when the probe last ran,
which is enough for P3 to alert on a failure and on a result that has gone stale. The metric
names and labels are this phase's to choose, and its done-record names them for P3.

[attachments/dhcp-probe.md](attachments/dhcp-probe.md) holds the wire as witnessed from srviac on
2026-10-03, and what it settles: the giaddr, the listener on UDP 67, a reply that comes from a
node address and not from the service address, about 3 s to an OFFER, DISCOVER only, and
addressing the service by IP (an exception to design-philosophy's hostnames rule; a comment
names the reason). Take srviac's own address from `host_vars/srviac.yml`'s `network_devices`.

The probe lands through the play that configures srviac (`ansible/playbooks/site.yml:32-41`).
`IaC/Apply` excludes that host, so the operator applies it with `site.yml --limit srviac`.
Whether the probe gets a role of its own is this phase's call. A second run reports `changed=0`,
and `--check --diff` shows what the first run would change.

Before handing over, witness the probe once from srviac, outside Ansible, the way the attachment's
witness was taken: a single DISCOVER, which takes no lease. Applying the role stays the operator's.

**Done (P1).** New role `dhcp_probe` (`ansible/roles/dhcp_probe/`), last role of `site.yml`'s
srviac play: a Python probe at `/usr/local/sbin/dhcp-probe`, a oneshot `dhcp-probe.service` and
`dhcp-probe.timer` (every 3 min), writing `/var/lib/prometheus/node-exporter/dhcp_probe.prom`.
Witnessed from srviac 2026-10-03 07:03 UTC under the unit's sandboxing: OFFER 10.1.1.80 after
3.004 s; dnsmasq logged DHCPDISCOVER/DHCPOFFER for `02:00:00:40:04:01`.

Later phases:
- P3: the series are `dhcp_probe_success` (1 = OFFER within 10 s, 0 = none),
  `dhcp_probe_last_run_timestamp_seconds` (unix time the probe finished) and
  `dhcp_probe_duration_seconds`, each labelled `server="10.2.1.10"`. Cadence 3 min; an erroring
  probe (UDP 67 taken, no route) writes nothing, so staleness covers it. Absent on prd until the
  operator applies `site.yml --limit srviac`.

Record:
- Probe matches replies on `xid` + `chaddr` + OFFER on an unconnected socket bound to
  `0.0.0.0:67`; DISCOVER padded to 300 octets, `hops=1`. No-OFFER exits 0 (a measurement, not a
  unit failure).
- `giaddr` derives in role defaults from the `network_devices` NIC carrying `gateway` (renders
  `10.1.0.45`); `dhcp_probe_server: 10.2.1.10` is a role default with the IP-not-name reason.
- The timer task is skipped under `--check` (as `microk8s` watchdog.yml does): the file diffs are
  the dry run's preview. Unit tests at `ansible/roles/dhcp_probe/tests/`, wired into the root
  component's `kc project test`.

### P2 — PrometheusDeploy: pod, node and LoadBalancer alerts ✅ DONE 2026-10-03

Target: github:pvginkel/PrometheusDeploy

This environment's config does not check the repo out. The driver adopts or clones it at
`/work/scratch/PrometheusDeploy` for this slice.

New rule groups in `config/prd/values.yaml`'s `serverFiles` alerting rules (`:58-371`). Each
window's comment gives its reason, as the existing groups' comments do. Each group gets promtool
tests under `tests/alert-rules/` (run by `tests/alert-rules.sh:15-17`), with a firing case and a
quiet case at every edge the rule claims:

- **A pod stuck in CrashLoopBackOff or ImagePullBackOff**, scoped and timed as Ruling D2 says:
  every namespace, warning, 15 minutes, one alert per pod. The production cluster also hosts the
  dev stage's `*-dev` namespaces, so those are included. Two things must not restart the 15
  minutes: the short spells a crash-looping container spends running between back-offs, and a
  pull that flips between ErrImagePull and ImagePullBackOff. kube-state-metrics v2.20.0 runs with
  only `--port` and `--resources` (no metric allow-list), and the series appears whenever a
  container waits. Witnessed on 2026-10-03: Prometheus' history holds the outage's
  `keycloak-prd` ImagePullBackOff and `dnsmasq-prd` `dhcp` CrashLoopBackOff series.
- **A node NotReady**: critical, cluster-wide (Ruling D2). The window lets a node's ordinary
  reboot pass. Prometheus' 42-day history shows how long the nodes' recent NotReady spells lasted.
- **A LoadBalancer Service that MetalLB does not announce**: critical, on every LoadBalancer
  Service except KubeCoder environments' (Ruling D3). The speaker's `metallb_speaker_announced`
  (speaker scraped on :7472) is the announcement, the same fact a `ServiceL2Status` records.
  MetalLB withdraws a Service with no ready endpoints, which is the outage's chain (handover
  `report.md`), so one signal covers both of R1's halves. Add the EndpointSlice signal only if it
  catches something the announcement misses. A gap in MetalLB's own metrics must not read as
  every Service unannounced.

  The rule recognises an environment's Service by the `app.kubernetes.io/managed-by: kubecoder`
  label KubeCoder puts on it, not by its namespace. `kubecoder-prd` also holds KubeCoder's own
  Helm-managed Services, and a LoadBalancer that KubeCoder's deploy adds there is not an
  environment, so it stays in scope. kube-state-metrics exports no Service labels today: its only
  flags are `--port` and `--resources`, witnessed live. The label therefore needs a labels
  allow-list entry for Services. Live on 2026-10-03, 42 of the 65 LoadBalancer Services were
  unannounced, and all 42 carry that label (32 in `kubecoder-prd`, 10 in `kubecoder-dev`). Every
  other LoadBalancer was announced, so a correct rule fires on nothing when it lands.

`tests/alert-routing.py` already checks that every rule reaches the Telegram receiver its
severity picks, with a "resolved" message. The new rules go through it unchanged.

**Done (P2).** PrometheusDeploy `469380f`, `017c71f`, `6199854` on `phase/040-P2`: three rule groups after `argocd` in
`config/prd/values.yaml` — `pods` (`PodStuckInBackOff`, warning, `for: 15m`, by namespace/pod,
containers and init containers, reasons CrashLoopBackOff|ImagePullBackOff|ErrImagePull over a
5 m `max_over_time`), `nodes` (`NodeNotReady`, critical, `for: 10m`), `loadbalancers`
(`LoadBalancerNotAnnounced`, critical, `for: 10m`; `MetalLBAnnouncementsBlind`, warning,
`absent(up{…component="speaker"} == 1)` for 10 m; the critical rule runs only while some speaker is scraped up, `6199854`). kube-state-metrics gains
`metricLabelsAllowlist: [services=[app.kubernetes.io/managed-by]]`, and `tests/alert-rules.sh`
asserts the rendered flag (`017c71f`). Tests `tests/alert-rules/{pods,nodes,loadbalancers}.yml`;
routing test passes unchanged.

Later phases:
- P4: Alertmanager's `extraSecretMounts` moved to `config/prd/values.yaml:517-521` (cited in place).
- Test phase: `kube_service_labels` exists on prd only once this lands; until then the 42
  unannounced KubeCoder environments' Services would fire. Check on prd after sync that
  `LoadBalancerNotAnnounced` is quiet and `kube_service_labels{label_app_kubernetes_io_managed_by="kubecoder"}` has 48 series.

Record:
- Look-back 5 m, not 10: 42 d of history at 1 m step show running spells ≤ 4 m; a 10 m look-back
  would have fired once (jenkins-prd `iot-support-validation-140`, an 8 m loop). Accepted cost: a
  loop whose last wait falls in the 5 m before minute 15 fires briefly; resolve lags 5 m.
- NotReady spells in 42 d outside the outage: all 1 m. LB announcement drops 2026-09-16..10-03:
  ≤ 6 m outside the outage's dhcp (166 m).
- Guard is "any speaker up", not "all speakers up" (srvk8s4's speaker was `up == 0` for the whole
  outage) and not "any announcement exists" (review r1 F1: an up speaker announcing nothing exports
  no series, so that guard silenced MetalLB withdrawing every Service). A down speaker reads as
  announcing nothing.
- No EndpointSlice signal: the announcement covers the outage chain; nothing found it misses.
- Live 2026-10-03: 48 LoadBalancer Services carry the kubecoder label (38 prd, 10 dev); the
  unannounced 42 are among them. Rule test mutations (look-back, reason set, guard, label, `> 0`)
  each fail a test.

### P3 — PrometheusDeploy: is OIDC discovery answering, is DHCP answering ✅ DONE 2026-10-03

Target: github:pvginkel/PrometheusDeploy

This environment's config does not check the repo out. The driver adopts or clones it at
`/work/scratch/PrometheusDeploy` for this slice.

- **A blackbox exporter in the Prometheus deploy** (settled), probing
  `https://auth.ginbov.nl/realms/homelab/.well-known/openid-configuration`, with a critical alert
  when discovery fails. On 2026-09-25 that failure took down DHCPApp and four other apps
  (handover `report.md`). Argo CD renders one upstream chart per app
  (`ArgoCDDeploy/releases/templates/applications.yaml:34-47`, the `prometheus` entry at
  `releases/values.yaml:207-214`), so the exporter rides the companion `chart/`, not a second
  upstream source. Every image it adds needs an entry under `architecture.yaml`'s `images:`:
  gen-architecture reports an undeclared image as a gap
  (`ArgoCDTools/aac-tools/image/gen_architecture.py:1030-1034`). A product the shared catalog
  lacks is declared in the judgment layer's own `products:`. A probe that cannot run, whether the
  exporter is down or its scrape fails, does not count as a passing probe.
- **The DHCP probe's alerts**, over P1's metrics. Those arrive with the `homelab-nodes` job's
  scrape of `srviac.home:9100` (`config/prd/values.yaml:41-52`). The alert is critical when the
  probe gets no OFFER, which is the 2026-09-25 outage itself. It is a warning when the result is
  stale or missing: srviac down, the timer stopped, or node-exporter not scraped. P1's series,
  each labelled `server="10.2.1.10"` plus the scrape's `instance="srviac.home:9100"`:
  `dhcp_probe_success` (1/0), `dhcp_probe_last_run_timestamp_seconds` (unix time the probe
  finished; the timer runs every 3 min, up to ~10 s late), `dhcp_probe_duration_seconds`. A probe
  that errors writes nothing, so its timestamp ages; the series is absent on prd until the
  operator applies `site.yml --limit srviac` (close-out A3).

Each new group gets promtool tests and goes through the routing test, as in P2.

**Done (P3).** PrometheusDeploy `245ee38` on `phase/040-P3`: `chart/templates/blackbox-exporter.yaml`
(ConfigMap, Deployment, Service `blackbox-exporter:9115`, image
`quay.io/prometheus/blackbox-exporter:v0.28.0`, module `oidc_discovery`: 200, TLS, body carries
the homelab realm's `"issuer"`); scrape job `oidc-discovery` in `extraScrapeConfigs`; rule groups
`oidc-discovery` and `dhcp` after `loadbalancers`; `architecture.yaml` gains image
`blackbox-exporter: ss:blackbox-exporter` and a top-level `products:` entry for it. Tests
`tests/alert-rules/{oidc-discovery,dhcp}.yml`; routing test passes unchanged.

Later phases:
- P4: Alertmanager's `extraSecretMounts` is now at `config/prd/values.yaml:632-636` (cited in
  place); `architecture.yaml` now has a `products:` block below `images:`.
- Test phase: after sync, `up{job="oidc-discovery"}` and `probe_success{job="oidc-discovery"}`
  read 1 on prd and `OIDCDiscovery*` is quiet. `DHCPProbeStale` (warning, labels `job` only)
  fires on prd until the operator applies srviac's play (A3); that is expected, not a finding.

Record:
- OIDC: `OIDCDiscoveryFailing` critical, `probe_success == 0` for 5 m; `OIDCDiscoveryUnprobed`
  warning, `absent(probe_success{job="oidc-discovery"})` for 10 m — a probe that cannot run fires
  the unwatched warning, the same split as P2's blind alerts and the plan's DHCP staleness.
  keycloak-prd had zero available replicas ≤ 3 m in 42 d outside the outage (196 m).
- DHCP: `DHCPNotAnswering` critical, `for: 12m` — a ≤ 6 m announcement drop reads as no OFFER for
  ≤ 10 m 10 s at the 3 m cadence and 1 m scrape. It holds on its own ALERTS while no
  `dhcp_probe_success` is scraped, so it resolves only on an OFFER. `DHCPProbeStale` warning, no
  `for:`: last run > 15 m old (three missed runs pass) or `absent_over_time(...[15m])`.
- Module witnessed with the v0.28.0 binary from here: homelab realm `probe_success 1`, master
  realm 0 (regex), unknown realm 0 (404). Mutations (hold removed, `for` 4 m, look-back 14 m)
  each fail a test.

### P3a — Architecture: healthchecks.io as an external service ✅ DONE 2026-10-03

Target: ../Architecture

Ruling review-A1, its first half: healthchecks.io joins the third-party services the federation
publishes, declared the way Telegram's Bot API is (`docs/architecture/external-services.yaml:29-39`),
so P4 can name it as a service Alertmanager uses. The done-record gives P4 the element's full
composite id: a `served_by` entry is drawn as written and never resolved
(`ArgoCDTools/aac-tools/image/gen_architecture.py:133-136`).

The repo is public (its `CLAUDE.md`): the entry describes the service only, never the ping URL or
anything else about the operator's check.

**Done (P3a).** Architecture `5253da5` on `phase/040-P3a`: `docs/architecture/external-services.yaml`
gains application service `svc:healthchecks-io,4d31c387-4492-4a39-8201-f5a9ff13ad22` (label
`healthchecks.io`, homepage `https://healthchecks.io/`, no logo — the viewer's library has none),
and the file's header comment names Alertmanager as its consumer. `kc project test` green.

Later phases:
- P4: add `"svc:healthchecks-io,4d31c387-4492-4a39-8201-f5a9ff13ad22"` to Alertmanager's
  `served_by` in `architecture.yaml`, beside Telegram's Bot API, written exactly so.
- Test phase: the published architecture draws the element only once `phase/040-P3a` reaches the
  Architecture repo's `main` (a push there redeploys the published dataset).

Record: the summary describes the service generically (pings to hc-ping.com, notification after
the grace period through its own integrations); nothing of the operator's check is in the repo.

### P4 — PrometheusDeploy: a heartbeat to healthchecks.io ✅ DONE 2026-10-03

Target: github:pvginkel/PrometheusDeploy

This environment's config does not check the repo out. The driver adopts or clones it at
`/work/scratch/PrometheusDeploy` for this slice.

The dead-man's switch of Rulings D1 and F1:

- Prometheus raises an alert that always fires, and Alertmanager delivers it to the
  healthchecks.io ping URL through a webhook receiver, never more than 5 minutes apart. The
  operator's check uses a period of 5 minutes and a grace of 10 (close-out action). When
  Prometheus or Alertmanager stops, the pings stop: a heartbeat that has stopped arriving sends
  nothing on its way out, not even a "resolved" ping.
- The heartbeat reaches healthchecks.io only, never Telegram, and no other alert reaches the
  webhook.
- The ping URL comes from OpenBao `kv/eso/prd/prometheus/prd/healthchecks`, property `ping_url`,
  and ESO materialises it into `prometheus-prd` the way `alertmanager-telegram` is materialised
  (`chart/templates/stage-manifests.yaml:9-29`, mounted by `config/prd/values.yaml:632-636`). It
  never appears in the rendered config. prd runs Alertmanager v0.34.1.
- `tests/alert-routing.py` assumes every receiver is a Telegram one (`:83-84`) and that every
  alert reaches one (`:96-109`). It learns the heartbeat as the one exception, and it asserts the
  exception's shape: the heartbeat reaches only the webhook, nothing else reaches the webhook, and
  the heartbeat sends no "resolved".
- Ruling review-A1, its second half: the judgment layer names healthchecks.io, by the id P3a's
  done-record gives (`svc:healthchecks-io,4d31c387-4492-4a39-8201-f5a9ff13ad22`), among the services that serve Alertmanager (`architecture.yaml:18-21`, which
  names only Telegram's Bot API today).

**Done (P4).** PrometheusDeploy `4ad7708` on `phase/040-P4`: rule group `heartbeat` (last, after
`dhcp`) with `Heartbeat` (`vector(1)`, no labels, no `for`); Alertmanager's first child route
`alertname="Heartbeat"` → receiver `healthchecks` (`group_interval: 1m`, `repeat_interval: 1m`, so
pings at most 2 m apart); receiver `healthchecks` = one `webhook_configs` entry, `url_file:
/etc/secrets/healthchecks/ping_url`, `send_resolved: false`; ExternalSecret
`alertmanager-healthchecks` (key `ping_url`) appended to `chart/templates/stage-manifests.yaml`,
mounted by a second `extraSecretMounts` entry at `/etc/secrets/healthchecks`; `architecture.yaml`
served_by lists both services. Tests `tests/alert-rules/heartbeat.yml` and `tests/alert-routing.py`.

Later phases:
- Test phase: after sync, ExternalSecret `alertmanager-healthchecks` in `prometheus-prd` reads
  Ready, the Alertmanager pod has restarted with the new mount (the StatefulSet's pod spec
  changed; it waits on the Secret until ESO syncs it), `ALERTS{alertname="Heartbeat"}` fires, and
  the healthchecks.io check shows pings at most 2 m apart. No Telegram message carries Heartbeat.

Settled beyond the text:
- The heartbeat is matched by `alertname`, and carries no `severity` (the routing test prints
  `None`).
- `tests/alert-routing.py` now walks each route's effective `receiver`/`group_interval`/
  `repeat_interval` and asserts, for Heartbeat, receiver `healthchecks` and interval sum ≤ 300 s;
  that `healthchecks` is exactly `{url_file, send_resolved: false}` (no `url`, so the ping URL is
  never in the rendered config); that no other alert or event reaches it; that every other
  receiver is one Telegram config; and that Heartbeat is raised exactly once. Mutations witnessed
  red: `send_resolved: true`, `repeat_interval: 5m`, a misspelt matcher, critical routed to the
  webhook.

### P5 — DockerImages: the setup image creates the read-only reader ✅ DONE 2026-10-03

Target: ../DockerImages

The `elasticsearch-setup` image (`elasticsearch-setup/app/main.py`) also creates the read-only
reader of Ruling review-Q1, beside what it does today (`:120-130`). The reader reads all data,
through the Elasticsearch API and in Kibana, where it can log in and use Discover. It writes
nothing, manages nothing in the cluster or its indices, and edits nothing in Kibana. prd runs
Elasticsearch 8.15.0 (its log, `version[8.15.0]`), whose built-in `viewer` role is that shape,
as the ruling notes.

The password reaches the image as an environment value, the way the existing ones do (`:5-8`).
P6 wires that value from a Secret. The variable's name and the user's name are this phase's to
choose, and the done-record names both for P6 and P7. Running the Job again converges, including
onto a changed password: P6's rotation path depends on that. The test phase witnesses the
reader's limits live under Ruling D4.

A push builds the image and CI writes its tag into ElasticsearchDeploy's
`images.elasticsearchSetup` (`elasticsearch-setup/deploy-pins.json`). DockerImages declares no
gate for a Dockerfile-only directory, so a `kaniko --no-push` build of the image is this phase's
proof that it builds.

**Done (P5).** DockerImages `234f665` on `phase/040-P5`: `elasticsearch-setup/app/main.py` gains
`create_reader_user`, run after `create_logstash_internal_user`: `put_user` of user `reader`,
role `viewer` (built-in), password from env `READER_PASSWORD`. `architecture.yaml`'s summary
names the reader. `kaniko --no-push` built the image; `kc project test` green.

Later phases:
- P6: wire env `READER_PASSWORD` into the setup Job. The image reads it with
  `os.environ["READER_PASSWORD"]`, so a pin of this image into a Job without the variable fails
  the Job at start (KeyError) — ElasticsearchDeploy's wiring must land before CI's pin.
- P7 and the test phase: the user is `reader` (`ELASTIC_USER=reader`).

Record:
- `viewer` reads every index whose name has no leading dot (data streams included, so
  `filebeat-*` resolves) and is read-only in Kibana; it holds no cluster privilege.
- Convergence: `put_user` with a password on an existing user replaces the password and roles;
  witnessed only against a stub client (call shape), not a live cluster — the test phase
  witnesses the user live under Ruling D4.

### P6 — ElasticsearchDeploy: the reader's password from OpenBao into the setup Job

Target: github:pvginkel/ElasticsearchDeploy

This environment's config does not check the repo out. The driver adopts or clones it at
`/work/scratch/ElasticsearchDeploy` for this slice.

- The setup Job gets P5's password variable, `READER_PASSWORD`, from OpenBao
  `kv/eso/prd/elasticsearch/prd/filebeat-reader`, property `password`, through the chart's
  `externalSecrets` section (`config/prd/values.yaml:6-13`). It is never a value in the repo. The
  KubeCoder card (KC-124) reads the same leaf later. prd's ESO reads `eso/prd/*`
  (`Ansible/ansible/inventories/prd/group_vars/openbao.yml:94-100`).
- The Job runs again whenever its spec changes, not only when its image pin does. Today its name
  derives from the pin alone (`chart/templates/elasticsearch-setup-job.yaml:6`), and the
  completed Job stays (`elasticsearch-setup-14d87`, live). A spec change under the same pin would
  therefore be a same-named Job with a different template. The API server refuses that, because a
  Job's template is immutable, and Argo CD's sync fails.
- The change reaches origin as two commits: this phase's, and the pin CI writes once P5's image
  has built. Whichever lands first must leave a sync that succeeds, and once both have landed the
  reader exists. The done-record names the push order the design needs, for the test phase.
- The README names the reader, its OpenBao leaf, and its rotation path (Ruling review-A2):
  `bao kv put` the new value, then make the setup Job rerun by deleting it so that Argo CD
  recreates it. Followed as written, the path leaves Elasticsearch on the new password. Two facts
  stand in its way, and the README accounts for both:
  - ESO refreshes the Secret from OpenBao hourly (`chart/values.yaml:39-40`). A Job that reruns
    before the refresh applies the old password again.
  - Argo CD does not recreate a deleted Job by itself. The app auto-syncs with `selfHeal: false`
    (live, and `ArgoCDDeploy/releases/templates/applications.yaml:67-70`), and auto-sync skips a
    revision it has already synced (`controller/appcontroller.go:2401-2403` in argo-cd v3.5.1, the
    version prd runs). The Job comes back on the next sync that someone starts.
- Fact for the executor: the Job's `helm.sh/resource-policy: replace` annotation (`:8`) is not a
  policy Helm or Argo CD knows.
- The plaintext elastic password (`config/prd/values.yaml:5`) stays where it is (ANS-200).

### P7 — Ansible runbook: the route to a replaced hook's log, through Kibana and the API, confirmed

Target: root

This phase carries out the settled Kibana-check ruling and Ruling review-Q1 on
`docs/runbooks/argocd.md`'s "A replaced hook's log: Kibana" (`:156-177`). The section drops
"unconfirmed" and stops naming `tf-presync-fieldnotes-prd-sx956` as the check owed; that pod
leaves the 7-day index around 2026-10-08.

The route becomes an answer for whoever holds the reader credential, in two forms:

- **Kibana**, for a person who logs in with the credential.
- **The equivalent API query**, which this phase adds, for an agent. An agent holds
  `ELASTIC_URL`/`ELASTIC_USER`/`ELASTIC_PASSWORD` (KC-124) and no browser.

The section's account of what is verified names both, each made with that credential and each
returning a current Argo CD hook pod's lines.

The route must hold to two facts:

- Kibana answers at `http://kibana.home`, with its own login form (`/internal/security/login_state`
  lists the basic provider alone). `https://kibana.home`, which the section names today, lands on
  another service. Witnessed 2026-10-03, the same as for `prometheus.home` and
  `alertmanager.home`. Elasticsearch answers at `http://elasticsearch.home` (401 without
  credentials).
- The reader cannot save a data view, because it is read-only in Kibana. So a route through a
  saved `filebeat-*` data view holds only if one is already saved, and nobody has checked that one
  is: ANS-164 had no credential.

The reader (Elasticsearch user `reader`, P5) exists only once the test phase's pushes have
landed P5 and P6, so this phase writes
the route in its confirmed form. The test phase confirms both forms before it pushes this repo
(Ordering constraints). Ruling D4 lets it read the reader's password, once, at
`kv/eso/prd/elasticsearch/prd/filebeat-reader`, property `password`, and no other OpenBao value.

- **The Kibana form is confirmed through Kibana:** a browser, or Kibana's own HTTP API with the
  reader's Kibana session. A query sent to Elasticsearch directly confirms only the API form.
- **A blocking finding:** either form returning no lines.

## Not in scope

- Exposing ELASTIC_URL/ELASTIC_USER/ELASTIC_PASSWORD to KubeCoder environments (KC-124).
- The ANS-15 Telegram bot; a srviac heartbeat probe (D1 chose healthchecks.io).
- New Argo CD alert rules (covered by slice 028).
- Moving or rotating the plaintext elastic superuser password (ANS-200).
- Alerting on the dev cluster.
- Applying srviac's play, and creating the healthchecks.io account, check and Telegram
  integration: those are the operator's.
