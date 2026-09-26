# P9 code review, round 1: Docs, HelmCharts is no longer the deploy path

Range `f7877e4..5cfdb0c` (one commit, 20 files). **Ready to merge. Nothing blocks.** Every doc the
phase lists now names the deploy repos and ArgoCDDeploy's registry. The claims I checked against
the repos they describe all hold: the registry entry shape, `.git` suffix, defaults, retry block
and finalizer against `releases/values.yaml`, `values.schema.json` and `releases/templates/applications.yaml`;
`releases`' prune-less automated policy against `chart/templates/releases.yaml`; DnsmasqDeploy's
`static-hosts-config`; StorageDeploy's `backupServer.rcloneRemote`, `s3Mirror.*`, CronJob, script
and `backup-reader` Terraform; the YouTrack digest pin and `jetbrains/youtrack{{ images.youtrack }}`;
StepCaDeploy's Secret names and keys; PrometheusDeploy's `extraScrapeConfigs`; and the stuck-field
figures against the handover findings (52/55). The root-cert inventory matches a tree scan of every
unarchived pvginkel repo: ten copies outside Ansible, and the runbook's md5 block, run as written,
prints eleven identical hashes. Step 11's grep finds the five `argocd.md` blockquotes plus P7's
docstring note, and nothing else uses the phrase. With the five blockquotes deleted, the text
around them still reads correctly (simulated). The executor dropped the handover flip instead of
giving it a note (N3). I checked the reason: all six non-`argo-cd` HelmCharts `release.yaml` files
say `disabled: true`, and all 48 registry apps have an `<app>-deploy` producer. So no handover is
left, and the ruling's intent holds. The gate ran root only, and the plan asks that the
`architecture` test pass when `ansible-architecture.yaml` changes. I ran `kc project test` for
`architecture` and `ansible` on 5cfdb0c. Both passed. The four findings below are all advisory.

## F1: step-ca-bootstrap day-zero step 7 no longer tells the operator to write the new material in · Minor · advisory · anchor: none · confidence: medium

`docs/runbooks/step-ca-bootstrap.md:243-263` used to end in a `kubectl create secret` command. Now
it only describes things: which Secrets the chart reads, that `stage-manifests.yaml` "today"
renders them, and a check that runs "once Argo has synced". It never says to put this ceremony's
new root, intermediate, key, passphrase and `ca.json`/`defaults.json` into
`chart/templates/stage-manifests.yaml`, base64-encoded, and push. The intermediate rotation's step 3
(`:540-549`) gives exactly that instruction for its three values. So an operator re-running the
ceremony after a CA loss can do step 7 without touching StepCaDeploy. Argo keeps serving the old
material, and the step's check (`Serving HTTPS on :8443`) passes on the old intermediate. Step 9
(`:281-288`) then shreds `.step/secrets/*`, the new intermediate key included. The root key in
Roboform can recover from that. Advisory, because the ceremony is not re-run in the normal course.

## F2: design-philosophy says every unit test is under `support/` and run by root's gate, and one is not · Minor · advisory · anchor: none · confidence: high

`docs/design-philosophy.md:61-62` says "Only the Python tools under `support/` carry unit tests,
which the root component's `test` runs". `tools/ai_workflow/test_track_build.py` is a tracked unit
test for `tools/ai_workflow/track_build.py`, and root's `test:` (`.kubecoder/project.yaml:18-20`)
runs only `support/argo-migrate` and `support/recommend-resources`. This is the binding change
doc, so a reader takes root's green as covering `track_build.py` when it does not.

## F3: kubecoder-cutover's P3 record cites `argocd.md` producer steps that no longer exist · Minor · advisory · anchor: none · confidence: high

P9 removed the handover proof and the flip from `argocd.md`'s "Giving an app its own architecture
producer" and renumbered what is left (`docs/runbooks/argocd.md:381-405`): step 2 is now "Push the
published branch", step 4 is the registration PR, and there is no step 5. `docs/runbooks/kubecoder-cutover.md:803-815`
still says to follow that section's "steps 2, 4 and 5" and calls step 2 "the handover equality
check", whose `handover_equality.py` command has left `argocd.md`. P9's new banner (`:8-12`) marks
the file as a finished run's record, so nobody acts on this. The step numbers are simply wrong now.

## F4: k8s-rebuild says HelmCharts' `configs/dev` tree already went into the archive · Minor · advisory · anchor: none · confidence: high

`docs/runbooks/k8s-rebuild.md:258` says "since HelmCharts' `configs/dev` tree went into its
archive (argo-cd D65)". But the archive is ANS-122, an Operator Action after this slice. D65 says
the tree "go[es] into the archive", and `/work/HelmCharts/configs/dev/` is still live today. The
sentence states a future event as done. By the F1 ruling nothing waits on it.
