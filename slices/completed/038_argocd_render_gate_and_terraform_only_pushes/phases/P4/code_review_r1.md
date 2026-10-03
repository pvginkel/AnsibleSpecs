# P4 code review — round 1

**Readiness: ready to merge, no findings.** The branch (`14ec1f7..2ece6fd`, FieldnotesDeploy
`phase/038-P4`) is one commit on top of origin `main` that changes FieldnotesDeploy's library
version and nothing else: `chart/Chart.yaml:8` pins `"0.4.0"` and `chart/Chart.lock` is
re-resolved to `0.4.0` with a new digest; `git grep` finds no other place in the repo that
states the version (the plan's "no test of its own pins the version" holds). The phase's opening
publish is witnessed independently: Charts `origin/main` is `8fc4717` (P3's commit), and
`https://charts.home/index.yaml` lists `homelab-shared` `0.4.0`. The gate is green on this commit
(`gate_r1.log`), and `chart-deps` building from the lock would refuse a lock out of sync with
`Chart.yaml`. A targeted render of the prd stage at a different revision (`hook.revision=abc123`)
carries the ConfigMap `tf-presync-revision` in `fieldnotes-prd` with `data.revision: "abc123"` and
no annotations, so the object follows the revision the render is given, as the outcome requires.
Nothing was pushed to FieldnotesDeploy, as the phase requires; the live proof (V03) is the test
phase's.

## Findings

None.
