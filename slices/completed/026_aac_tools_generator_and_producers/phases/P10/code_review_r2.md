# P10 code review — round 2

**Readiness: ready to merge, with one advisory finding.** The Ansible diff (`b92d01a`) is the same as in round 1 and is still correct:
- `Jenkinsfile.architecture:4,12-13` runs `arch-validate` in `containerTemplates.aac_tools`, which is defined at `JenkinsPipelineUtils/vars/containerTemplates.groovy:33`.
- The `architecture` gate (`.kubecoder/project.yaml:55`) runs through the `aac-tools` sidecar that this environment declares (`.kubecoder/config.yaml:113`), and the r2 gate is green.
- Nothing in the repo still calls the copy.

Round 1's F1 is resolved by AnsibleSpecs `44a3336`. I re-checked its claims against live state:
- The four carriers' Jenkinsfiles call `build job: 'ScanToPdf'` / `'MyDownloads'` / `'Webathome'` with `wait: false` and no guard (ScanToPdfServer:31, ScanToPdfClient:50, MyDownloadsServer:37, MyDownloadsClient:50,55).
- `scantopdf-prd`, `media-prd` and `webathome-org-prd` run `automated: {prune: true}` against ScantopdfDeploy, MediaDeploy and WebathomeOrgDeploy.
- Jenkins records the upstream causes (ScanToPdf #33, #34, #28; MyDownloads #98, #100; Webathome #236, #238).
- The medians in the new text match the last eight green builds: ScanToPdf 1.5 min, MyDownloads 2.3, Webathome 4.2, ScanToPdfServer 1.2, ScanToPdfClient 2.5, MyDownloadsServer 2.3, MyDownloadsClient 18.8.

The reassignment follows P10's own rule that carriers pinning the same deploy repo go in different batches (plan.md:711-712):
- ScantopdfDeploy: P12a batch 2 and P12b batch 1.
- MediaDeploy: P12a batch 3 and P12b step 3.
- WebathomeOrgDeploy (app pin): P12a batch 3 and P12b step 3.

Every deploy repo they pin into is done in the ledger (sweep_ledger.md:47,56,64). The P12a gate text now covers "a job their push starts" (plan.md:731-735). The sweep tool will not skip these builds. `track_build.py` follows `Scheduling project:` lines (`_SCHEDULED_RE`, line 117), and the carriers' consoles print exactly that for the `wait: false` triggers (ScanToPdfServer #20, MyDownloadsClient #68). The counts are consistent: 3 + 17 + 7 = 27 assigned, matching the Done record, the P11–P13b sections and the ledger.

## F1 — Minor · advisory · anchor: none · confidence: high

**Close-out N4 says scantopdf-prd and media-prd restart once, but the schedule restarts each of them twice.**

N4's Consequence line (close-out.md, N4) says "scantopdf-prd, media-prd and FieldnotesApp's app restart once on unchanged code during P12a–b". The plan pushes two carriers into each of those deploy repos, in separate batches on purpose:
- ScanToPdfServer (P12a batch 2, plan.md:762-763) and ScanToPdfClient (P12b batch 1, plan.md:787-788) each start a `ScanToPdf/ScanToPdf` build.
- MyDownloadsServer (P12a batch 3, plan.md:769-770) and MyDownloadsClient (P12b step 3, plan.md:792-794) each start a `MyDownloads/MyDownloads` build.

Each of those builds tags its image `:${currentBuild.number}` and pins it without a guard, so each app rolls twice. The operator judges D1's trade-off from this line, and it undercounts the restarts. Nothing in the sweep's own gating depends on the count, so this is advisory.
