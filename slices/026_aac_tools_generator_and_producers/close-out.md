# Close-out — slice 026 aac_tools_generator_and_producers

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Close ANS-85 as won't-do (Ruling D2)

Ruling D2 rules the app-name equality check out of this slice and closes its card as won't-do; the Argo CD runbook's warning stays (docs/runbooks/argocd.md:330-334). No role in the run touches the tracker.

**Consequence:** ANS-85 stays open in the backlog as an unscheduled ask the operator has already decided against.

**Provenance:** read | plan-writer, planning, r1 — plan.md Ruling D2
**Disposition:**

### A2 — Settle V02 after the next KubeCoder promotion of KubeCoderDeploy main to prd (operator; …

V02 — The published architecture shows kube-coder-tunnel-reclaim mapped, with no gap line and no duplicate kubecoder.home service. KubeCoderDeploy's AaC build publishes from its `prd` branch, and this slice lands the mapping on `main` only.

`verification.json` marks V02 owed after: the next KubeCoder promotion of KubeCoderDeploy main to prd (operator; not done by this slice). The run cannot take that action; settle the criterion once it has happened.

executor P9b r1, 2026-09-29 — KubeCoderDeploy main now carries the mapping on origin: P9b pushed `c776662` (P5's `e9a5ca7` plus the --help pointer). The push started no AaC/KubeCoderDeploy build: the job polls `*/prd`, and its last build is still #10. A prd generation from that main prints no `gap:` line. The promotion is the only step left.

**Consequence:** V02 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A3 — Settle V09 after the operator's restart of the Architecture KubeCoder environment and …

V09 — A central architecture update session on a deploy repo runs `gen-architecture --help` from the Architecture environment's aac-tools toolchain as the judgment layer's schema.

`verification.json` marks V09 owed after: the operator's restart of the Architecture KubeCoder environment and the release of central update runs (ARCH-14). The run cannot take that action; settle the criterion once it has happened.

**Consequence:** V09 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A4 — Restart KitchenDisplay's KubeCoder environment so its lint gate finds the aac-tools sidecar (operator)

P11 moved KitchenDisplay's `lint` gate from `./scripts/arch-validate.py` to `cexec aac-tools arch-validate docs/architecture/*.yaml` and declared `- use: aac-tools` in its `.kubecoder/config.yaml` (KitchenDisplay `067308b`, pushed). A running environment picks the new toolchain up only on restart, and the restart is the operator's (push-sweep attachment § Migrating a carrier). DockerImages' and KubeCoder's gates need no restart: DockerImages' gate is guarded and runs in the Ansible environment, which declares aac-tools, and KubeCoder's config already declared it.

**Consequence:** Until that environment restarts, `kc project lint` in it fails at the first statement, because `cexec aac-tools` finds no sidecar.

**Provenance:** witnessed: executor, P11, r1, KitchenDisplay 067308b
**Disposition:**

### A5 — Restart the Ginbov, NewsFilter, Webathome, ScanToPdf and MyDownloads KubeCoder environments so their lint gates find the aac-tools sidecar (operator)

P12a moved the `lint` gate of Ginbov, NewsFilter, Webathome, ScanToPdfServer and MyDownloadsServer from `./scripts/arch-validate.py` to `cexec aac-tools arch-validate docs/architecture/*.yaml`, and declared `- use: aac-tools` in the environment each gate runs in. For Ginbov, NewsFilter and Webathome that is their own `.kubecoder/config.yaml`. ScanToPdfServer and MyDownloadsServer have no environment of their own. They are worked in the environments of the ScanToPdf and MyDownloads packager repos, whose `.kubecoder/config.yaml` gains the declaration (ScanToPdf `def421e`, MyDownloads `7a66719`). That also covers ScanToPdfClient's and MyDownloadsClient's gates, which move in P12b. A running environment picks up a new toolchain only on restart, and the restart is the operator's (push-sweep attachment § Migrating a carrier). GitblitMCPServer's environment already declared aac-tools, and GitblitMCPSupportPlugin is worked in it. YouTrackMCPServer's gates never ran the script.

**Consequence:** Until each environment restarts, `kc project lint` in it fails at the arch-validate step, because `cexec aac-tools` finds no sidecar.

**Provenance:** witnessed: executor, P12a, r1, sweep_ledger.md P12a rows
**Disposition:**

### A6 — Restart the IntercomServer and SSEGateway KubeCoder environments so their lint gates find the aac-tools sidecar (operator)

P12b moved the `lint` gate of IntercomServer and SSEGateway from `./scripts/arch-validate.py` to `cexec aac-tools arch-validate docs/architecture/*.yaml`, and declared `- use: aac-tools` in each repo's own `.kubecoder/config.yaml`. No other environment config in the estate clones either repo (gitblit search of `.kubecoder/config.yaml`). A running environment picks up a new toolchain only on restart, and the restart is the operator's (push-sweep attachment § Migrating a carrier). ScanToPdfClient's and MyDownloadsClient's gates run in the ScanToPdf and MyDownloads environments, which A5 covers. FieldnotesApp and DHCPApp had no local gate that ran the script, and their environments already declared aac-tools.

**Consequence:** Until each environment restarts, `kc project lint` in it fails at the arch-validate step, because `cexec aac-tools` finds no sidecar.

**Provenance:** witnessed: executor, P12b, r1, sweep_ledger.md P12b rows
**Disposition:**

### A7 — Restart the ElectronicsInventory KubeCoder environment so its lint gates find the aac-tools sidecar (operator)

P12c moved both components' `lint` gate in ElectronicsInventory from `../scripts/arch-validate.py` to `cexec aac-tools arch-validate docs/architecture/*.yaml`, and declared `- use: aac-tools` in the repo's own `.kubecoder/config.yaml`. A running environment picks up a new toolchain only on restart, and the restart is the operator's (push-sweep attachment § Migrating a carrier). ZigbeeControl had no local gate that ran its copies, so its environment config is unchanged.

**Consequence:** Until the environment restarts, `kc project lint --project backend|frontend` in it fails at the arch-validate step, because `cexec aac-tools` finds no sidecar.

**Provenance:** witnessed: executor, P12c, r1, sweep_ledger.md P12c rows
**Disposition:**

### A8 — Restart the InfraStatisticsDisplay, GestureDevice, UnderfloorHeatingController and DoorbellReceiver KubeCoder environments so their lint gates find the aac-tools sidecar (operator)

P13a moved each of these four firmware repos' `lint` gate from `./scripts/arch-validate.py docs/architecture/*.yaml` to `cexec aac-tools arch-validate docs/architecture/*.yaml`, and declared `- use: aac-tools` in each repo's own `.kubecoder/config.yaml`. A running environment picks up a new toolchain only on restart, and the restart is the operator's (push-sweep attachment § Migrating a carrier).

**Consequence:** Until each environment restarts, `kc project lint` in it fails at the arch-validate step, because `cexec aac-tools` finds no sidecar.

**Provenance:** witnessed: executor, P13a, r1, sweep_ledger.md P13a rows
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — R1's generator fix also removes a duplicate service from five other deploy repos' published models

The same bug R1 names for KubeCoder (a pod with two in-house apps each realizing a service makes gen-architecture mint a duplicate service for the host) already hit five other producers. With the fix, each drops its minted svc:<ns>-<service> and its Realization, and the host's interface is assigned to the routed container's own in-house service instead: electronics-inventory-deploy (parts.ginbov.nl -> svc:electronics-inventory-ui-web), fieldnotes-deploy (fieldnotes.home/fieldnotes -> svc:fieldnotes-ui-web; fieldnotes-hooks.webathome.org -> svc:webhook-relay), iot-deploy (iot.ginbov.nl -> svc:iotsupport-ui-web), scantopdf-deploy (scantopdf.home -> svc:scantopdf-api), zigbee2mqtt-deploy (z2m.webathome.org -> svc:zigbee-control-ui-web). They land on each repo's next AaC build after aac-tools is published.

code-writer P1 r1, 2026-09-29 — Checked 2026-09-29: in the live dataset each of the six minted svc: ids appears only in its own producer's element, Realization and Assignment(s), and no file in /work/Architecture names one, so nothing dangles today; the consequence is limited to the ids disappearing.

code-reviewer P1 r1, 2026-09-29 — Checked 2026-09-29: the five dropped ids (svc:electronics-inventory-prd-electronics-inventory, svc:fieldnotes-prd-fieldnotes, svc:fieldnotes-prd-fieldnotes-hooks, svc:iot-prd-iotsupport, svc:scantopdf-prd-scantopdf, svc:zigbee2mqtt-prd-zigbee-control) appear in the live dataset only in their own producer's Assignment and Realization relations. No file in /work/Architecture or /work/DockerImages references them, so nothing hand-authored dangles.

**Consequence:** The published model loses five minted per-deployment services and their UUIDs; anything hand-authored elsewhere that references one of those svc: ids now dangles.

**Provenance:** witnessed, code-writer, P1, r1, old-vs-new generation of the 26 deploy repos with in-house images (/work/scratch/p1-cmp/out)
**Disposition:**

### N2 — Run paused for an operator question in P4

The question, as the driver recorded it:

> Planned stop (Rulings D3, F3): ArgoCDTools main eadf4ca (P1–P3) is published, and IaC/ArgoCDTools #20 built it green, so registry:5000/aac-tools:20 and :latest carry the new generator. The how-to diff is committed (Ansible 5ef7adc on phase/026-P4, gate green) and so is the done-record. Please restart this environment (kc env restart) to bring the published aac-tools sidecar and modern-app together, then relaunch the run; the relaunched round only confirms and hands back done.

Stopped 2026-09-29 21:15; resumed 2026-09-29 21:24.

**Consequence:** none the loop acts on — the answer was in before the run resumed where it paused; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:**

### N3 — KitchenDisplay moved from the device class to P11: its Jenkins deploy job is disabled

The Grounding classed KitchenDisplay as restarting a Raspberry Pi service on every push. Jenkins reports Firmware/KitchenDisplay as disabled (buildable false). Its last eight builds (#64–#71, to 2026-06-06) failed at 'Deploy kitchendisplay': the job checks out HelmCharts for assets/kubernetes-pipeline-key, and the file is not there. HelmCharts is now archived. A push therefore starts only AaC/KitchenDisplay, and P10 put it in P11, the no-rollout class. P11 checks that the job is still disabled right before the push. If it has been enabled, P11 moves KitchenDisplay to the end of P13b.

**Consequence:** The Pi restart Ruling D1 accepted for KitchenDisplay does not happen. KitchenDisplay has no working Jenkins deploy: re-enabling the job as it stands fails at the same missing HelmCharts key.

**Provenance:** witnessed | code-writer, P10, r1 — Jenkins Firmware/KitchenDisplay api/json and #71 console
**Disposition:**

### N4 — The prd class grows to seventeen carriers: four the Grounding classed as no rollout redeploy prd through a job their push starts

ScanToPdfServer, ScanToPdfClient, MyDownloadsServer and MyDownloadsClient build no image themselves. But each Jenkinsfile runs `build job:` (`wait: false`) on `ScanToPdf/ScanToPdf` or `MyDownloads/MyDownloads`, and MyDownloadsClient also on `Webathome`. Each of those runs kaniko and pins, with no guard, into ScantopdfDeploy, MediaDeploy or WebathomeOrgDeploy. The `scantopdf-prd`, `media-prd` and `webathome-org-prd` Applications auto-sync. Jenkins records the chain on real pushes: ScanToPdf #33 and #34, MyDownloads #98 and #100, and Webathome #236 and #238 were started by these carriers. The four moved from P11 to P12a–b and now go through the prd health gate. Ruling D1's trade-off named twelve prd apps. With FieldnotesApp (P10 r1), the sweep also restarts scantopdf and media.

code-reviewer, P10, r2, 2026-09-30 — Correction: scantopdf-prd and media-prd each restart twice, not once. ScanToPdfServer (P12a) and ScanToPdfClient (P12b) each start a ScanToPdf build that pins ScantopdfDeploy. MyDownloadsServer (P12a) and MyDownloadsClient (P12b) each start a MyDownloads build that pins MediaDeploy. (phases/P10/code_review_r2.md F1)

**Consequence:** scantopdf-prd, media-prd and FieldnotesApp's app restart once on unchanged code during P12a–b, on top of the twelve production apps Ruling D1's trade-off named.

**Provenance:** witnessed, code-writer, P10, fix round r2, Jenkins build causes and the GitHub Jenkinsfiles (phases/P10/code_review_r1.md F1)
**Disposition:**

### N5 — KubeCoder was pushed without KubeCoder's devlock, which this environment cannot reach

KubeCoder's deploy-operations.md says a hand-driven push that rolls `kubecoder@dev` takes the devlock first. The lease is a flock on the shared KubeCoderSpecs mount (`scripts/devlock.sh`), and this environment has only a scratch clone of KubeCoderSpecs, whose lock file is a different inode. P11 pushed under Ruling D1 after checking proxies instead: the last `KubeCoder/Build-Main` build was #557 on 2026-09-28 19:29 UTC, no build was running, and KubeCoderSpecs' latest commit (2026-09-28 21:28 +0200) closes out slice 236, with no slice in a test or doc phase on origin. The push rebased onto origin/main, so the image it built is a superset of what dev ran.

**Consequence:** none, if no KubeCoder session was validating on dev at the time. Otherwise that session saw its dev pods roll once on unchanged code.

**Provenance:** witnessed: executor, P11, r1, /work/scratch/p9-sweep/logs/carrier-KubeCoder.log
**Disposition:**

### N6 — P12a pushed the ScanToPdf and MyDownloads packager repos, which no phase listed, for one environment config line each

ScanToPdfServer, ScanToPdfClient, MyDownloadsServer and MyDownloadsClient carry no `.kubecoder/config.yaml`. Each is worked in the environment of its packager repo (ScanToPdf or MyDownloads), whose config clones it. Their `lint` gates now run `cexec aac-tools arch-validate`, so the attachment's § Migrating a carrier gives those two environments the aac-tools declaration: ScanToPdf `def421e` and MyDownloads `7a66719`, config only. Ruling D1 authorises pushing every repo the sweep touches, but a packager push runs its job, `ScanToPdf/ScanToPdf` or `MyDownloads/MyDownloads`, with no guard. That job rebuilds the image and pins it. P12a pushed each packager in a batch apart from the carrier that pins the same deploy repo. ScanToPdf #38 pinned ScantopdfDeploy `45f0087`, and MyDownloads #105 pinned MediaDeploy `17171dc`. scantopdf-prd and media-prd were Synced and Healthy at each pin. Neither packager has an `AaC/` job. P12b's clients use the same two environments and leave the packagers alone.

**Consequence:** scantopdf-prd and media-prd each restart once more on unchanged code: three times across P12a–b, where N4's correction counted two.

**Provenance:** witnessed: executor, P12a, r1, sweep_ledger.md rows ScanToPdf and MyDownloads
**Disposition:**

### N7 — Run paused for an operator question in P12b

The question, as the driver recorded it:

> D1 stop rule: FieldnotesApp #40, the build of the pushed head 1ee1929, is red. One of 347 tests failed, backend test_board_sync::test_syncs_and_deliveries_are_counted (board_syncs_total{changed} read 1.0, expected 2). It is a race between the observation write and the counter increment, in code the migration does not touch (close-out B3). The build stopped before kaniko: no image, no pin, and fieldnotes-prd stays Healthy at 45bf980. AaC/FieldnotesApp #5 is green on the head. IntercomServer, DHCPApp and ScanToPdfClient are pushed and done. SSEGateway (41cf1b5) and MyDownloadsClient (fc6c74b) a…

Stopped 2026-09-30 01:34; resumed 2026-09-30 08:29.

**Consequence:** none the loop acts on — the answer was in before the run resumed where it paused; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:**

### N8 — Ruling D5's FieldnotesApp rebuild did not run: an operator push had already built the migrated code green

Ruling D5 said to rebuild FieldnotesApp once on 1ee1929 after #40 went red. When P12b resumed, FieldnotesApp's main was at 97777d7 (FN-18, 2026-09-30 03:05), a descendant of 1ee1929 that no phase of this slice made. FieldnotesApp #41 had built it green and pinned FieldnotesDeploy b7daf6f, and fieldnotes-prd was Synced/Healthy there. AaC/FieldnotesApp #6 was green on it and ran arch-validate in the aac-tools container. A rebuild of the job builds main's head, so it would only have restarted fieldnotes-prd again on the same code. The run counted #41 as D5's green build and went on to SSEGateway.

**Consequence:** none — fieldnotes-prd runs an image built from a head that carries the migration; the B3 race is unchanged and can still redden a later FieldnotesApp build

**Provenance:** witnessed, code-writer, P12b r2, sweep_ledger.md FieldnotesApp row
**Disposition:**

### N9 — Run paused for an operator question in P12c

The question, as the driver recorded it:

> D1 stop rule at IoTSupport: AaC/IoTSupport is still red at #41, its last build (last green #37), failing in IoTSupport's own generator with `ERROR: firmware product UUID 3e684732-6621-4297-926f-a4d9f82c538e not found in the published dataset` (the archived SomfyRemote's somfy_remote firmware product, still used by registered device somfy-remote-fhwiwoxa; close-out B2), and no ruling settles it, so IoTSupport is neither migrated nor pushed. ElectronicsInventory 55fb7b7 and ZigbeeControl e6c9f76 are pushed and done: app builds #256/#61 green, both prd apps Synced/Healthy at their new pins, AaC…

Stopped 2026-09-30 09:23; resumed 2026-09-30 09:27.

**Consequence:** none the loop acts on — the answer was in before the run resumed where it paused; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — Jenkins AaC/Architecture and AaC/WebathomeOrgDeploy trigger each other in an endless loop, redeploying the architecture site every ~6 minutes · major

AaC/Architecture pins the new site image into WebathomeOrgDeploy. The push of that pin starts AaC/WebathomeOrgDeploy ("Started by GitHub push"), and that job starts AaC/Architecture downstream, which pins again. Nothing else is needed to keep it going. On 2026-09-25, every one of the last 12 AaC/Architecture builds (#1861-#1872, 08:31-09:35) was "Started by upstream project AaC/WebathomeOrgDeploy". AaC/WebathomeOrgDeploy #354-#358 built exactly the pin commits (`ci: image pins from AaC/Architecture #1868`…`#1872`). WebathomeOrgDeploy's origin/main gained 161 commits since 2026-09-24. The triage-2026-09-24 handover (ANS-111) attributes the 5-9-minute rollouts to the 79 producers publishing. The self-trigger means they would continue with no producer activity at all, and ANS-111's RollingUpdate fix removes the outage but not the loop. The plan works around it: the push sweep rebases WebathomeOrgDeploy immediately before pushing (attachments/push-sweep.md).

code-writer, P9c r1, 2026-09-29 — Already fixed outside this slice: Architecture a2dabd2 (2026-09-26, ANS-136) marks WebathomeOrgDeploy trigger: false, so AaC/WebathomeOrgDeploy no longer starts AaC/Architecture. On 2026-09-29, pin pushes started AaC/WebathomeOrgDeploy #563-#567, each green. None of AaC/Architecture #2214-#2263, the job's whole retained history, was started by WebathomeOrgDeploy. WebathomeOrgDeploy now gains one pin commit per collector run, not one every ~6 minutes.

**Consequence:** Jenkins runs two builds every ~6 minutes forever, the architecture site's pod is replaced each time (35-45 s with no pod until ANS-111's fix lands), and WebathomeOrgDeploy gains ~200 pin commits a day.

**Provenance:** witnessed | plan-writer, planning, r1 — Jenkins API build causes for AaC/Architecture and AaC/WebathomeOrgDeploy, and WebathomeOrgDeploy git log, 2026-09-25
**Disposition:**

### B2 — IoTSupport: AaC/IoTSupport has been red since 2026-09-24, because its generator cannot map the archived SomfyRemote's firmware product · major

AaC/IoTSupport #38–#41 (2026-09-24 to 2026-09-26, each started by a GitHub push) fail in IoTSupport's own tools/gen-architecture.py with 'ERROR: firmware product UUID 3e684732-6621-4297-926f-a4d9f82c538e not found in the published dataset'. The last green build is #37 (2026-09-21). In backend/docs/architecture/firmware-products.yaml that UUID is somfy_remote, the product SomfyRemote published. SomfyRemote is archived and its product is no longer in the dataset, but IoTSupport still registers a device of that model: the published dataset still carries IoTSupport's #37 artifact, with device:somfy-remote-fhwiwoxa and a Specialization to ss:somfy-remote,3e684732-…. The generator fails on any registered model it cannot map, so dropping the mapping line alone swaps one error for another. Remedy options: retire the somfy-remote device (and its model) in the IoTSupport service, then drop the mapping line. Or keep SomfyRemote's product in the dataset some other way. P12c checks for a ruling or a later green AaC/IoTSupport build before it touches IoTSupport, and otherwise stops there with a question.

executor, P12c r2, 2026-09-30 — Resolved under Ruling D6: the operator deleted device fhwiwoxa and model somfy_remote in IoT Support (2026-09-30 07:25 UTC), the run dropped somfy_remote from firmware-products.yaml with IoTSupport's migration (c38bd6f), and AaC/IoTSupport #42 built that head green; AaC/Architecture #2314 published it.

**Consequence:** IoTSupport's published architecture stays frozen at its 2026-09-21 artifact. The sweep stops at IoTSupport, the last P12c carrier, so V12 cannot hold for it until the operator retires the device or rules otherwise.

**Provenance:** witnessed | code-writer, P10, r1 — Jenkins AaC/IoTSupport #41 console; sweep_ledger.md § Carriers
**Disposition:**

### B3 — FieldnotesApp: test_syncs_and_deliveries_are_counted scrapes the board-sync counter before the queued sync increments it · minor

FieldnotesApp #40 (P12b's push of `1ee1929`, 2026-09-30 01:19) failed in its suite on one of 347 tests: `backend/tests/fieldnotes/test_board_sync.py::test_syncs_and_deliveries_are_counted` asserted `fieldnotes_board_syncs_total{result="changed"} == 2` and read 1.0. The test waits with `eventually` for the observation's status to read `closed`, then scrapes. The queued sync runs on a `threading.Timer` in `ObservationService.sync_later`. `board_sync` (`backend/app/fieldnotes/observations.py:214-215`) commits the observation through `self.store.write(...)` first and increments `metrics.board_syncs` only after the write returns. So the test can see `closed` and scrape before the second `changed` is counted. The same job was green seven times on 2026-09-27/28 with the test unchanged (last touched in `e7891ed`). P12b's commit changes only `Jenkinsfile.architecture` and deletes `scripts/arch-validate.py`, which the suite does not read.

**Consequence:** FieldnotesApp builds fail at random on this test, and a red build ships no image. A retry on the same head is the only remedy today.

**Provenance:** witnessed: executor, P12b, r1, https://jenkins.webathome.org/job/FieldnotesApp/40/ (testReport, validation.log)
**Disposition:**

### B4 — IoTSupport: deleting a device model logs an SQLAlchemy row-count warning for firmware_versions · cosmetic

When the operator deleted the somfy_remote model (DELETE /api/device-models/4, 2026-09-30 07:25 UTC), iotsupport-app logged `app/services/device_model_service.py:211: SAWarning: DELETE statement on table 'firmware_versions' expected to delete 5 row(s); 0 were matched.` The model and its S3 objects were deleted and the request returned 204, so the rows were already gone when the ORM's own delete ran — two paths delete the same firmware_versions rows. Out of this slice's scope; not fixed.

**Consequence:** none today — the delete succeeds; the warning is noise in the backend log on every model deletion

**Provenance:** witnessed: executor, P12c, r2, kubectl logs iot-prd/iotsupport-598d6d6f5-gjlv7 -c iotsupport-app
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — App builds could skip rebuilding and pinning when a push changes no build input

Twelve app repos build and pin into an auto-synced deploy repo on every push (plan Grounding, R6). Only DockerImages, HelmCharts and KubeCoder carry a changeset guard, and no skip-ci convention exists. So a commit touching only Jenkinsfile.architecture, a README or scripts/ rebuilds the image and restarts the production app. This slice accepts that once per app (Ruling D1). A changeset guard in the shared build (or a skip rule for architecture-only paths) would let the next estate-wide sweep, or any doc commit, leave production alone. Out of this slice (plan: Not in scope).

**Consequence:** Every docs-only or architecture-only commit to one of these twelve app repos restarts its production app on a rebuilt image, and each device repo re-flashes its hardware.

**Provenance:** read | plan-writer, planning, r1 — plan.md Grounding (R6) and refinement.md D1
**Disposition:**

### S2 — The aac-tools catalog entry still tells agents to keep a repo's scripts/arch-validate.py copy

KubeCoderDeploy chart/values.yaml:594-596, the KubeCoder catalog description of the aac-tools toolchain, says: "A repo that also carries scripts/arch-validate.py needs that copy for its own Jenkins pipeline, which runs outside this image — leave it where it is." Once R6 has run, no active producer carries the copy and Jenkins runs arch-validate from containerTemplates.aac_tools, so the sentence describes a setup that no longer exists. The plan leaves it alone. The file is under chart/, so a push there rolls KubeCoder dev, and the catalog text reaches prd only through a promotion. Both are outside the deploy-repo sweep's no-rollout pushes.

**Consequence:** An agent that reads the environment's tool description is told to keep a copied validator, which the slice has just removed estate-wide, until someone edits the catalog entry and promotes KubeCoder.

**Provenance:** read | plan-writer, r3, KubeCoderDeploy chart/values.yaml:594-596 (also shown by kc env describe)
**Disposition:**

### S3 — aac-tools gen-architecture: confirm R1's front-door fallback, which keeps jenkins-mcp's and trello-mcp's hosts on the shared svc:mcp-filter

P1 reads R1 ("consider only the container behind the Service") with a fallback the executor settled, not the operator. When the routed container realizes no in-house service, the pod's single in-house service is referenced (gen_architecture.py:1302). Across the 26 in-house deploy repos it fires for four Services, all with the same output as before the phase. mydownloads (routed to gluetun) gets svc:mydownloads-api, which is right. jenkins-mcp, trello-mcp and trello-mcp-public (routed to the auth nginx) get svc:mcp-filter, although trello-mcp's pod also runs the upstream server ss:trello-mcp. Strict scoping would instead mint services realized by the proxy. An `exposures:` entry naming `server` would now mint a Trello MCP service realized by that container.

**Consequence:** The published model keeps assigning the Trello MCP and Jenkins MCP hosts to the one mcp-filter service every filter deployment shares, until someone rules on the reading or adds an exposures: entry.

**Provenance:** witnessed, code-reviewer, P1, r1, phases/P1/code_review_r1.md F2
**Disposition:**

### S4 — aac-tools gen-architecture: no test catches it if two parts of container scoping regress · minor

The suite still passes after either of two mutations. One makes the instance record carry the image-level realizes instead of the scoped one (gen_architecture.py:1035). The boundBy capability filter, the loopback pick and the secret-store match read that record, so a boundBy onto a container-scoped capability would then hard-fail. The other makes the scope gap compare against every rendered container instead of the image's own (:1096). Worth a test each. P6's layer relies on neither path.

**Consequence:** A later change could break a boundBy that resolves onto a container-scoped capability without any test failing. Nothing in the estate relies on that path today.

**Provenance:** witnessed, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### S5 — aac-tools gen-architecture: resolve_boundby's comment still calls the container env literal-valued · cosmetic

gen_architecture.py:1572-1573 says the value is expanded against the container's other literal-valued env. Since P2 that env also holds ConfigMap-sourced values (container_env).

**Consequence:** none

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F2
**Disposition:**

### S6 — aac-tools gen-architecture: the --help contract test does not notice when the image entry's served_by definition is removed · minor

HelpContractTests' key check (ArgoCDTools aac-tools/tests/test_gen_architecture.py:1492-1497) only requires each key to appear somewhere in --help. The JUDGMENT_KEYS section labels are subtest names, not the section searched. Deleting the served_by bullet from the image-entry keys (gen_architecture.py:133-136) leaves all three HelpContractTests green, because the cnpg paragraph still names served_by. The same holds for any key named in two paragraphs (product, realizes, upstream). The contract is complete at eadf4ca: this is only a regression guard. A check that looks for each key in its own paragraph would close it.

**Consequence:** A later docstring edit could drop served_by's (or realizes', product's) image-entry definition from --help without any test failing.

**Provenance:** witnessed | code-reviewer, P3, r1 — phases/P3/code_review_r1.md F1 (mutation run)
**Disposition:**

### S7 — aac-tools gen-architecture: --help says product entries are copied as written, but lifecycle and stereotype are overwritten · nit

The products paragraph of the contract (ArgoCDTools aac-tools/image/gen_architecture.py:163) says "The generator copies the fields as written". The code (:1026-1032) sets stereotype to SoftwareProduct and lifecycle to active whatever the entry says. lifecycle is a schema field (Architecture schema/v0.1/generated/systemsoftware.schema.yaml:30). No estate layer sets it today.

**Consequence:** A judgment layer that sets lifecycle on a product it owns, for example to retire it, publishes the product as active, with no gap and no error.

**Provenance:** read | code-reviewer, P3, r1 — phases/P3/code_review_r1.md F2
**Disposition:**

### S8 — P3's old-vs-new comparison harness regenerates KubeCoderDeploy from main, not the prd branch its architecture job publishes · nit

/work/scratch/p3-cmp/run.sh copies every deploy repo's origin/main. KubeCoderDeploy's Jenkinsfile.architecture clones branch prd, whose chart and values differ from main. The reviewer regenerated origin/prd e050439 with both generators: both exit 0, the artifacts are byte-identical, and the gap line is the same. So P3's conclusion holds. P4 redoes the comparison only if origin moves the generator. The plan's P3 Later phases now tells it to include prd.

**Consequence:** none — witnessed identical at eadf4ca; a P4 redo that skips prd would leave the published KubeCoderDeploy stage unchecked.

**Provenance:** witnessed | code-reviewer, P3, r1 — phases/P3/code_review_r1.md F3
**Disposition:**

### S9 — ArgoCDDeploy architecture.yaml: the argocd comment says an unset upstream var hard-fails on every other container of the image, but init containers are exempt · nit

architecture.yaml:25-26 says 'on any other container of the image an upstream wire whose var is unset is a hard fail'. The generator skips upstream on init containers (ArgoCDTools aac-tools/image/gen_architecture.py:1774, 'if not upstream or inst["is_init"]: continue'). An image-level REDIS_SERVER wire fails on applicationset-controller, notifications-controller and secret-init, and leaves the copyutil init container alone. The reason given for scoping the wire still holds; only 'any other container' is too broad. Could be narrowed to the image's non-init containers when P9a edits this file's header.

**Consequence:** none — a reader who follows the comment still writes a correct layer

**Provenance:** witnessed, code-reviewer, P6, r1, phases/P6/code_review_r1.md (F1)
**Disposition:**

### S10 — Deploy repos' architecture.yaml still name HelmCharts configs/prd/<app>/<stage>/release.yaml as the registry entry that pins the upstream chart version · nit

PrometheusDeploy's architecture.yaml:7-8 says the upstream chart version is the one 'this app's registry entry pins (HelmCharts configs/prd/<app>/<stage>/release.yaml): bump both'. HelmCharts was archived on 2026-09-28, and the pin now lives in ArgoCDDeploy releases/values.yaml (prometheus: stages.prd.version "29.33.0", line 210). The same HelmCharts wording appears in 9 more deploy repos' architecture.yaml (grep 'HelmCharts configs' over /work/scratch/sweep031/*/architecture.yaml). P7 left it alone because it is outside R5.

**Consequence:** A maintainer bumping an upstream chart version is sent to an archived repo for the second pin; the header does not name ArgoCDDeploy's releases/values.yaml, where the version actually is.

**Provenance:** witnessed, code-writer, P7, r1, /work/scratch/PrometheusDeploy/architecture.yaml
**Disposition:**

### S11 — P7's done-record cited the pre-amend PrometheusDeploy sha e761059; the branch head is 4aa1ef5 · nit

The executor amended its commit (reflog: 4aa1ef5 is 'commit (amend)' of e761059) after writing the done-record. The review corrected the sha in plan.md in place.

**Consequence:** none — plan.md now names 4aa1ef5

**Provenance:** witnessed, code-reviewer, P7, r1, phases/P7/code_review_r1.md
**Disposition:**

### S12 — Architecture update-architecture agent: the contract it reads from the sidecar's gen-architecture --help can be older than the generator the deploy repos build with · minor

update-architecture.md:49-50 has a central update session run `cexec aac-tools gen-architecture --help` for a deploy repo's contract, and says it is the contract of the generator the deploy repos build with. Jenkins pulls registry:5000/aac-tools untagged with alwaysPullImage on every AaC build (JenkinsPipelineUtils containerTemplates.groovy:34). The Architecture environment's sidecar carries whatever image its pod last started with, and the sessions run in that pod (tooling/fleet.py:827). So after an ArgoCDTools publication that changes the judgment-layer contract, the agent reads the older contract until the environment restarts. Idea: restart the Architecture environment as part of publishing a contract change, or have the fleet check the sidecar's image digest against registry latest before it runs sessions.

**Consequence:** After a future contract change, central update sessions edit deploy repos' judgment layers against the older contract until someone restarts the Architecture environment. A valid but incomplete edit passes the AaC build unnoticed.

**Provenance:** read, code-reviewer, P8, r1, phases/P8/code_review_r1.md F1
**Disposition:**

### S13 — Close-out B1 is still live, though P9c recorded its pin loop fixed by Architecture a2dabd2 (ANS-136) · nit

P9c noted B1 instead of striking it. Its note (and attachments/push-sweep.md:76-79) say Architecture a2dabd2 (2026-09-26) sets trigger: false on webathome-org-deploy, so AaC/WebathomeOrgDeploy no longer starts AaC/Architecture. No pin commit followed WebathomeOrgDeploy 6c83563 on origin/main. The list view shows B1's headline ('endless loop … · major') and its Consequence ('two builds every ~6 minutes forever'), not the note, and counts still counts it.

**Consequence:** The triage view presents a loop fixed on 2026-09-26 as the report's one open major bug.

**Provenance:** read | code-reviewer, P9c, r1 — phases/P9c/code_review_r1.md F1
**Disposition:**

### S14 — Close-out B2 is still live, though P12c r2 resolved it under Ruling D6 · nit

P12c r2 noted B2 resolved (the operator's device and model delete, c38bd6f, AaC/IoTSupport #42 green) but did not strike it. Its Consequence line still says the sweep stops at IoTSupport and that V12 cannot hold for it. The list view shows that line under B2's '· major' headline, not the note, and counts still counts it. close_out.py strike --reason is the tool's path for a resolved entry, as S13 records for B1.

**Consequence:** The triage view presents IoTSupport's red AaC build, green since #42, as an open major bug that stops the sweep.

**Provenance:** read | code-reviewer, P12c, r1 — phases/P12c/code_review_r1.md F1
**Disposition:**
