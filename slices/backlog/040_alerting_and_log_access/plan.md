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

## Task shape

cross-cutting — the rulings land work in four repos (PrometheusDeploy rules, blackbox exporter
and heartbeat receiver; Ansible's srviac DHCP probe; DockerImages' setup image;
ElasticsearchDeploy's credential wiring) and set a new pattern: an out-of-cluster probe feeding
in-cluster Prometheus through node-exporter's textfile collector.

## Ordering constraints

- **Two operator steps come before the run** (both are close-out actions headed `Before
  /dev:run-slice`). One: the healthchecks.io check, with the ping URL written to
  `kv/eso/prd/prometheus/prd/healthchecks`. Two: the filebeat reader's password, written to
  `kv/eso/prd/elasticsearch/prd/filebeat-reader`. The test phase pushes P4 and P6 to prd, and
  Argo CD syncs them at once. Without the leaf behind it, the Alertmanager pod waits on its Secret
  mount (`chart/templates/stage-manifests.yaml:6-7` in PrometheusDeploy says so of the Telegram
  Secret), so all alerting stops. Without its leaf, the setup Job waits on its Secret.
- **The test phase's push order:**
  - ElasticsearchDeploy and DockerImages go in the order P6's done-record names. CI writes the
    setup image's pin into ElasticsearchDeploy after a DockerImages push
    (`DockerImages/elasticsearch-setup/deploy-pins.json`), so the slice reaches that repo as two
    commits that land separately.
  - The Ansible repo goes last, after the query P7 depends on has returned a current hook pod's
    lines.
  - PrometheusDeploy may go before the operator applies srviac's play. Until that apply, P3's
    warning for a stale or missing DHCP-probe result fires. That is expected: the apply resolves
    it.
- P5 precedes P6 because the environment variable that carries the reader's password is P5's to
  name, and P6 wires it. No phase writes the image pin by hand.

### P1 — srviac probes DHCP the way the relay does

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

### P2 — PrometheusDeploy: pod, node and LoadBalancer alerts

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
- **A LoadBalancer Service that MetalLB does not announce**: critical, scoped as Ruling D2 says.
  The speaker's `metallb_speaker_announced` (speaker scraped on :7472) is the announcement, the
  same fact a `ServiceL2Status` records. MetalLB withdraws a Service with no ready endpoints,
  which is the outage's chain (handover `report.md`), so one signal covers both of R1's halves.
  Add the EndpointSlice signal only if it catches something the announcement misses. A gap in
  MetalLB's own metrics must not read as every Service unannounced. Live on 2026-10-03: 42 of the
  65 LoadBalancer Services were unannounced. All 42 are KubeCoder environments in
  `kubecoder-prd`/`kubecoder-dev` (a stopped environment keeps its Service, labelled
  `app.kubernetes.io/managed-by: kubecoder`). Every other LoadBalancer was announced.

`tests/alert-routing.py` already checks that every rule reaches the Telegram receiver its
severity picks, with a "resolved" message. The new rules go through it unchanged.

### P3 — PrometheusDeploy: is OIDC discovery answering, is DHCP answering

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
  stale or missing: srviac down, the timer stopped, or node-exporter not scraped.

Each new group gets promtool tests and goes through the routing test, as in P2.

### P4 — PrometheusDeploy: a heartbeat to healthchecks.io

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
  (`chart/templates/stage-manifests.yaml:9-29`, mounted by `config/prd/values.yaml:399-403`). It
  never appears in the rendered config. prd runs Alertmanager v0.34.1.
- `tests/alert-routing.py` assumes every receiver is a Telegram one (`:83-84`) and that every
  alert reaches one (`:96-109`). It learns the heartbeat as the one exception, and it asserts the
  exception's shape: the heartbeat reaches only the webhook, nothing else reaches the webhook, and
  the heartbeat sends no "resolved".

### P5 — DockerImages: the setup image creates the filebeat reader

Target: ../DockerImages

The `elasticsearch-setup` image (`elasticsearch-setup/app/main.py`) also creates two things,
beside what it does today (`:120-128`):

- a role that grants read on the `filebeat-*` indices and nothing else: no write, no cluster
  privilege, no other index;
- a user that holds only that role, with the password the Job hands it.

The password reaches the image as an environment value, the way the existing ones do (`:5-8`).
P6 wires that value from a Secret. The variable's name is this phase's to choose, and the
done-record names it for P6, along with the user's name. Running the Job again converges,
including onto a changed password.

A push builds the image and CI writes its tag into ElasticsearchDeploy's
`images.elasticsearchSetup` (`elasticsearch-setup/deploy-pins.json`). DockerImages declares no
gate for a Dockerfile-only directory, so a `kaniko --no-push` build of the image is this phase's
proof that it builds.

### P6 — ElasticsearchDeploy: the reader's password from OpenBao into the setup Job

Target: github:pvginkel/ElasticsearchDeploy

This environment's config does not check the repo out. The driver adopts or clones it at
`/work/scratch/ElasticsearchDeploy` for this slice.

- The setup Job gets P5's password variable from OpenBao
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
- Fact for the executor: the Job's `helm.sh/resource-policy: replace` annotation (`:8`) is not a
  policy Helm or Argo CD knows.
- The plaintext elastic password (`config/prd/values.yaml:5`) stays where it is (ANS-200).

### P7 — Ansible runbook: the Kibana route to a replaced hook's log, confirmed

Target: root

This is the settled Kibana-check ruling, carried out on `docs/runbooks/argocd.md`'s "A replaced
hook's log: Kibana" (`:156-177`). That section drops "unconfirmed" and stops naming
`tf-presync-fieldnotes-prd-sx956` as the check owed; that pod leaves the 7-day index around
2026-10-08. The route becomes a real answer for a reader who holds the reader credential, which
KC-124 later exposes as `ELASTIC_URL`/`ELASTIC_USER`/`ELASTIC_PASSWORD`. Its account of what is
verified names a query made with that credential, which returns a current Argo CD hook pod's lines.

The reader exists only once the test phase's pushes have landed P5 and P6, so this phase writes
the route in its confirmed form. The test phase runs that query with the new credential before it
pushes this repo (Ordering constraints). If the query returns nothing, that is a blocking finding.

## Not in scope

- Exposing ELASTIC_URL/ELASTIC_USER/ELASTIC_PASSWORD to KubeCoder environments (KC-124).
- The ANS-15 Telegram bot; a srviac heartbeat probe (D1 chose healthchecks.io).
- New Argo CD alert rules (covered by slice 028).
- Moving or rotating the plaintext elastic superuser password (ANS-200).
- Alerting on the dev cluster.
- Applying srviac's play, and creating the healthchecks.io account, check and Telegram
  integration: those are the operator's.
