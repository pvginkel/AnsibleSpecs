# P7 code review — round 2

**Readiness.** The fix commit (`ea17776`, `docs/runbooks/argocd.md:180-216` only) resolves F1, so
the phase may merge. The API route now runs in two steps. The first is a `size: 0` search with a
`terms` aggregation on `kubernetes.pod.name`, ordered by a `max(@timestamp)` sub-aggregation
`desc`. It lists each attempt of the app as one bucket, newest first, together with its last
line's time (`:186-197`). The second fetches one attempt's lines with an exact `term` on the pod
name, sorted ascending (`:201-212`). The current attempt can no longer be cut off by older ones:
for F1's repro input `fieldnotes-prd` (35 pods in 7 days), step one returns 35 buckets, well
under `size: 500`. The busiest Job I counted, webathome-org-prd at 195 pods, is also under that
limit. Step two reads about 100 lines from a single pod, against a cap of 10,000 (the default
`max_result_window`).

The field types hold. FilebeatDeploy's `chart/files/filebeat/filebeat.yml:25` sets
`setup.template.enabled: true`, so Filebeat's stock template maps `kubernetes.pod.name` and
`kubernetes.namespace` as `keyword` and `@timestamp` as `date`. A terms aggregation and an exact
`term` therefore work on the pod name, and a `max` on `@timestamp` returns `value_as_string`, the
field the `jq` filter reads. The section's other text agrees with the change. The "verified" line
names "the two API queries above" (`:215-216`), which the test phase confirms before the push, as
plan.md P7 ("writes the route in its confirmed form") and V10 set out. Round 1's F2 is advisory
and stays unfixed. That is correct, and I do not re-report it. The fix introduces no new
findings. The gate was green on `ea17776`. I did not run anything live, because this round
touches no live premise beyond the Filebeat template, which I read from the repo.

## Findings

None.
