# P7 code review — round 1

Range `32dab1f..132c3d7` (Ansible, `phase/014-P7`): `docs/runbooks/argocd.md` only.

**Readiness: ready to merge.** The new section `## Giving an app its own architecture producer`
and the paragraph added at the flip in the registering section deliver everything the phase's
outcome and V07 ask for. It gives the steps. The producer id is `<app>-deploy`, and the chart name
must equal the registry directory. `.architecturerc` names the real sources and carries only the
three keys. It warns that an owned product is minted once. The job and the `repo:` registration are
the operator's, after the first green build. At a handover the producer is registered before the
flip, with the collector red in between, and a new app has no flip. The promotion-branch gap is
stated as a fact of today with no card id. Before accepting the text, I checked each factual claim
against the code it describes. The claims below all held:
- the reconciler default (HelmCharts `tools/deploy/deploy_cli/release.py:155-174`) and the skip
  (`gen_architecture.py:586-587`)
- HelmCharts' dating query (`gen_architecture.py:170-173`; the runbook's command yields
  `2026-06-17` for `charts/kubecoder`)
- the shared `NS` constant (ArgoCDTools `gen_architecture.py:121`)
- `--stage` required and single-valued (`:678-686`), and `gap:` written to stderr without failing
  the run (`:1015-1018`)
- the handover check's flags, its derivation of the app from the chart name, and its clone of the
  checkout's HEAD, which makes it generic for any app (`handover_equality.py:81-90`, `:212-237`,
  `:251-252`)
- the registry entry shape (`pipeline-producers.schema.yaml`)
- fleet.py's `RC_KEYS`, its `origin/HEAD` clone and default-branch push, and its reading of gaps
  from the last successful build (`fleet.py:17-27`, `:36`, `:94-95`)
- both deploy repos' `Jenkinsfile.architecture`, `.kubecoder/project.yaml`, `.gitignore` and
  `.architecturerc`

Both in-page anchors resolve. The gate has no statements for root, so it proves nothing here. That
is expected for a doc-only phase. One advisory finding.

## Findings

### F1 — Minor · advisory · comment-prose · anchor: none · confidence: high

The runbook's dating rule for a new app contradicts its own worked example.
`docs/runbooks/argocd.md:317-318` says *"A new app takes the date of its deploy repo's first
commit."* The table at `:275` offers ArgoCDDeploy as the new-app example "to copy from". ArgoCDDeploy
dates the app from the first commit carrying the chart, not from the repo's first commit:
`/work/ArgoCDDeploy/architecture.yaml:5-7` has *"The first commit carrying the chart"*,
`introduced: '2026-08-17'`. `git -C /work/ArgoCDDeploy log --reverse` shows the repo's first commit
is `e8cb797` on 2026-08-16, a README-only "Initial commit". The chart arrives in `3fc0b7e` on
2026-08-17. P2's done-record states that choice as HelmCharts' dating rule, applied to `chart/`.
The same bullet, at `:305-306`, also says "a deploy repo's history dates the repo, not the app".
A reader following the stated rule for the next new app dates it from whatever the repo's first
commit holds, and the worked example would have given a different date. No ids are affected: a new
app has no published elements to match. So this is only a wrong `introduced` value on a new app's
elements.
