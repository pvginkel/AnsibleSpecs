# Slice 040 — plan review, round 1

**Verdict: questions.** The plan covers slice.md's requirements one to one, and each of the 14
criteria can be earned by a phase or by a named operator step. The citations I opened hold, in
PrometheusDeploy, ElasticsearchDeploy, DockerImages, ArgoCDDeploy, ArgoCDTools and Ansible. I
re-checked live: kube-state-metrics v2.20.0 runs with only `--port`/`--resources`,
`kube_service_labels` is empty, prd runs Alertmanager v0.34.1, `metallb_speaker_announced` has 23
series, and 42 unannounced LoadBalancer Services sit in `kubecoder-prd` (32) and `kubecoder-dev`
(10). I worked two expectations out on my own and they match the plan:

- **P6's immutable-Job collision.** The two ElasticsearchDeploy commits land separately, so in
  either order one sync changes the Job template under an unchanged pin-derived name.
- **P1's reply path.** Under RFC 2131 §4.1 the reply goes to `giaddr` on port 67, which is the
  attachment's witness.

The Targets resolve:

- PrometheusDeploy and ElasticsearchDeploy are not in `.kubecoder/config.yaml`, and each carries a
  `.kubecoder/project.yaml`.
- `../DockerImages` is checked out.
- `root` holds `docs/runbooks/`.

The task shape, the phase order and the one attachment are sound. One finding needs the operator.

## Operator-decidable

### Q1 — The reader credential cannot open the Kibana route that P7 declares confirmed for it

**Problem.** R3's second half is "the Kibana route … can be checked, and it becomes a real
answer". The route in the runbook is the Kibana UI. P5 builds a reader whose only privilege is an
index privilege. P7 and V10 then declare the Kibana route a real answer *for a holder of that
credential*, and the plan never says which surface the confirming query goes through. Nobody
downstream is authorised to decide what that surface is.

**Evidence.**
- `docs/runbooks/argocd.md:160-165`: the route is "`https://kibana.home` → Discover, data view
  `filebeat-*`" with a KQL query string. KQL runs only in Kibana. Elasticsearch's own API does not
  take it.
- P5 asks for "a role that grants read on the `filebeat-*` indices and nothing else: no write, no
  cluster privilege, no other index", and "a user that holds only that role". V09 repeats this.
- Elastic's security model (documented; I did not try it live, for want of the credential): a user
  needs Kibana feature privileges in its role to use Kibana at all. Those are application
  privileges, which "nothing else" excludes. A user that holds only index privileges is refused
  by Kibana and never reaches Discover or the `filebeat-*` data view.
- P7: "The route becomes a real answer for a reader who holds the reader credential, which KC-124
  later exposes as `ELASTIC_URL`/`ELASTIC_USER`/`ELASTIC_PASSWORD`." V10: "a query made with the
  new credential returns a current Argo CD hook pod's lines … the runbook's route … reads as an
  answer for a reader who holds the credential". Neither says whether that query goes through
  Kibana or through Elasticsearch's API. The variable names KC-124 exposes point to the API.

**Impact.** The run can go one of two ways:

- **The test agent queries the API.** It queries Elasticsearch's API with the credential, which
  is the natural move for an agent. The query passes, and the runbook ships a Kibana Discover
  route stated as confirmed for a credential that cannot open Kibana. That is again an unproven
  claim stated as an answer, the thing R3 asks to remove, and V10 is checked off on a query that
  never exercised the route.
- **The test agent tries Kibana.** It is refused, and files the blocking finding D4 prescribes.
  The fix loop then has two ways out. One widens the role beyond R3's "can only read the
  `filebeat-*` indices". The other changes what the runbook's route is. Both choices are the
  operator's, and the run would make one unattended.

**The operator's call.** Which surface the reader credential must serve: Kibana Discover, the
Elasticsearch API, or both. That decides what "the Kibana route … can be checked" is checked
through, and what P7 may claim for a holder of the credential.

## Blocking

None.

## Advisory

### A1 — P4's new outbound SaaS dependency has no place in the architecture artifact, and the plan is silent on it

- **Problem.** P4 makes Alertmanager call healthchecks.io. PrometheusDeploy's judgment layer
  records what serves Alertmanager: `architecture.yaml:19-21` has
  `served_by: ["svc:telegram-bot-api,…"]`.
- **Why P4 cannot record it.** A `served_by` id is "drawn as written and never resolved", and
  must be an element the dataset publishes (`ArgoCDTools/aac-tools/image/gen_architecture.py:133-136`).
  Third-party SaaS elements are declared in
  `Architecture/docs/architecture/external-services.yaml`, and no phase targets that repo. Unlike
  P3's image (`gen_architecture.py:1030-1034`), no gate flags the omission.
- **Impact.** Either the published architecture leaves out the dead-man's switch's external
  dependency, or P4 writes a `served_by` id that resolves to nothing. Whether to model it is the
  plan's to state, either way.

### A2 — Nothing re-applies a changed reader password

- **Problem.** P5 says "Running the Job again converges, including onto a changed password", and
  P6 makes the Job rerun on a spec change. The spec carries a `secretKeyRef`, not the value. An
  OpenBao rotation therefore refreshes the ESO Secret but reruns nothing.
- **Impact.** After a rotation, Elasticsearch keeps the old password while KC-124 hands every
  environment the new one. The plan names no rotation path.

### A3 — No verification path is named for V09's negative half

- **Problem.** V09 asserts "The user can neither write nor read an index outside `filebeat-*`".
  Witnessing that live needs the reader's password. D4's permission is "to run the query
  confirming the runbook's Kibana route".
- **Impact.** A test agent that holds D4 to its stated purpose verifies V09 from P5's code only.
  Whether the one read also covers V09's live checks is a widening only the operator can grant.
