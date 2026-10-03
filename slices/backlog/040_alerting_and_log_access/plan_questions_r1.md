# Slice 040 — plan questions, round 1

The plan is complete apart from these two points: P2's LoadBalancer scope, and how P7 gets
confirmed. P2's text defers to Ruling D2, so it holds whatever you rule. P7 and its ordering line
are written for Q2's option A, and the next pass rewrites them if you choose otherwise. Each
point needs your call: the first collides with live state, and the second needs a permission
only you can give.

## Q1 — Should the LoadBalancer alert skip KubeCoder environments' Services?

**The decision.** Ruling D2 makes the alert "a LoadBalancer Service with no ready endpoints / not
announced by MetalLB" critical and unscoped. The refinement put it that way because such Services
are "cluster-wide by nature". On the production cluster that is not true today. On 2026-10-03,
42 of its 65 LoadBalancer Services were not announced by MetalLB (`kube_service_spec_type` less
`metallb_speaker_announced`, queried live). **Every one of the 42 is a KubeCoder environment** in
`kubecoder-prd` or `kubecoder-dev`: a stopped environment keeps its LoadBalancer Service, labelled
`app.kubernetes.io/managed-by: kubecoder`, and has no pod behind it. The other 17 LoadBalancer
Services, including DHCP and DNS, were all announced. Built as ruled, the alert sends 42 critical
pages the moment PrometheusDeploy is pushed. They never resolve, and every environment stop adds
one more.

**Options.**

- **A — skip KubeCoder environments' Services; every other LoadBalancer Service stays in scope
  and critical.** A running environment whose pod is broken then has no LoadBalancer alert.
  Ruling D2's pod alert, a warning, still catches its crash loop or image pull.
- **B — unscoped, as ruled.** 42 critical alerts that stay firing, plus one per stopped
  environment.
- **C — an allow-list of infrastructure Services** (DHCP, DNS, ingress and so on). The quietest,
  but a new LoadBalancer Service is silent until someone adds it. This is the trade-off you
  rejected for the pod alert.

**Recommendation: A.** KubeCoder environments are the only LoadBalancer Services that are
unannounced by design. Without them, the alert means what D2 wants it to mean: something that
serves the house has lost its address. Whether P2 matches on the namespace or on the label is its
own call (the label needs a kube-state-metrics labels allow-list entry; the namespace needs
nothing).

## Q2 — How does the run confirm the runbook's Kibana route?

**The decision.** The settled ruling sets an order: once a query with the new credential returns
a current Argo CD hook pod's lines, `docs/runbooks/argocd.md` drops "unconfirmed". Two facts of
the run stand in the way of that order:

1. **The reader exists only after the test phase's pushes.** The DockerImages push makes CI build
   the setup image and write its pin into ElasticsearchDeploy, and then Argo CD syncs the Job.
   Every code phase runs before those pushes, P7 (the runbook edit) included. So no phase can see
   the reader live.
2. **The query needs the reader's password, which is an OpenBao value.** CLAUDE.md requires your
   explicit permission, per path, before an agent reads one.

**Options.**

- **A — let the test phase read `kv/eso/prd/elasticsearch/prd/filebeat-reader` (property
  `password`) for the confirming query.** P7 writes the route in its confirmed form. After its
  Elasticsearch pushes, the test phase runs the query. It pushes the Ansible repo only once the
  query has returned a current hook pod's lines, so the confirmed text never reaches origin
  before the proof. A failed query is a blocking finding and comes back as a phase. Cost: an
  agent reads one credential once. It is a read-only key to seven days of logs, and KC-124 will
  hand it to every environment anyway.
- **B — you run the query after the run; the runbook edit leaves the slice.** P7 is dropped, and
  R3's runbook half becomes a close-out action: confirm, then drop "unconfirmed" as a doc touch.
  Cost: the slice delivers R3 only in part, and the runbook keeps saying "unconfirmed" until you
  do it.
- **C — the test phase runs the query from a short-lived pod in `elasticsearch-prd` that takes
  the password from the ESO-made Secret, so no agent sees it; otherwise as A.** Cost: the run
  creates an ad-hoc pod in a prd namespace with the cluster-admin kubeconfig, which is more
  moving parts than reading the value.

**Recommendation: A.** It keeps the order the ruling sets as far as anything published goes, and
it keeps R3 inside the slice. The credential it exposes to one agent is the one KC-124 will expose
to all of them. Your ruling would read, for example: "the test phase may read
`kv/eso/prd/elasticsearch/prd/filebeat-reader#password` for the runbook query."
