# Close-out — slice 029 helmcharts_decommission

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

### A1 — Settle V15 after the operator's registry switch, run from P6's runbook (including …

V15 — After the operator's switch, `releases` owns the 50 Applications. Each keeps its uid, creation timestamp and spec. No ApplicationSet remains. A registry push to ArgoCDDeploy refreshes `releases` through its webhook, and nothing polls.

`verification.json` marks V15 owed after: the operator's registry switch, run from P6's runbook (including ArgoCDDeploy's relay webhook). The run cannot take that action; settle the criterion once it has happened.

**Consequence:** V15 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A2 — Settle V24 after the operator's registry switch, run from P6's runbook through its last …

V24 — After the operator's registry switch, the last step of the switch runbook has run. No doc still says that a procedure is owed until the registry switch has run, and the procedures those notes carried now describe the registry Argo reads.

`verification.json` marks V24 owed after: the operator's registry switch, run from P6's runbook through its last step. The run cannot take that action; settle the criterion once it has happened.

**Consequence:** V24 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
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

### N1 — P3's pre-removal caller check found a live caller the plan's search missed: KitchenDisplay deploys with helmCharts.rsync and helmCharts.ssh

The plan said the library's scp, rsync and ssh helpers had zero callers in the org (GitHub code search, 2026-09-26). P3 re-ran the search before removing anything. KitchenDisplay's Jenkinsfile (main, last touched 69bd690, 2026-06-04; the repo was pushed 2026-09-13) clones HelmCharts into `HelmCharts/`, and its 'Deploy kitchendisplay' stage calls `helmCharts.ssh` twice (stop and start the systemd unit on 192.168.178.11) and `helmCharts.rsync` once (`bin/.` to `/var/local/kitchendisplay/bin`). Both helpers use `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key`. P3 removed only what has no caller: `cicd.helmDeploy()` and `helmCharts.scp` (JenkinsPipelineUtils phase/029-P3 6f87d09). It kept rsync and ssh, and returned a question to the operator.

**Consequence:** V21 as written (the library names no HelmCharts asset) cannot hold without breaking KitchenDisplay's deploy stage or widening the slice; P3 waits on the operator's ruling.

**Provenance:** witnessed | code-writer, P3, r1, gh search code 'helmCharts.rsync(' / 'helmCharts.ssh(' --owner pvginkel
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — ChartsDeploy: the chart that deploys charts.home takes homelab-shared from charts.home itself (D17's trap) · major

ChartsDeploy `chart/Chart.yaml` names `homelab-shared` 0.3.1 from `https://charts.home` as a dependency, and the repo vendors no tarball (`chart/` holds only `Chart.lock`, `Chart.yaml`, `templates/`, `values.yaml`; read with `gh api` 2026-09-26). Argo's repo-server has to fetch the library from charts.home to render the app that serves charts.home. argo-cd D17 names this trap and phases.md A.1 asked for a library-free chart; the move to ChartsDeploy did not keep it. Found while bringing argo-cd `design.md`'s charts.home paragraph current in P1, which now states it; not fixed here (out of scope).

**Consequence:** On a rebuilt cluster, or whenever charts.home is down, Argo cannot render charts.home, so it cannot bring it back, and every app that uses the library stays unrenderable until someone starts charts.home by hand.

**Provenance:** read — code-writer, P1, r1; gh api repos/pvginkel/ChartsDeploy (chart/Chart.yaml, tree)
**Disposition:**

### B2 — Architecture: the HA fleet's Zigbee bridge map still targets the pre-migration Z2M instance ids · minor

tools/ha-fleet/annotations.yaml's zigbee_bridges maps both bridges to ss:zigbee2mqtt-zigbee2mqtt1-zigbee2mqtt,30978e51-… and ss:zigbee2mqtt-zigbee2mqtt2-zigbee2mqtt,43ac1818-…, the ids HelmCharts' generator minted. zigbee2mqtt-deploy now publishes ss:zigbee2mqtt-prd-zigbee2mqtt1-zigbee2mqtt,3b3dcf7a-9bbc-5a29-9120-5e7d552e2d39 and ss:zigbee2mqtt-prd-zigbee2mqtt2-zigbee2mqtt,a2c8ea0b-84f7-5a8d-adc9-3c1f169df12e. The collector reports 66 dangling-reference warnings from home-automation-fleet, all of them these two ids, tolerated only by --relaxed. The fix is replacing the two ids. P2 left it alone: it is data, not the producer text P2 brought current.

**Consequence:** In the Home Assistant view, every Zigbee leaf's Serving edge to its Z2M instance dangles, and the collector cannot drop --relaxed while they remain.

**Provenance:** witnessed | code-writer, P2, r1, collector over AaC/Architecture #2048 producer-artifacts
**Disposition:**

### B3 — Architecture: the Infrastructure view lets in the deploy repos' 94 release instances · minor

views/infrastructure.yaml's excludeProducers is meant to keep release instances out (its comment until P2 named 'the helm-charts release instances'). Since the Argo migration, those instances are published by the *-deploy producers: 94 release-tagged SystemSoftware elements from 36 of them. The view's kinds predicate includes SystemSoftware, and nothing excludes these producers. P2 only dropped helm-charts, whose per-release output was already empty, so the view's contents did not change. Excluding them needs a rule that fits the view: 36 producer ids, or an instance gate that spares the env-tagged prd server Nodes.

**Consequence:** The Infrastructure view shows every deployed container next to the servers and network gear it was meant to show alone.

**Provenance:** witnessed | code-writer, P2, r1, merged dataset from the collector run
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

### S1 — ArgoCDDeploy's test gate reads HelmCharts' _providers/clusters.yaml, so it breaks once the HelmCharts clone is dropped

ArgoCDDeploy's `tests/render-chart.py:76` binds the hook environment's literals in `config/prd/values.yaml` to `../HelmCharts/_providers/clusters.yaml`, which it treats as the source of truth. This slice does not change that. The plan keeps HelmCharts cloned until the archive, and dropping the clone from `.kubecoder/config.yaml` belongs to the archive (ANS-122). Once the clone is gone, `kc project test` in ArgoCDDeploy fails on the missing file. Before the clone goes, the binding needs a new source of truth, most likely ArgoCDDeploy's own values, since the archived file will never change again.

**Consequence:** After ANS-122 drops the HelmCharts checkout, ArgoCDDeploy's gate fails on every run until the binding is changed.

**Provenance:** read — plan-writer, planning r1, tests/render-chart.py:76 and .kubecoder/config.yaml
**Disposition:**

### S2 — srviac's iac agent still clones HelmCharts and holds the HelmCharts deploy credentials

Ansible's `support/iac-agent/etc/iac/secrets.example.yaml` still describes things that only `IaC/HelmCharts` uses. Its `repos:` list clones HelmCharts on every iac run (:37-42), and its prd kubeconfig and homelab-provider storage credentials are marked for the HelmCharts deploy (:113, :158, :191). `support/iac-image/Dockerfile:55-63` and `support/iac-agent/bin/iac-impl:53` describe the HelmCharts deploy harness too. This slice's asks do not cover them. After ANS-121 deletes the job, they are dead weight on srviac. The credentials in particular are a standing grant that nothing uses. A follow-up could remove them from the agent's config and image, and the operator would converge srviac.

**Consequence:** srviac keeps cloning an archived repo on every iac run and keeps credentials that no job uses.

**Provenance:** read — plan-writer, planning r1, support/iac-agent/etc/iac/secrets.example.yaml
**Disposition:**

### S3 — One Helm release Secret remains on prd: argocd-prd's bootstrap install

The D61 pass removed every migrated app's Helm release Secret. A read on 2026-09-26 (secrets of type `helm.sh/release.v1`, names only) finds exactly one left: `sh.helm.release.v1.argocd-prd.v1` in `argocd-prd`, created 2026-09-04 by Argo's own bootstrap `helm install` (D3). Argo has managed that release ever since, but Helm still lists it as deployed. If someone runs `helm upgrade` or `helm uninstall` against it, Helm would act on Argo CD itself. It is not a migrated app's Secret, so D61 did not cover it, and this slice leaves it. Deleting it is the operator's call.

**Consequence:** `helm list -A` shows Argo CD as a Helm release, and a stray Helm command could act on it.

**Provenance:** witnessed — plan-writer, planning r1, kubectl get secrets --field-selector type=helm.sh/release.v1 (prd)
**Disposition:**

### S4 — After the registry switch, a follow-up removes what the switch leaves dead

The plan gates the hand-over behind one stage-level setting that the operator flips, so that every state of ArgoCDDeploy's `main` during the run is safe to sync. Once the switch is done, these are dead: the ApplicationSet branch and the setting in ArgoCDDeploy's chart; `releases.registry`, which points at HelmCharts; the render test's HelmCharts-registry assertions; HelmCharts' relay webhook; and the relay's applicationset-controller leg. Removing the chart parts changes nothing in the render. P6's runbook ends with this list (attachments/registry-switch.md, 'After the switch'). The slice cannot do the removal, because it has to wait for the operator's switch.

**Consequence:** Until the follow-up lands, ArgoCDDeploy carries a disabled ApplicationSet path next to the live registry, and a reader could take it for a live option.

**Provenance:** read — plan-writer, planning r1, plan.md P5/P6 and attachments/registry-switch.md
**Disposition:**

### S5 — AnsibleSpecs README.md still names HelmCharts as the workloads repo · nit

`/work/AnsibleSpecs/README.md` line 3: "Sister repos: [/work/Ansible](../Ansible) (code), [/work/HelmCharts](../HelmCharts) (workloads)." The workloads now deploy from per-app deploy repos, and ArgoCDDeploy holds the registry (argo-cd D63). P1's scope was the argo-cd records and the estate register, and P9's is Ansible's docs, so no phase touches this line.

**Consequence:** A session that reads AnsibleSpecs' README first is pointed at HelmCharts for workloads.

**Provenance:** read — code-writer, P1, r1
**Disposition:**

### S6 — The estate register links to seven slice and spec paths that have moved · cosmetic

In `/work/AnsibleSpecs/decisions.md`, relative links to `slices/runtime-secrets-sweep.md`, `slices/microceph-prod.md` (three times), `slices/internal-ha-vips.md`, `specs/dns-reservation-api.md` and `specs/dns-reservation-terraform.md` resolve to nothing. The files were moved under `slices/completed/` and other paths. These links predate this slice, and P1 found them while checking its own links.

code-writer P1 r1, 2026-09-26 — The targets now sit at `slices/completed/runtime-secrets-sweep.md`, `slices/completed/internal-ha-vips.md`, `change_requests/microceph_prod/microceph-prod.md` and `slices/completed/dns-reservation-provider/dns-reservation-{api,terraform}.md`.

**Consequence:** Those links in the doctrine every session reads first lead nowhere.

**Provenance:** witnessed — code-writer, P1, r1; a relative-link check over decisions.md
**Disposition:**

### S7 — The estate register's k8s-upgrade pin list still names HelmCharts' deploy tooling as a consumer to bump and redeploy · minor

AnsibleSpecs `decisions.md:279` lists "the Helm deploy tooling in `HelmCharts/tools/requirements.txt`" among the `kubernetes` Python client pins that a cluster upgrade must bump and redeploy first. After this slice HelmCharts deploys nothing (argo-cd `design.md:10`). P1 left the list as it is on purpose. ArgoCDTools does not use the client, so no live consumer is missing from the list.

**Consequence:** The next k8s upgrade run from the doctrine tries to commit a pin bump to HelmCharts, which is archived after ANS-122 and not to be added to before it (D43).

**Provenance:** read — code-reviewer, P1, r1; phases/P1/code_review_r1.md F1
**Disposition:**

### S8 — P6 carries AnsibleSpecs edits (the runbook path in D64 and phases.md) under Target: root · nit

P1 added `plan.md:406-411` to P6. It asks P6 to put the switch runbook's path into argo-cd `decisions.md` D64 and `phases.md`, both in AnsibleSpecs, but P6's `Target:` is `root`. The phase branch and its review cover one repo, so these edits sit outside both.

**Consequence:** P6's AnsibleSpecs edits can land on whatever AnsibleSpecs branch is checked out, unreviewed.

**Provenance:** read — code-reviewer, P1, r1; phases/P1/code_review_r1.md F2
**Disposition:**

### S9 — Architecture's prose docs still name HelmCharts as a producer or deploy path · nit

P2 brought current the comments, schema examples, the producer kit (.claude/) and the tool texts. The prose docs it left for a docs pass: README.md:5 and USAGE.md:7 list HelmCharts among the producers; README.md:216-217 says the Helm chart lives in pvginkel/HelmCharts (the Jenkinsfile pins into WebathomeOrgDeploy); docs/architecture-update.md:50 cites HelmCharts' gen_architecture.py as the gap-line example, and :115 names IaC/HelmCharts as the usual downstream build; docs/iotsupport-iot-architecture-guidance.md:149-150, :164 and :192 describe HelmCharts' image mapping and instances as current. The published summary of if:home-assistant-api (docs/architecture/home-automation.yaml:98) points at HelmCharts/charts/nginx/files/nginxmanager/external-services.yaml. P9 targets Ansible only, so no planned phase covers these.

**Consequence:** A reader of Architecture's README, USAGE or update docs, or of that published element, is sent to HelmCharts, which is archived after ANS-122.

**Provenance:** read | code-writer, P2, r1, grep of /work/Architecture at a4402f6
**Disposition:**

### S10 — Architecture's producer manual: the Ceph example no longer matches the 'service you own' rule it illustrates · nit

In .claude/architecture/producer-manual.md:825-830, the 'Re-provide via your own service layer' bullet says to Realize 'a new cluster-local TechnologyService **you** own'. After P2 its Ceph example says svc:cluster-ceph-rbd is 'declared in the Architecture repo's shared catalog', so the deploying repo does not own the service in the example.

**Consequence:** A producer that copies the example instead of the rule references a catalog service rather than declaring its own.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F2
**Disposition:**

### S11 — Intercom's dev-upload script takes the OTA signing key from a sibling HelmCharts checkout's assets/ · nit

Intercom `tools/dev-upload/upload.bat` (last changed d3c3f3c, 2025-04-19) mounts `%CD%/../HelmCharts/assets` into its uploader container and signs with `/workspace/keys/kubernetes-signing-key`. It is a developer-machine script, not a Jenkins caller, so it does not block ANS-121. After ANS-122 the key still lives only in the archived repo.

**Consequence:** A dev OTA upload of Intercom needs a HelmCharts clone for as long as the signing key lives only there; the archive leaves it readable, so nothing breaks.

**Provenance:** read | code-writer, P3, r1, gh search code 'HelmCharts/assets' --owner pvginkel
**Disposition:**
