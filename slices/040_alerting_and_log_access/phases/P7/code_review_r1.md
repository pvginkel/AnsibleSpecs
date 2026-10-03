# P7 code review — round 1

**Readiness.** The diff (`d401415`, `docs/runbooks/argocd.md` only) does most of what P7 asks for.
It drops "unconfirmed" and the `tf-presync-fieldnotes-prd-sx956` check, moves Kibana to
`http://kibana.home`, names `reader` and its OpenBao leaf, covers the case where no data view is
saved (the unwitnessed step is handed to the test phase), and fixes the `destroy-stage` link.
The slug `#a-replaced-hooks-log-kibana-or-the-api` matches the new heading. No other link uses
the old anchor. One problem blocks: the API form, which this phase adds, returns the oldest
1000 lines across every attempt in the 7-day window. For any app that synced more than about ten
times that week, the lines of the attempt you are looking for are cut, and nothing says so.
The gate (green) does not cover prose. I took the numbers below from live Prometheus and
`kubectl logs` and did not re-run the suite.

## F1 — Major · blocking · anchor: repro-trace · confidence: high

**The API query returns the oldest attempts' lines, not the replaced attempt's, and gives no sign
that it truncated.** `docs/runbooks/argocd.md:184-195`: `"size": 1000`, `"sort": [{"@timestamp":
"asc"}]`, a `wildcard` on `tf-presync-<app>-<stage>-*`, and no time-range filter. `jq` prints
only `.hits.hits[]`, so `hits.total` never shows. The wildcard matches every hook pod of that
app in the 7-day retention, because each sync is a new pod (`:157-159`). The query keeps the
first 1000 lines in ascending time and throws away the newest ones. The attempt being
diagnosed is usually the newest.

Repro, using live numbers from 2026-10-03:
- About 100 lines per attempt: `kubectl logs` on current `argocd-hooks` pods gives 98–109
  (calendar-support, ceph-csi-*, charts, dnsmasq, elasticsearch).
- Distinct hook pods per Job over the last 7 days, from Prometheus `kube_pod_info{namespace="argocd-hooks"}`:
  `tf-presync-webathome-org-prd` 195, `tf-presync-kubecoder-dev` 43,
  `tf-presync-fieldnotes-prd` 35, `tf-presync-dnsmasq-prd` 27, `tf-presync-zigbee2mqtt-prd` 20.
- Input `<app>-<stage>` = `fieldnotes-prd` matches about 3,500 lines. The output is the roughly
  10 oldest attempts, about 6–7 days old. The current attempt's lines are missing, and the
  output looks like a complete answer.

This contradicts the section's own claim that "the same query lists each attempt's lines in
order" (`:180-181`). It also breaks P7's outcome: the "equivalent API query", for an agent with
no browser (plan.md P7; V10: "returns the same pod's lines"). The Kibana form does not have this
problem, because it sets "the time range to cover the attempt" (`:169`) and the API form has
nothing like that.

It also bears on V10's proof. The test phase confirms the API form by running it "as written"
against "a current" hook pod. That passes for an app with fewer than about ten attempts this
week, such as calendar-support-prd, and the defect ships unseen.

## F2 — Minor · advisory · anchor: none · confidence: high

**The section describes KC-124's environment variables as if they already exist.** At
`docs/runbooks/argocd.md:162`, "an agent holds it as
`ELASTIC_URL`/`ELASTIC_USER`/`ELASTIC_PASSWORD`", and at `:180`, `http://elasticsearch.home`
(`$ELASTIC_URL`). Exposing them is KC-124's work and out of this slice's scope (plan.md "Not in
scope"). This environment has no `ELASTIC_*` variable today. Until KC-124 lands and picks
`ELASTIC_URL`'s value (which may not be `elasticsearch.home`), an agent that follows the
section looks for variables it does not have.
