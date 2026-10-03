# Slice 040 — refinement

## D1 — Whether the out-of-cluster dead-man's switch is a healthchecks.io check or a probe on srviac

**Context.** Alertmanager runs in the cluster and pages you over Telegram, through a critical and
a warning receiver; nothing outside the cluster can send a notification today. The outage card
asked for an out-of-cluster heartbeat and named two homes for it: the healthchecks.io leg of the
Telegram-bot card, or a probe on srviac once srviac had a static address. The Telegram-bot card is
parked in Later and unbuilt, healthchecks.io is used nowhere in the estate, and srviac has held its
static address since the outage.

**The ask.** A cluster that fails to cold-boot, or an alert pipeline that dies, makes no noise
today — Prometheus and Alertmanager go down with it. Something outside the cluster has to notice
when they stop and tell you.

**Background.** A home outside the cluster is either a service you hold an account with or a host
you keep running. srviac is the only host outside the cluster this slice already touches (it
carries the DHCP probe), and it sits on one Proxmox host.

**Why yours.** It adds either an external SaaS account you own or code on srviac you keep running;
the card named both.

**Recommendation.** healthchecks.io. Prometheus carries an always-firing heartbeat alert;
Alertmanager sends it every few minutes to a healthchecks.io check through a webhook receiver;
when the pings stop, healthchecks.io notifies you — through its own Telegram integration to the
same chat, or by email. That covers every way the pipeline can die — a failed cold boot,
Prometheus or Alertmanager down, the whole homelab off power or off the internet — with no new
code to keep running. The trade-off is an external dependency and an account you create by hand
(account, check, notification channel, and the ping URL written to OpenBao — an operator
procedure), and the ping URL is a secret Alertmanager must read. Not verified: whether you already
have a healthchecks.io account (asked below).

**The other way.** A timer on srviac that checks Alertmanager is alive and sends to Telegram
directly with the bot token from OpenBao: no SaaS, all self-hosted — but new code to maintain,
and srviac sits on one Proxmox host, so a power or internet loss, or that host down, is silent
again.

**If this is wrong.** Low: the receiver swap is small; the cost is one more operator setup done
for nothing.

**Operator.** agree (2026-10-03, in chat)

## D2 — How wide the pod-health alerts reach: every namespace, or an allow-list of infrastructure namespaces

**Context.** Prometheus on the production cluster carries ten rules today: node memory stall,
backups, and the three Argo alerts the Argo CD slice delivered last week (sync still failed,
health still degraded, Argo metrics gone). None watches pod state. Alerts reach Telegram only, as
critical or warning, and kube-state-metrics already exposes pod and node state.

**The ask.** The outage card asks for an alert on a pod stuck crash-looping or unable to pull its
image. In the outage the two failing pods were Keycloak (image pull) and the DHCP pod (crash
loop); a pod-level rule would have caught both.

**Background.** The pod rule is one query; what varies is which namespaces it watches. The
production cluster also hosts things that break by design — a KubeCoder environment a developer is
mid-way through, a deploy left half done. Node not-ready and a LoadBalancer with no ready
endpoints or no MetalLB announcement are critical and cluster-wide by nature; the scoping question
is the pod rule's alone.

**Why yours.** How much noise you tolerate for coverage of a namespace nobody thought to list is a
preference only you can judge.

**Recommendation.** Every namespace on the production cluster, warning severity, after the
condition has held fifteen minutes, one alert per pod. It catches the next unknown failure
wherever it lands. The trade-off: anything that crash-loops routinely — an environment a developer
broke, a half-finished deploy — pages as a warning until it is fixed or excluded. Today nothing
on the production cluster is crash-looping or stuck pulling an image.

**The other way.** An allow-list of infrastructure namespaces (DHCP and DNS, Keycloak, ingress,
Argo CD, Prometheus, storage): quiet, but a new critical app is silent until someone adds it.

**If this is wrong.** Noise, or a missed pod; the scope is one rule line to change.

**Operator.** agree (2026-10-03, in chat)

## D3 — Whether the LoadBalancer alert skips KubeCoder environments' Services

**Context.** The plan is written: seven build phases across the Prometheus deploy, Ansible,
DockerImages and the Elasticsearch deploy, plus test and doc. When you agreed the pod alerts
(every namespace, warning, fifteen minutes), the same ruling made the alert on a LoadBalancer
Service that MetalLB does not announce critical and unscoped, on the grounds that such Services
are cluster-wide by nature. The plan's alert phase defers to that ruling and builds whatever you
rule here.

**The ask.** The outage card's first missing signal is the DHCP failure itself: a LoadBalancer
Service with no ready endpoints, which MetalLB therefore never announces. The alert has to page
when a Service that serves the house has lost its address.

**Background.** Queried live on the production cluster on 2026-10-03: 42 of its 65 LoadBalancer
Services were not announced by MetalLB, and every one of the 42 is a KubeCoder environment — a
stopped environment keeps its LoadBalancer Service with no pod behind it, so unannounced is its
normal state. Every other LoadBalancer Service, DHCP and DNS among them, was announced. Built as
agreed, the alert sends 42 critical pages the moment the Prometheus deploy is pushed; they never
resolve, and every environment stop adds one more.

**Why yours.** It narrows an alert you agreed as unscoped.

**Recommendation.** Skip KubeCoder environments' Services; every other LoadBalancer Service stays
in scope and critical, so the alert means what you wanted it to mean: something that serves the
house has lost its address. The trade-off: a running environment whose pod breaks gets no
LoadBalancer alert; the pod alert you agreed, a warning, still catches its crash loop or image
pull. Whether the rule recognises an environment by its namespace or by the KubeCoder label is
settled in the plan.

**The other way.** An allow-list of infrastructure Services (DHCP, DNS, ingress and so on): the
quietest, but a new LoadBalancer Service is silent until someone adds it — the trade-off you
rejected for the pod alert.

**If this is wrong.** A missed address loss on a running environment (low), or noise; one matcher
to change.

**Operator.** "Agreed" (2026-10-03, in chat)

## D4 — Whether the test phase may read the Elasticsearch reader's password from OpenBao to confirm the runbook's Kibana route

**Context.** The plan is written; its runbook phase (the Argo CD runbook's Kibana route to a
replaced hook's log, confirmed) is written for this recommendation, and the test phase pushes the
Ansible repo last. Already settled, and you saw it: the read-only Elasticsearch user is created by
the setup Job from a password you write to OpenBao; the Kibana check uses a current Argo CD hook
pod's log; and once a query with the new credential returns that pod's lines, the runbook drops
"unconfirmed". The standing rule is that an agent reads no OpenBao secret value without your
explicit permission, given per path.

**The ask.** The log-access card asks that, with the reader in place, the Kibana route the Argo CD
runbook gives for a replaced hook's log be checked, so it becomes a real answer instead of an
unconfirmed one.

**Background.** Two facts of the run stand in the way. The reader exists only after the test
phase's pushes — the image build, CI writing the pin into the Elasticsearch deploy, then Argo CD
syncing the Job — so no build phase can run the confirming query. And the query needs the
reader's password, which lives only in OpenBao.

**Why yours.** It is a read of an OpenBao secret value by an agent, which only your per-path
permission allows.

**Recommendation.** Allow the test phase to read the reader's password, once, at the one path the
plan names — the Elasticsearch reader's leaf under the production ESO tree,
`kv/eso/prd/elasticsearch/prd/filebeat-reader`, property `password` — to run the confirming query
against a current hook pod's log. The runbook edit is written as confirmed, but the Ansible repo
is pushed only after the query has returned lines; a query that returns nothing is a blocking
finding and comes back as work. The trade-off: one agent sees one credential — a read-only key to
seven days of logs, the same one the KubeCoder card will hand to every environment anyway.

**The other way.** You run the query after the run, and the runbook edit leaves the slice as a
close-out action: no credential read by an agent, but the runbook keeps saying "unconfirmed" until
you do it, and the slice delivers the log-access requirement only in part.

**If this is wrong.** A credential read you did not want (low: read-only, logs only), or a runbook
line that stays unconfirmed.

**Operator.** "Agreed" (2026-10-03, in chat)

## Open facts — questions only you can answer

**F1.** Do you already have a healthchecks.io account, and should its notification go to the same
Telegram chat Alertmanager uses? Settles the operator procedure under D1.

**Operator.** "I just created an account. Telegram is fine." (2026-10-03, in chat) — healthchecks.io's own Telegram integration, set up in healthchecks.io.

## Settled

- The outage card said Prometheus has eight rules covering node memory stall and backups only; it
  has ten, the Argo CD slice having added three Argo alerts (sync still failed, health still
  degraded, Argo metrics gone), and Argo's own sync-failed and degraded notifications also reach
  Telegram — so the card's "check the overlap" is answered: Argo sync-failed and degraded are
  covered, and this slice adds no Argo rule.
- The relay-style DHCP probe that got an OFFER on the outage day was recorded only by its shape — a
  unicast DISCOVER to the DHCP service address with the relay address set — never as a command;
  the plan designs the probe from that shape, and not verified is exactly how the OFFER gets back
  to a probe host that is not the relay, which the plan must prove.
- The DHCP probe runs on srviac — outside the cluster, on the static address it has held since the
  outage, so it does not depend on the DHCP it tests — as a systemd timer that writes its result
  to srviac's node-exporter, which Prometheus already scrapes; an alert fires on failure and on the
  result going stale, and you run the Ansible playbook for srviac.
- OIDC discovery is probed by a blackbox exporter added to the Prometheus deploy, on the homelab
  realm's discovery URL — the one the cold-boot runbook checks.
- The read-only Elasticsearch user is created by the Elasticsearch setup Job, with a new role that
  reads the filebeat indices only; you generate its password and write it to OpenBao with one
  command, at a path both the setup Job and the later KubeCoder card can read, and the Job picks
  it up from there — manual creation in Kibana loses on being unrepeatable.
  **Operator (plan review, 2026-10-03):** "I would prefer access is not limited to specific data
  sets. I would like it to be able to read all data. If Kibana adds value (it sounds like it does),
  and this allows logging into Kibana, that's a plus." — the user reads all data and can log into
  Kibana, still read-only.
- The Kibana check in the Argo CD runbook uses a current Argo hook pod's log — the one the runbook
  names expires around 2026-10-08 — and once a query returns lines, the runbook drops
  "unconfirmed".
- The plaintext elastic superuser password in the Elasticsearch deploy repo's values is out of
  scope; the session files a card for moving it to OpenBao and rotating it.
- Exposing the credential to every environment stays with the KubeCoder card; your "yes" on the
  Elasticsearch card covers the user and its OpenBao credential, which is all this slice does.
- Size: about seven build phases plus test and doc — the Prometheus deploy repo (Kubernetes-state
  rules; blackbox exporter and OIDC probe; dead-man's-switch receiver), Ansible (DHCP probe on
  srviac), DockerImages (the setup image creates the read-only role and user), the Elasticsearch
  deploy repo (wiring the new user's password from OpenBao), and the Ansible runbook (Kibana route
  confirmed) — repos PrometheusDeploy, Ansible, DockerImages, ElasticsearchDeploy.
