# Close-out — slice 029 helmcharts_decommission

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-26 11:18 → 15:59 · 9 phases · 1 bail-out (1 operator question) · 1 test round · doc
phase done · $90.41 (planner 15 %, research 3 %, rework 4 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 029 clears the way for deleting HelmCharts' Jenkins jobs and archiving the repo. It shipped
an Argo CD native registry in ArgoCDDeploy (`releases/`: one values file rendered into one
Application per app-stage and validated by its schema, a `releases.owner` switch, and a read-only
equivalence check), the operator's registry-switch runbook with its rehearsal fixtures,
argo-migrate's flip and autosync against the new registry, recommend-resources in Ansible's
`support/` (one patch per deploy repo for the operator to delete or edit, then local commits),
the product catalog moved into Architecture with the `helm-charts` producer retired, and
JenkinsPipelineUtils without `helmDeploy()` or `scp`. The decision records (D63–D65) and the docs
in all five repos now describe deploy repos and the new registry. The switch itself is the
operator's step, and until it runs Argo still reads HelmCharts' `release.yaml` tree.

## Outstanding actions

Focus: run the registry switch from Ansible's `docs/runbooks/registry-switch.md` (A1, A2).
Until it runs, the new registry deploys nothing, and V15 and V24 stay open. Push AnsibleSpecs (A4).

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### ~~A1 — Settle V15 after the operator's registry switch, run from P6's runbook (including …~~ — settled: V15 verified after the registry switch ran 2026-09-28 (AnsibleSpecs e8a3b9f)

<details><summary>struck — body kept for the record</summary>

V15 — After the operator's switch, `releases` owns the 50 Applications. Each keeps its uid, creation timestamp and spec. No ApplicationSet remains. A registry push to ArgoCDDeploy refreshes `releases` through its webhook, and nothing polls.

`verification.json` marks V15 owed after: the operator's registry switch, run from P6's runbook (including ArgoCDDeploy's relay webhook). The run cannot take that action; settle the criterion once it has happened.

**Consequence:** V15 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:** Yes (the operator, 2026-09-28, to marking it done) — settled: the registry switch ran 2026-09-28; V15 verified in verification.json (AnsibleSpecs e8a3b9f)

</details>

### ~~A2 — Settle V24 after the operator's registry switch, run from P6's runbook through its last …~~ — settled: V24 verified after runbook step 11 ran 2026-09-28 (Ansible d424f8a, AnsibleSpecs 89fab16, e8a3b9f)

<details><summary>struck — body kept for the record</summary>

V24 — After the operator's registry switch, the last step of the switch runbook has run. No doc still says that a procedure is owed until the registry switch has run, and the procedures those notes carried now describe the registry Argo reads.

`verification.json` marks V24 owed after: the operator's registry switch, run from P6's runbook through its last step. The run cannot take that action; settle the criterion once it has happened.

**Consequence:** V24 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:** Yes (the operator, 2026-09-28, to marking it done) — settled: runbook step 11 ran 2026-09-28 (Ansible d424f8a, AnsibleSpecs 89fab16); V24 verified (e8a3b9f)

</details>

### ~~A3 — P8's proof run left 30 unpushed resource-request commits in /tmp/rr-proof on the dev container · nit~~ — closed by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

Step two of the proof ran against real clones: 30 deploy repos carry one local commit each on main, from the 2026-09-19..26 Prometheus window. NewsfilterDeploy's patch was deleted and GrafanaDeploy's memory hunk overruled (160Mi -> 192Mi) as a demonstration, so the commits are not a clean recommendation. /tmp is not durable. The operator can discard them and run 'python3 support/recommend-resources/recommend_resources.py report <dir>' fresh when they want the requests applied.

**Consequence:** None if discarded; the resource requests the live estate needs wait for the operator's own run of the tool.

**Provenance:** witnessed, executor, P8 r1
**Disposition:** Close.

</details>

### ~~A4 — AnsibleSpecs is not pushed: it is 37 commits ahead of origin, including slices 030 and 031's planning commits~~ — done: AnsibleSpecs pushed 2026-09-28

<details><summary>struck — body kept for the record</summary>

The test phase pushed Ansible (ca536a6), Architecture (d73109d), ArgoCDDeploy (4afb8fb) and JenkinsPipelineUtils (6f87d09), the repos in `state.json`'s `bases` that the driver's push check covers. It did not push AnsibleSpecs: the driver excludes the spec repo from that check, the working tree is shared, and the 37 unpushed commits include other slices' planning work (030, 031) that this slice does not own. Push it when the operator wants those records on origin: `cd /work/AnsibleSpecs && git push origin main`. The operator's call, not this slice's.

**Consequence:** The slice's records (decisions, runbook path, close-out, verification) exist only in this pod's /work/AnsibleSpecs until someone pushes; nothing else reads them from origin.

**Provenance:** witnessed, test-agent, phase test, round 1, git -C /work/AnsibleSpecs log origin/main..HEAD
**Disposition:** Yes (the operator, 2026-09-28, to marking it done) — AnsibleSpecs pushed 2026-09-28

</details>

## Notable events

Focus: one pause (N1, N2: KitchenDisplay still calls `helmCharts.rsync`/`ssh`, so they stay) and
one red build after a push, fixed (N5). Act on N4: two step-ca passphrases reached a transcript.

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### ~~N1 — P3's pre-removal caller check found a live caller the plan's search missed: KitchenDisplay deploys with helmCharts.rsync and helmCharts.ssh~~ — acknowledged by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

The plan said the library's scp, rsync and ssh helpers had zero callers in the org (GitHub code search, 2026-09-26). P3 re-ran the search before removing anything. KitchenDisplay's Jenkinsfile (main, last touched 69bd690, 2026-06-04; the repo was pushed 2026-09-13) clones HelmCharts into `HelmCharts/`, and its 'Deploy kitchendisplay' stage calls `helmCharts.ssh` twice (stop and start the systemd unit on 192.168.178.11) and `helmCharts.rsync` once (`bin/.` to `/var/local/kitchendisplay/bin`). Both helpers use `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key`. P3 removed only what has no caller: `cicd.helmDeploy()` and `helmCharts.scp` (JenkinsPipelineUtils phase/029-P3 6f87d09). It kept rsync and ssh, and returned a question to the operator.

consult 1, 2026-09-26 — Ruled before the run resumed (N2): keep rsync and ssh as they are, with follow-up ANS-144 to move KitchenDisplay's key to a Jenkins SSH credential. V21 was amended to match and P3 merged. The Consequence line above describes the state before the ruling.

**Consequence:** V21 as written (the library names no HelmCharts asset) cannot hold without breaking KitchenDisplay's deploy stage or widening the slice; P3 waits on the operator's ruling.

**Provenance:** witnessed | code-writer, P3, r1, gh search code 'helmCharts.rsync(' / 'helmCharts.ssh(' --owner pvginkel
**Disposition:** Ok

</details>

### ~~N2 — Run paused for an operator question in P3~~ — acknowledged by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

The question, as the driver recorded it:

> The pre-removal code search found a live caller: KitchenDisplay's Jenkinsfile (main) clones HelmCharts and deploys with helmCharts.ssh (x2) and helmCharts.rsync, both using $WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key. So far only cicd.helmDeploy() and helmCharts.scp are removed, since neither has a caller (JenkinsPipelineUtils phase/029-P3 6f87d09, gate green); rsync and ssh are kept. Operator: (a) keep rsync/ssh as they are, amending V21 so the library still names HelmCharts' assets and KitchenDisplay keeps cloning the archived repo for its key; (b) move the key to a Jenkins SSH cre…

Stopped 2026-09-26 12:07; resumed 2026-09-26 12:10.

**Consequence:** none the loop acts on — the answer was in before the run resumed where it paused; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:** Ok

</details>

### ~~N3 — P9 dropped argocd.md's producer handover steps (the handover proof and the flip) instead of giving the flip an owed note · nit~~ — acknowledged by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

The docs-across-the-switch ruling, the plan's P9 text and V18 name three procedures that carry an owed note: registering an app, the handover flip (argocd.md, 'Giving an app its own architecture producer', step 6) and the cold-boot bootstrap. The handover flip was the step where a migrating app's stage left HelmCharts' helm-charts producer and its own producer took the ids over. No handover remains: every live app is migrated, the three parked apps' release.yaml files say disabled: true, and P2 retires the helm-charts producer. So P9 removed the handover steps (the handover_equality proof and the flip) and the flip's ordering rules, and stated the handover in the past tense. Registering an app and the cold-boot bootstrap carry their notes, and so do the Facts table's registry rows, 'Diagnosing a failed sync' item 4 and 'Upgrading Argo CD' step 2. argo_migrate.py's flip keeps P7's own owed note.

**Consequence:** V18's check for a note on 'the handover flip' finds no such step in argocd.md; the procedure it named is gone, not left un-noted.

**Provenance:** witnessed, code-writer, P9, r1, docs/runbooks/argocd.md
**Disposition:**  Ok

</details>

### ~~N4 — P9's read of StepCaDeploy's stage-manifests.yaml printed two step-ca passphrases (base64) into the session transcript · minor~~ — acknowledged by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

To rewrite step-ca-bootstrap.md's Secret layout, P9 grepped StepCaDeploy's chart/templates/stage-manifests.yaml for kind, name and key lines. The pattern also matched the data lines, so the base64 values of step-ca-ca-password's and step-ca-ssh-host-ca-password's password keys (and the encrypted intermediate and SSH host CA keys) reached the transcript. Nothing decoded or used them. The values are committed in that private repo, a known state that AnsibleSpecs decisions.md ('Intermediate key + passphrase') tracks moving into ansible-vault.

code-reviewer P9 r1, 2026-09-26 — The review repeated it: a grep of StepCaDeploy's stage-manifests.yaml for Secret names and keys matched the data lines, and the same base64 values reached the reviewer's transcript. They are the same values N4 already names, so the consequence does not change.

**Consequence:** The step-ca intermediate key passphrase and the SSH host CA key passphrase are transcript-exposed. Under the estate's rotated_at convention, that is a reason to rotate them when the Secrets move out of the chart.

**Provenance:** witnessed, code-writer, P9, r1
**Disposition:** Ok

</details>

### ~~N5 — The push to Architecture's main turned its CI build red: P2's Infrastructure-view test reads repo files the Docker build-viewer stage did not carry; fixed and redeployed · minor~~ — acknowledged by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

The test phase pushed Architecture d7c4878 (P2). Jenkins AaC/Architecture #2068 failed in the Dockerfile's `build-viewer` stage: `viewer/src/views/infrastructure-view.test.ts` (added in P2's review r1) reads `docs/architecture/catalog.yaml`, `docs/architecture/infrastructure.yaml` and `views/infrastructure.yaml` through `../../../` from `src/views/`. Locally that is the repo root, so `kc project test` (and the driver's sweep) passed. In the image build the stage copied only `viewer/` to `/app`, so the path resolved to `/` and the suite died with `ENOENT: /docs/architecture/catalog.yaml`. Mechanical repair by the test-fixer: stage 2 now lays out `/work/viewer` with `/work/docs/architecture/` and `/work/views/` beside it (the precedent stage 3 sets), and the final stage copies `/work/viewer/dist`. Reproduced and cleared with `kaniko --context /work/Architecture --no-push --target build-viewer`; pushed as d73109d; #2069 built d73109d, pushed the image and pinned WebathomeOrgDeploy c179e5a. The live dataset then dropped the helm-charts producer (825 unique elements, the 37 moved ids under `architecture`, the 3 unreferenced ones gone).

**Consequence:** none now; had it not been caught, no Architecture build would have produced an image or deployed the dataset without helm-charts

**Provenance:** witnessed, test-agent, phase test, round 1, Jenkins AaC/Architecture #2068 (log /tmp/track_build/AaC_Architecture_2068.log), #2069; Architecture d73109d
**Disposition:** Ok

</details>

### ~~N6 — IaC/Scheduled Drift #117 failed at 11:24Z on srvk8sdev (changed=2), before any of this slice's pushes · nit~~ — acknowledged by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

Looked at while reading Jenkins after the pushes. The build ran the pre-slice `main` (Ansible ca536a6 was pushed at 13:22Z, the build ran at 11:24Z), and the slice changes no role, playbook, inventory or Terraform (its only edits under `ansible/` are a comment and role READMEs). Terraform drift (prd), pve/wrkdev, and k8s prd ended `changed=0 failed=0`; `k8s dev` (srvk8sdev) ended `changed=2`, and the build finished FAILURE. Recorded so the operator sees it beside the pushes; the cause was not investigated further.

**Consequence:** The next scheduled drift run will show srvk8sdev's two changed tasks again until an operator converges it; this slice reaches no host.

**Provenance:** read, test-agent, phase test, round 1, Jenkins IaC/Scheduled Drift #117 console
**Disposition:** Ok

</details>

## Bugs

Focus: B1 first (major, read, ChartsDeploy): charts.home cannot come back on its own after a
rebuild. Then B5 and B4, witnessed, in this slice's recommend-resources. B2 and B3 are witnessed
in Architecture and predate the slice. Four of the five are witnessed.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B2 — Architecture: the HA fleet's Zigbee bridge map still targets the pre-migration Z2M instance ids · minor

tools/ha-fleet/annotations.yaml's zigbee_bridges maps both bridges to ss:zigbee2mqtt-zigbee2mqtt1-zigbee2mqtt,30978e51-… and ss:zigbee2mqtt-zigbee2mqtt2-zigbee2mqtt,43ac1818-…, the ids HelmCharts' generator minted. zigbee2mqtt-deploy now publishes ss:zigbee2mqtt-prd-zigbee2mqtt1-zigbee2mqtt,3b3dcf7a-9bbc-5a29-9120-5e7d552e2d39 and ss:zigbee2mqtt-prd-zigbee2mqtt2-zigbee2mqtt,a2c8ea0b-84f7-5a8d-adc9-3c1f169df12e. The collector reports 66 dangling-reference warnings from home-automation-fleet, all of them these two ids, tolerated only by --relaxed. The fix is replacing the two ids. P2 left it alone: it is data, not the producer text P2 brought current.

**Consequence:** In the Home Assistant view, every Zigbee leaf's Serving edge to its Z2M instance dangles, and the collector cannot drop --relaxed while they remain.

**Provenance:** witnessed | code-writer, P2, r1, collector over AaC/Architecture #2048 producer-artifacts
**Disposition:** Raise — ANS-159

### B6 — Ansible openbao role: the unconditional writes (Write AppRoles, Write the OIDC config, Write the OIDC admin role) always report ok · minor

ansible/roles/openbao/tasks/approle.yml and oidc.yml issue uri POSTs with no when and no changed_when, so they run on every pass and never report changed, whether or not the state differed. The six gated writes were fixed to report changed in Ansible c94ae95 after a run that rewrote the iac-agent policy recapped changed=0. Reporting these three honestly needs a read-and-compare first.

**Consequence:** A run that changes an AppRole's settings or the OIDC config shows changed=0, so neither the operator nor the drift job can see it happened.

**Provenance:** witnessed, the operator's session after the registry switch, 2026-09-28; Ansible c94ae95
**Disposition:** Please advise. — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested card — ANS-160

### ~~B1 — ChartsDeploy: the chart that deploys charts.home takes homelab-shared from charts.home itself (D17's trap) · major~~ — fixed in ChartsDeploy f46677b, RegistryDeploy 458ca4c; the rest carded as ANS-162

<details><summary>struck — body kept for the record</summary>

ChartsDeploy `chart/Chart.yaml` names `homelab-shared` 0.3.1 from `https://charts.home` as a dependency, and the repo vendors no tarball (`chart/` holds only `Chart.lock`, `Chart.yaml`, `templates/`, `values.yaml`; read with `gh api` 2026-09-26). Argo's repo-server has to fetch the library from charts.home to render the app that serves charts.home. argo-cd D17 names this trap and phases.md A.1 asked for a library-free chart; the move to ChartsDeploy did not keep it. Found while bringing argo-cd `design.md`'s charts.home paragraph current in P1, which now states it; not fixed here (out of scope).

**Consequence:** On a rebuilt cluster, or whenever charts.home is down, Argo cannot render charts.home, so it cannot bring it back, and every app that uses the library stays unrenderable until someone starts charts.home by hand.

**Provenance:** read — code-writer, P1, r1; gh api repos/pvginkel/ChartsDeploy (chart/Chart.yaml, tree)
**Disposition:** What do you propose as a solution? — on the advice (vendor the library tarball): "How do we ensure that the tarball is automatically updated? Does this need a pipeline change? If so, please create a card." — no pipeline change: the pin is exact and moves only on a deliberate commit, and tests/check-deps.sh fails a bump without its tarball. Done in ChartsDeploy f46677b and RegistryDeploy 458ca4c (Charts 3608684, AnsibleSpecs b3cb2fc for the docs); the rest of the cold-boot chain carded as ANS-162

</details>

### ~~B3 — Architecture: the Infrastructure view lets in the deploy repos' 94 release instances · minor~~ — fixed in Architecture 5538aed

<details><summary>struck — body kept for the record</summary>

views/infrastructure.yaml's excludeProducers is meant to keep release instances out (its comment until P2 named 'the helm-charts release instances'). Since the Argo migration, those instances are published by the *-deploy producers: 94 release-tagged SystemSoftware elements from 36 of them. The view's kinds predicate includes SystemSoftware, and nothing excludes these producers. P2 only dropped helm-charts, whose per-release output was already empty, so the view's contents did not change. Excluding them needs a rule that fits the view: 36 producer ids, or an instance gate that spares the env-tagged prd server Nodes.

**Consequence:** The Infrastructure view shows every deployed container next to the servers and network gear it was meant to show alone.

**Provenance:** witnessed | code-writer, P2, r1, merged dataset from the collector run
**Disposition:** Fix inline or raise. I'm looking at the view and it's a mess. It contains far too much, so you're right to raise this. — fixed inline: Architecture 5538aed (the view's predicate admits only the ansible and architecture producers; 185 → 77 elements on the live dataset)

</details>

### ~~B4 — Ansible recommend-resources: a Deployment pod whose ReplicaSet hash is under 8 characters is not matched to its workload · minor~~ — fixed in Ansible f3b40af

<details><summary>struck — body kept for the record</summary>

infer_workload's suffix pattern, carried over unchanged from HelmCharts' recommend_resources.py under the 'policy unchanged' rule, strips a Deployment pod's '-<hash>-<id>' only when the pod-template-hash is 8-10 characters. The hash is a variable-length encoding, and live pods carry shorter ones. In P8's live run on 2026-09-26, 'architecture-viewer-8cb446d-…' (webathome-org-prd) and 'keycloak-d8cb679-…' (keycloak-prd) resolved to workloads 'architecture-viewer-8cb446d' and 'keycloak-d8cb679', and landed in not-placed.txt instead of their chart's resources.<workload>.<container>. The pattern also makes an 8-10 character last word of a DaemonSet name read as a hash (prometheus-node-exporter -> prometheus-prd-prometheus-node); the maps' keys already rely on that, so a fix has to re-key them.

**Consequence:** Containers of a Deployment whose current ReplicaSet hash is short get no recommendation until a rollout happens to produce a longer hash.

**Provenance:** witnessed, executor, P8 r1, /tmp/rr-proof/not-placed.txt
**Disposition:** Please advise. — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested fix now — Ansible f3b40af

</details>

### ~~B5 — Ansible recommend-resources: requests are raised without regard to the container's limit · minor~~ — closed by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

revise() (support/recommend-resources/recommend_resources.py:496-515) reads and writes only `requests`, a policy carried verbatim from HelmCharts' tool. P8's proof patch for PrometheusDeploy already raises server.resources.requests.memory to 1536Mi, the same value as its limits.memory 1.5Gi. The next upward ratchet would put the request above the limit. The patch preamble does not show limits. Review F6.

**Consequence:** A future run can produce a values file whose request exceeds its limit. After the push, Argo's sync of that app fails on the API server's validation until someone edits the limit or the request by hand.

**Provenance:** witnessed, code-reviewer, P8, r1, phases/P8/code_review_r1.md F6
**Disposition:** Close

</details>

## Open questions and rulings

Focus: none are open. The one question the run needed, P3's (N1), was answered mid-run.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: the archive turns on S1, S2, S21 and S23, and each needs a decision first. S4 is the
follow-up after the switch. Witnessed: S3, S12, S14, S16, S19, S29. The doc phase settled S5, S7, S10,
S13, S14, S15 and S25, and most of S9, S20 and S22; the notes say what is left.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S23 — No deploy repo validates its render against prd's Kubernetes minor: HelmCharts' kubeconform gate has no successor · minor

k8s-upgrade.md's 'Move the HelmCharts chart gate to prd's new minor' set KUBE_VERSION in HelmCharts' Jenkinsfile, whose 'Gate releases' stage rendered every prd release and ran kubeconform against that minor's schemas. HelmCharts deploys nothing now, so P9 deleted the section. A read-only search on 2026-09-26 found no successor: no KUBE_VERSION, kubeconform or --kube-version in Charts, ArgoCDTools, JenkinsPipelineUtils or ArgoCDDeploy, and the deploy repos checked (StorageDeploy, IotDeploy, StepCaDeploy) carry only Jenkinsfile.architecture.

**Consequence:** A channel bump that removes an API version a deploy repo's chart still uses is caught only when Argo's sync of that app fails.

**Provenance:** read, code-writer, P9, r1, research subagent report (repo trees via gh api)
**Disposition:** Please advise — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested card (a pre-bump check on apiserver_requested_deprecated_apis) — ANS-161

### ~~S1 — ArgoCDDeploy's test gate reads HelmCharts' _providers/clusters.yaml, so it breaks once the HelmCharts clone is dropped~~ — fixed in ArgoCDDeploy fb35a6c

<details><summary>struck — body kept for the record</summary>

ArgoCDDeploy's `tests/render-chart.py:76` binds the hook environment's literals in `config/prd/values.yaml` to `../HelmCharts/_providers/clusters.yaml`, which it treats as the source of truth. This slice does not change that. The plan keeps HelmCharts cloned until the archive, and dropping the clone from `.kubecoder/config.yaml` belongs to the archive (ANS-122). Once the clone is gone, `kc project test` in ArgoCDDeploy fails on the missing file. Before the clone goes, the binding needs a new source of truth, most likely ArgoCDDeploy's own values, since the archived file will never change again.

**Consequence:** After ANS-122 drops the HelmCharts checkout, ArgoCDDeploy's gate fails on every run until the binding is changed.

**Provenance:** read — plan-writer, planning r1, tests/render-chart.py:76 and .kubecoder/config.yaml
**Disposition:** Yes (the operator, 2026-09-28, to marking it done) — fixed in ArgoCDDeploy fb35a6c: config/prd/values.yaml is the literals' source, the gate checks their shape; green with /work/HelmCharts removed

</details>

### ~~S2 — srviac's iac agent still clones HelmCharts and holds the HelmCharts deploy credentials~~ — done 2026-09-28: srviac secrets.yaml (operator), Ansible 35d9e3e, policy applied, kv/iac/kubeconfig-prd deleted

<details><summary>struck — body kept for the record</summary>

Ansible's `support/iac-agent/etc/iac/secrets.example.yaml` still describes things that only `IaC/HelmCharts` uses. Its `repos:` list clones HelmCharts on every iac run (:37-42), and its prd kubeconfig and homelab-provider storage credentials are marked for the HelmCharts deploy (:113, :158, :191). `support/iac-image/Dockerfile:55-63` and `support/iac-agent/bin/iac-impl:53` describe the HelmCharts deploy harness too. This slice's asks do not cover them. After ANS-121 deletes the job, they are dead weight on srviac. The credentials in particular are a standing grant that nothing uses. A follow-up could remove them from the agent's config and image, and the operator would converge srviac.

**Consequence:** srviac keeps cloning an archived repo on every iac run and keeps credentials that no job uses.

**Provenance:** read — plan-writer, planning r1, support/iac-agent/etc/iac/secrets.example.yaml
**Disposition:** Yes (the operator, 2026-09-28, to marking it done) — done: the operator cleaned srviac's /etc/iac/secrets.yaml; Ansible 35d9e3e (secrets.example, iac-agent policy, applied); kv/iac/kubeconfig-prd deleted

</details>

### ~~S3 — One Helm release Secret remains on prd: argocd-prd's bootstrap install~~ — done 2026-09-29: Secret deleted on prd; Ansible 4fb51c0

<details><summary>struck — body kept for the record</summary>

The D61 pass removed every migrated app's Helm release Secret. A read on 2026-09-26 (secrets of type `helm.sh/release.v1`, names only) finds exactly one left: `sh.helm.release.v1.argocd-prd.v1` in `argocd-prd`, created 2026-09-04 by Argo's own bootstrap `helm install` (D3). Argo has managed that release ever since, but Helm still lists it as deployed. If someone runs `helm upgrade` or `helm uninstall` against it, Helm would act on Argo CD itself. It is not a migrated app's Secret, so D61 did not cover it, and this slice leaves it. Deleting it is the operator's call.

**Consequence:** `helm list -A` shows Argo CD as a Helm release, and a stray Helm command could act on it.

**Provenance:** witnessed — plan-writer, planning r1, kubectl get secrets --field-selector type=helm.sh/release.v1 (prd)
**Disposition:** Please advise — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested delete + runbook step — deleted on prd 2026-09-29; argocd.md cold-boot step 7 in Ansible 4fb51c0

</details>

### ~~S4 — After the registry switch, a follow-up removes what the switch leaves dead~~ — done in ArgoCDDeploy 1d6da09, a811fa5, fb35a6c and Ansible 92ec266

<details><summary>struck — body kept for the record</summary>

The plan gates the hand-over behind one stage-level setting that the operator flips, so that every state of ArgoCDDeploy's `main` during the run is safe to sync. Once the switch is done, these are dead: the ApplicationSet branch and the setting in ArgoCDDeploy's chart; `releases.registry`, which points at HelmCharts; the render test's HelmCharts-registry assertions; HelmCharts' relay webhook; and the relay's applicationset-controller leg. Removing the chart parts changes nothing in the render. P6's runbook ends with this list (attachments/registry-switch.md, 'After the switch'). The slice cannot do the removal, because it has to wait for the operator's switch.

executor P5 r1, 2026-09-26 — P5 names the chart parts. The branch is chart/templates/applicationsets.yaml and the setting is releases.owner (chart/values.yaml, config/prd/values.yaml). The test parts are tests/render-chart.py's S1 position, check_applicationsets and the helpers it calls, and HelmCharts in REPOS and PERMITTED_SOURCES. releases.owner's validation in chart/templates/releases.yaml goes too. releases.autoSync stays, true from the switch. Jenkinsfile.architecture's header also names HelmCharts' configs/prd/argocd/prd/release.yaml as where Argo's branch is set; from the switch that is releases/values.yaml's apps.argocd.

**Consequence:** Until the follow-up lands, ArgoCDDeploy carries a disabled ApplicationSet path next to the live registry, and a reader could take it for a live option.

**Provenance:** read — plan-writer, planning r1, plan.md P5/P6 and attachments/registry-switch.md
**Disposition:** Yes (the operator, 2026-09-28, to marking it done) — done: ArgoCDDeploy 1d6da09, a811fa5, fb35a6c; Ansible 92ec266

</details>

### ~~S5 — AnsibleSpecs README.md still names HelmCharts as the workloads repo · nit~~ — fixed in AnsibleSpecs 91a4d96

<details><summary>struck — body kept for the record</summary>

`/work/AnsibleSpecs/README.md` line 3: "Sister repos: [/work/Ansible](../Ansible) (code), [/work/HelmCharts](../HelmCharts) (workloads)." The workloads now deploy from per-app deploy repos, and ArgoCDDeploy holds the registry (argo-cd D63). P1's scope was the argo-cd records and the estate register, and P9's is Ansible's docs, so no phase touches this line.

doc-writer, doc phase r1, 2026-09-26 — Addressed in AnsibleSpecs 91a4d96: the README's sister repos name Ansible and ArgoCDDeploy (Argo CD and its registry of the workloads, which deploy from per-app deploy repos).

**Consequence:** A session that reads AnsibleSpecs' README first is pointed at HelmCharts for workloads.

**Provenance:** read — code-writer, P1, r1
**Disposition:** Fix inline — already fixed in AnsibleSpecs 91a4d96

</details>

### ~~S6 — The estate register links to seven slice and spec paths that have moved · cosmetic~~ — resolved by consult 1 (AnsibleSpecs 150fb1a): the seven links in decisions.md point at slices/completed/, change_requests/microceph_prod/ and slices/completed/dns-reservation-provider/; a relative-link check over decisions.md finds none broken; struck by consult 1

<details><summary>struck — body kept for the record</summary>

In `/work/AnsibleSpecs/decisions.md`, relative links to `slices/runtime-secrets-sweep.md`, `slices/microceph-prod.md` (three times), `slices/internal-ha-vips.md`, `specs/dns-reservation-api.md` and `specs/dns-reservation-terraform.md` resolve to nothing. The files were moved under `slices/completed/` and other paths. These links predate this slice, and P1 found them while checking its own links.

code-writer P1 r1, 2026-09-26 — The targets now sit at `slices/completed/runtime-secrets-sweep.md`, `slices/completed/internal-ha-vips.md`, `change_requests/microceph_prod/microceph-prod.md` and `slices/completed/dns-reservation-provider/dns-reservation-{api,terraform}.md`.

**Consequence:** Those links in the doctrine every session reads first lead nowhere.

**Provenance:** witnessed — code-writer, P1, r1; a relative-link check over decisions.md
**Disposition:**

</details>

### ~~S7 — The estate register's k8s-upgrade pin list still names HelmCharts' deploy tooling as a consumer to bump and redeploy · minor~~ — closed by the operator, 2026-09-29 (fixed in AnsibleSpecs 91a4d96)

<details><summary>struck — body kept for the record</summary>

AnsibleSpecs `decisions.md:279` lists "the Helm deploy tooling in `HelmCharts/tools/requirements.txt`" among the `kubernetes` Python client pins that a cluster upgrade must bump and redeploy first. After this slice HelmCharts deploys nothing (argo-cd `design.md:10`). P1 left the list as it is on purpose. ArgoCDTools does not use the client, so no live consumer is missing from the list.

doc-writer, doc phase r1, 2026-09-26 — Addressed in AnsibleSpecs 91a4d96: decisions.md's pin list no longer names HelmCharts/tools/requirements.txt; the DockerImages images and ZigbeeControl remain.

**Consequence:** The next k8s upgrade run from the doctrine tries to commit a pin bump to HelmCharts, which is archived after ANS-122 and not to be added to before it (D43).

**Provenance:** read — code-reviewer, P1, r1; phases/P1/code_review_r1.md F1
**Disposition:** Please advise — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested close (already fixed in AnsibleSpecs 91a4d96)

</details>

### ~~S8 — P6 carries AnsibleSpecs edits (the runbook path in D64 and phases.md) under Target: root · nit~~ — closed by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

P1 added `plan.md:406-411` to P6. It asks P6 to put the switch runbook's path into argo-cd `decisions.md` D64 and `phases.md`, both in AnsibleSpecs, but P6's `Target:` is `root`. The phase branch and its review cover one repo, so these edits sit outside both.

consult 1, 2026-09-26 — The edits landed on AnsibleSpecs main as d05e22d (D64 and phases.md's endgame name /work/Ansible/docs/runbooks/registry-switch.md). What stays true is that no phase review covered them.

**Consequence:** P6's AnsibleSpecs edits can land on whatever AnsibleSpecs branch is checked out, unreviewed.

**Provenance:** read — code-reviewer, P1, r1; phases/P1/code_review_r1.md F2
**Disposition:** Close

</details>

### ~~S9 — Architecture's prose docs still name HelmCharts as a producer or deploy path · nit~~ — fixed in Architecture 5b3e4f6, 84ae5ad

<details><summary>struck — body kept for the record</summary>

P2 brought current the comments, schema examples, the producer kit (.claude/) and the tool texts. The prose docs it left for a docs pass: README.md:5 and USAGE.md:7 list HelmCharts among the producers; README.md:216-217 says the Helm chart lives in pvginkel/HelmCharts (the Jenkinsfile pins into WebathomeOrgDeploy); docs/architecture-update.md:50 cites HelmCharts' gen_architecture.py as the gap-line example, and :115 names IaC/HelmCharts as the usual downstream build; docs/iotsupport-iot-architecture-guidance.md:149-150, :164 and :192 describe HelmCharts' image mapping and instances as current. The published summary of if:home-assistant-api (docs/architecture/home-automation.yaml:98) points at HelmCharts/charts/nginx/files/nginxmanager/external-services.yaml. P9 targets Ansible only, so no planned phase covers these.

doc-writer, doc phase r1, 2026-09-26 — Addressed in Architecture 5b3e4f6 (not pushed): README.md (producers; the viewer's chart is in WebathomeOrgDeploy, which the pipeline pins and Argo CD syncs), USAGE.md, docs/architecture-update.md (gap lines come from aac-tools' gen-architecture; the IaC/HelmCharts downstream example is gone) and docs/iotsupport-iot-architecture-guidance.md. Still open: the published summary of if:home-assistant-api (docs/architecture/home-automation.yaml:98) is model data, which the doc phase does not edit.

**Consequence:** A reader of Architecture's README, USAGE or update docs, or of that published element, is sent to HelmCharts, which is archived after ANS-122.

**Provenance:** read | code-writer, P2, r1, grep of /work/Architecture at a4402f6
**Disposition:** Fix inline — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — the rest fixed in Architecture 5b3e4f6; the if:home-assistant-api summary in Architecture 84ae5ad

</details>

### ~~S10 — Architecture's producer manual: the Ceph example no longer matches the 'service you own' rule it illustrates · nit~~ — fixed in Architecture 5b3e4f6

<details><summary>struck — body kept for the record</summary>

In .claude/architecture/producer-manual.md:825-830, the 'Re-provide via your own service layer' bullet says to Realize 'a new cluster-local TechnologyService **you** own'. After P2 its Ceph example says svc:cluster-ceph-rbd is 'declared in the Architecture repo's shared catalog', so the deploying repo does not own the service in the example.

doc-writer, doc phase r1, 2026-09-26 — Addressed in Architecture 5b3e4f6 (not pushed): the Ceph example says svc:cluster-ceph-rbd sits in the shared catalog rather than with the driver, and that a service added this way is declared by its own producer.

**Consequence:** A producer that copies the example instead of the rule references a catalog service rather than declaring its own.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F2
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — already fixed in Architecture 5b3e4f6

</details>

### ~~S11 — Intercom's dev-upload script takes the OTA signing key from a sibling HelmCharts checkout's assets/ · nit~~ — closed by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

Intercom `tools/dev-upload/upload.bat` (last changed d3c3f3c, 2025-04-19) mounts `%CD%/../HelmCharts/assets` into its uploader container and signs with `/workspace/keys/kubernetes-signing-key`. It is a developer-machine script, not a Jenkins caller, so it does not block ANS-121. After ANS-122 the key still lives only in the archived repo.

**Consequence:** A dev OTA upload of Intercom needs a HelmCharts clone for as long as the signing key lives only there; the archive leaves it readable, so nothing breaks.

**Provenance:** read | code-writer, P3, r1, gh search code 'HelmCharts/assets' --owner pvginkel
**Disposition:** The file isn't used anymore. Please close. It has no priority.

</details>

### ~~S12 — ElectronicsInventory's docs/slice-test-plan.md still says its Jenkinsfile ends in cicd.helmDeploy() · nit~~ — fixed in ElectronicsInventory a47d773

<details><summary>struck — body kept for the record</summary>

P3 removed cicd.helmDeploy() from JenkinsPipelineUtils. A GitHub code search for helmDeploy right before the phase handed back found no caller in code. It did find one stale prose mention: ElectronicsInventory docs/slice-test-plan.md:15 ("...and ends in `cicd.helmDeploy()`. That is the repo's standing..."). That repo is not in this slice's scope, and P9 covers Ansible only.

**Consequence:** A reader of ElectronicsInventory's test plan is told the build hands off through a helper that no longer exists.

**Provenance:** witnessed, code-writer, P3, r2, gh search code --owner pvginkel helmDeploy
**Disposition:** Fix inline — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — ElectronicsInventory a47d773

</details>

### ~~S13 — ArgoCDDeploy's README and root project description do not mention the registry chart or the equivalence check · nit~~ — fixed in ArgoCDDeploy 83b6cf8

<details><summary>struck — body kept for the record</summary>

P4 added releases/ (the registry: values.yaml, values.schema.json, one Application per app-stage) and tools/registry-equivalence.py to ArgoCDDeploy. README.md still describes the repo as the wrapper chart plus its stage configuration, and .kubecoder/project.yaml's root description says the same. P9 targets Ansible only, so no planned phase covers ArgoCDDeploy's own prose.

doc-writer, doc phase r1, 2026-09-26 — Addressed in ArgoCDDeploy 83b6cf8 (not pushed): README.md describes releases/ (values.yaml is the registry, values.schema.json its validation), the releases Application, releases.owner and tools/registry-equivalence.py; the root description names the registry chart. registry-switch.md's dead-after list now includes that README paragraph.

**Consequence:** A reader of ArgoCDDeploy's README is not told that the repo holds the registry, where it is, or how to check it against the live Applications.

**Provenance:** read | code-writer, P4, r1, ArgoCDDeploy 19e40d3
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — already fixed in ArgoCDDeploy 83b6cf8

</details>

### ~~S14 — Ansible argocd runbook: its Conventions say the default kubeconfig cannot list argoproj.io kinds, and it can · nit~~ — fixed in Ansible 43b88c5

<details><summary>struck — body kept for the record</summary>

docs/runbooks/argocd.md's Conventions: "the read-only default kubeconfig cannot list `argoproj.io` kinds". On 2026-09-26 the default kubeconfig (`--context prd`, no --kubeconfig) listed Applications, ApplicationSets and the AppProject in argocd-prd; ArgoCDDeploy's tools/registry-equivalence.py relies on it, and docs/live-infra-access.md says kubecoder-ro holds get/list/watch on those three kinds. P9's docs pass targets HelmCharts wording, so nothing in the slice corrects this line.

doc-writer, doc phase r1, 2026-09-26 — Addressed in Ansible 43b88c5: argocd.md's Conventions say the default kubeconfig can list Applications, ApplicationSets and AppProjects but not patch or annotate them (kubectl auth can-i on 2026-09-26: list yes, patch no, for all three).

**Consequence:** A reader of the argocd runbook reaches for the cluster-admin prd-write kubeconfig for reads that the read-only identity already covers.

**Provenance:** witnessed — code-writer, P6, r1, kubectl reads while testing the registry-switch runbook's helpers
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — already fixed in Ansible 43b88c5

</details>

### ~~S15 — Ansible registry-switch runbook: status reads run straight after an asynchronous sync or refresh, with no instruction to wait · nit~~ — fixed in Ansible 43b88c5

<details><summary>struck — body kept for the record</summary>

docs/runbooks/registry-switch.md's argosync is a kubectl patch of operation and returns before the sync runs; step 4's hand refresh likewise. Steps 1d, 4, 9 and 10 read status in the same block and state the post-completion result as what the operator should see; only step 1a says to repeat until Synced. In step 1d the rehearsal diff ('no diff output', the proof that the child is unchanged after the app-of-apps' sync) is met vacuously by a read taken before the sync applies the child; the same block's tracking-id read fails in that case, so re-running the whole block recovers. In step 4, argostate right after argosync prints the previous operation (OutOfSync Succeeded), and outofsync right after the refresh prints nothing, a case the step has no branch for.

doc-writer, doc phase r1, 2026-09-26 — Addressed in Ansible 43b88c5: argosync now returns only once the controller has cleared .operation (the sync finished, successfully or not), and step 4 waits for the refresh annotation to go before outofsync. Grounded in Argo CD v3.5.1's controller/appcontroller.go (setOperationState clears operation on a completed phase; persistReconciliationStatus drops the refresh annotation); not run against the cluster.

**Consequence:** An operator who pastes a step block whole sees pre-completion state and has to re-run; in the rehearsal's step 1d, re-running only the failing read would leave the adoption proof resting on a pre-sync diff.

**Provenance:** read — code-reviewer, P6, r1, phases/P6/code_review_r1.md F1
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — already fixed in Ansible 43b88c5

</details>

### ~~S16 — The nine upstream deploy repos' README and architecture.yaml name HelmCharts' release.yaml as the registry entry that pins the chart version · nit~~ — fixed in the nine upstream deploy repos, 2026-09-29

<details><summary>struck — body kept for the record</summary>

argo-migrate's scaffold wrote the line into each upstream deploy repo: the README's "chart version" bullet (`HelmCharts configs/prd/<app>/<stage>/release.yaml, upstream.version`) and the comment above architecture.yaml's `upstream:` block. Read on GrafanaDeploy `main` (README.md:10, architecture.yaml:9). The same text is in CephCsiCephfsDeploy, CephCsiRbdDeploy, CloudnativePgDeploy, CsiDriverSmbDeploy, ExternalSecretsDeploy, HeadlampDeploy, PrometheusDeploy and StepCaDeploy, since the same template wrote all nine. P7 changed the scaffold templates to name ArgoCDDeploy `releases/values.yaml` (the stage's `version`). The nine repos are outside this slice, and P9 targets Ansible only.

**Consequence:** Once the registry switch has run, an operator bumping an upstream chart who follows the deploy repo's README edits HelmCharts' inert release.yaml, not the registry Argo reads. The live version does not move, and D57's two pins drift apart.

**Provenance:** witnessed, code-writer, P7 r1, gh api repos/pvginkel/GrafanaDeploy/contents/{README.md,architecture.yaml}
**Disposition:** Fix inline — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — GrafanaDeploy 4584e09, CephCsiCephfsDeploy 4f9283a, CephCsiRbdDeploy c4b7418, CloudnativePgDeploy 99e670a, CsiDriverSmbDeploy 4c1e8c4, ExternalSecretsDeploy f1083d5, HeadlampDeploy 4528629, PrometheusDeploy 566062c, StepCaDeploy 85842a4

</details>

### ~~S17 — argo-migrate's arch step still runs HelmCharts' generator for a helm-charts producer that no longer publishes · nit~~ — closed under the operator's nit rule, 2026-09-29

<details><summary>struck — body kept for the record</summary>

cmd_arch's second half (`helm_charts_without`, `hc_releases_without`) renders every HelmCharts release but the migrating app's, and checks that the edges helm-charts publishes are still drawn. Once P2's Architecture push lands, the published dataset has no helm-charts relations. The check then compares against nothing, and all it still asks is that HelmCharts' `gen-architecture` builds from the archived checkout. P7 moved its on-Argo read to the registry and left the half in place, because the plan keeps the tool's HelmCharts reads. Removing it (and `HC / docs/architecture/helm-charts.yaml`) is a follow-up for after that push.

**Consequence:** Each remaining migration's arch step needs a working poetry environment in the archived HelmCharts checkout, and fails if it has none, for a check with nothing left to protect.

**Provenance:** read, code-writer, P7 r1, support/argo-migrate/argo_migrate.py cmd_arch
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29: removing cmd_arch's HelmCharts half is not a small change, and only the three parked apps could still need it

</details>

### ~~S18 — argo-migrate's unit suite covers the registry text edits only; its registry reads and parse-equality guard have no test · nit~~ — closed under the operator's nit rule, 2026-09-29

<details><summary>struck — body kept for the record</summary>

support/argo-migrate/test_registry.py imports only registry_flip, registry_autosync and Stop. Nothing tests App.on_argo, registry_upstream/check_upstream_pin, preflight's choice of server-side apply from the registry's syncOptions, or hc_releases_without's flipped. checked(), the guard that an edit changes nothing but the intended entry, survives being made a no-op: all 10 tests stay green. Today's reads match HelmCharts' (50/50 stages, syncOptions and upstream pins agree), and a flip/autosync round trip over all 49 real app-stages is clean. The gap is only that nothing will catch a regression. A suggestion: point the tests at a fixture registry (ARGOCD_DEPLOY is a module constant) and add one read test per question and one refusal test for checked().

**Consequence:** A later edit that sends one of the tool's registry reads back to HelmCharts or the per-stage state, or that breaks the edit guard, passes root's test gate.

**Provenance:** read, code-reviewer, P7, r1, phases/P7/code_review_r1.md F1
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29: a test gap with little riding on it

</details>

### ~~S19 — recommend-resources' unit suite: two paths pass under mutation, the local-chart name and apply's invalid-YAML rollback · nit~~ — closed under the operator's nit rule, 2026-09-29

<details><summary>struck — body kept for the record</summary>

Replacing the local chart's Chart.yaml name with the app name (recommend_resources.py:132) passes, because every fixture's chart name equals its app name (test_recommend_resources.py:96-99, :247, :255). Dropping apply's invalid-YAML refusal or its git reset rollback (:631, :633-634) also passes. No live chart name differs from its app today. Review F4, F5.

**Consequence:** A later edit that keys local apps on the app name, or that drops apply's YAML guard, passes root's test gate.

**Provenance:** witnessed, code-reviewer, P8, r1, phases/P8/code_review_r1.md F4 F5
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29: a test gap with little riding on it

</details>

### ~~S20 — Ansible code comments, inventory and Terraform descriptions still point at HelmCharts for workloads, dnsmasq and credentials · nit~~ — closed under the operator's nit rule, 2026-09-29

<details><summary>struck — body kept for the record</summary>

P9's doc list covers the docs, READMEs and one code comment (microk8s defaults). These comments were outside it and still name HelmCharts as where something lives: ansible/inventories/prd/group_vars/k8s_prd.yml:57,122, all/vips.yml:8, openbao.yml:68,122,125, ceph_dev.yml:3,46,89, k8s_dev.yml:2,25,38,60,63, hosts.yml:32,46, host_vars/srvk8s4.yml:22; ansible/roles/microk8s/tasks/taints.yml:17; ansible/playbooks/rebuild-k8s.yml:156 and playbooks/tasks/pre-drain-handoff.yml:22; support/iac-image/Dockerfile:55-63; Ansible.code-workspace:10; terraform/prd/variables.tf:41 (backupServer.managementToken's source) and terraform/prd/vms.tf:107 (srvk8sdev's VM description, 'HelmCharts iteration target'). Editing vms.tf's description is a Proxmox-side change a terraform plan shows. The iac agent's copies are S2's.

doc-writer, doc phase r1, 2026-09-26 — Addressed in Ansible 43b88c5: vips.yml and k8s_prd.yml:122 (DnsmasqDeploy's static-hosts-config in chart/templates/stage-manifests.yaml), srvk8s4.yml, taints.yml and rebuild-k8s.yml (tolerations live in the deploy repos), pre-drain-handoff.yml (KeycloakDeploy carries the label), terraform/prd/variables.tf (the token's server copy is OpenBao kv/eso/prd/storage/prd/backup-server via StorageDeploy's ExternalSecret). Left as they are: the srvk8sdev/configs/dev comments (F1, as P1 left the estate register's), k8s_prd.yml:57 (historical), openbao.yml's grant comments (they describe grants that still serve HelmCharts' deploy, S2's clean-up), support/iac-image/Dockerfile (a push rebuilds the iac image), terraform/prd/vms.tf:107 (a Proxmox-side change) and Ansible.code-workspace (HelmCharts stays cloned until the archive).

**Consequence:** A reader following those comments is sent to HelmCharts paths that are gone or archived; no behaviour depends on them.

**Provenance:** read, code-writer, P9, r1, git grep -i helmcharts in Ansible
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29: what is left is srvk8sdev's history in comments, openbao.yml's grant comments (they go with S30), and two with side effects (vms.tf's Proxmox description, an iac image rebuild)

</details>

### ~~S21 — Planning a deploy repo's Terraform by hand loads its credentials with HelmCharts' scripts/setup-env.sh · minor~~ — fixed in Ansible 657d13c

<details><summary>struck — body kept for the record</summary>

live-infra-access.md now says a deploy repo's Terraform is applied by the PreSync hook, which has no plan step, and that planning it from here takes HelmCharts' scripts/setup-env.sh prd for the OpenBao-held provider credentials (kubecoder-cutover.md's no-destroy plan, argo_migrate.py plan). argo_migrate.py's plan also reads HelmCharts' _providers/clusters.yaml for the non-secret tf_vars. Neither has another home. .kubecoder/config.yaml keeps cloning HelmCharts until the archive (ANS-122) drops it.

**Consequence:** Once the HelmCharts clone leaves this environment, there is no documented way to plan a deploy repo's Terraform before a sync applies it.

**Provenance:** read, code-writer, P9, r1, docs/live-infra-access.md
**Disposition:** Move the file into the Ansible repo please. — moved: Ansible 657d13c (scripts/setup-env.sh; live-infra-access.md, the cutover runbook's no-destroy plan and argo_migrate.py plan source it)

</details>

### ~~S22 — Ansible docs: slice-testing-strategy.md says the repo has no runnable test suite, and CLAUDE.md lists KubeCoderDeploy under /work · nit~~ — fixed in Ansible 43b88c5, ca536a6 and since

<details><summary>struck — body kept for the record</summary>

Found by P9 while editing nearby text; neither concerns HelmCharts. docs/slice-testing-strategy.md:6 and :13 say there is no runnable test suite and that kc project test is yamllint, ansible-lint, terraform fmt and the architecture validator; root's test now runs support/argo-migrate's and support/recommend-resources' unit tests (P7, P8). P9 corrected the same claim in design-philosophy.md. CLAUDE.md's 'Related repos on this machine' lists KubeCoderDeploy as under /work, but .kubecoder/config.yaml does not declare it and /work holds no clone. Also docs/runbooks/kubecoder-cutover.md:15 links slice 012's plan at slices/012_kubecoder_argo_cutover/, which moved to slices/completed/.

consult 1, 2026-09-26 — The dead link in kubecoder-cutover.md:15 is fixed: it points at slices/completed/012_kubecoder_argo_cutover/plan.md (Ansible ca536a6). Still open: slice-testing-strategy.md's 'no runnable test suite' (a file this slice did not touch) and CLAUDE.md's KubeCoderDeploy line, which needs a choice between declaring the repo in .kubecoder/config.yaml and dropping it from the list.

doc-writer, doc phase r1, 2026-09-26 — slice-testing-strategy.md addressed in Ansible 43b88c5: the roles and Terraform have no runnable suite, argo-migrate and recommend-resources carry unit tests, and root's gate runs them. design-philosophy.md narrowed the same way: iac-impl is a Python tool under support/ with no tests, so 'the Python tools under support/' was too wide. Still open: CLAUDE.md's KubeCoderDeploy line (declare the repo in .kubecoder/config.yaml, or drop it from the list).

**Consequence:** The test phase's strategy doc understates what root's gate runs, a session that reaches for /work/KubeCoderDeploy finds nothing, and one link in the KubeCoder cutover record is dead.

**Provenance:** read, code-writer, P9, r1
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — all fixed since: Ansible 43b88c5, ca536a6; CLAUDE.md now lists KubeCoderDeploy under /work/scratch

</details>

### ~~S24 — DockerImages' certbot args.sh bind-mounts HelmCharts' nginx copy of the homelab root; StepCaDeploy's values still credit charts/step-ca/args.sh · nit~~ — fixed in DockerImages 1722f83 and StepCaDeploy c9dc159

<details><summary>struck — body kept for the record</summary>

DockerImages certbot/scripts/args.sh:18 mounts $(pwd)/../../HelmCharts/charts/nginx/files/ca/homelab-root.crt for a hand-run certbot. The nginx copy that is deployed is now NginxDeploy's chart/files/ca/homelab-root.crt, and P9's step-ca-root-rotation.md inventory drops HelmCharts' copies, so a root rotation leaves the one args.sh reads stale. Separately, StepCaDeploy's config/prd/values.yaml keeps a comment saying charts/step-ca/args.sh pulls smallstep/step-certificates; the registry's apps.step-ca.stages.prd.version pins it.

**Consequence:** After ANS-122 drops the HelmCharts clone, a hand-run certbot from DockerImages fails its bind mount. After a root rotation, a run before that serves the old root. The StepCaDeploy comment points a reader at a file in the archive.

**Provenance:** read, code-writer, P9, r1
**Disposition:** Fix inline — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29 — args.sh is gone since DockerImages 1722f83; the StepCaDeploy comment fixed in StepCaDeploy c9dc159

</details>

### ~~S25 — Ansible step-ca-bootstrap.md: day-zero step 7 no longer says to write the ceremony's new material into StepCaDeploy · minor~~ — closed by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

P9 turned step 7 (docs/runbooks/step-ca-bootstrap.md:243-263) from a kubectl create secret command into a description: which Secrets the chart reads, that StepCaDeploy's chart/templates/stage-manifests.yaml renders them today, and a check once Argo has synced. It never says to base64 this ceremony's root, intermediate, key, passphrase and ca.json/defaults.json into stage-manifests.yaml and push. The intermediate rotation's step 3 (:540-549) says exactly that for its three values.

consult 1, 2026-09-26 — Not a mechanical fix, so it stays open. Two facts for whoever writes step 7's instruction, read from StepCaDeploy main's chart/templates/stage-manifests.yaml (Secret names, data keys and ca.json's path fields only; no values printed). (1) The manifest renders five Secrets, not four: step-ca-ssh-host-ca-password (key password) is missing from step 7's table. It belongs to 'Enabling the SSH host CA' step 2, not to this ceremony. (2) The chart's ca.json uses the pod's paths (root /home/step/certs/root_ca.crt, key /home/step/secrets/intermediate_ca_key, db /home/step/db) and carries an ssh.hostKey block. The ceremony's local .step/config/ca.json has neither, so it cannot be base64'd in as it is. The instruction has to say what carries over (the new certs, the key, the passphrase, and the provisioner the init minted) and what stays (the pod paths and the ssh block).

doc-writer, doc phase r1, 2026-09-26 — Addressed in Ansible 43b88c5: step 7 lists all five Secrets (step-ca-ssh-host-ca-password included, marked as the SSH host CA's), says which values the ceremony replaces in stage-manifests.yaml (the certs, the key, the passphrase, and in ca.json/defaults.json the authority block's provisioners and claims and the root fingerprint, keeping the chart's /home/step paths and ssh block), then restarts the StatefulSet and diffs step-ca-certs' root_ca.crt against .step/certs/root_ca.crt. Grounded in StepCaDeploy main's Secret names, data keys and ca.json/defaults.json paths (values not read); the procedure has not been run.

**Consequence:** An operator re-running the ceremony after a CA loss can pass step 7's check on the old material Argo keeps serving. Step 9 then shreds the new intermediate key, and it has to be re-issued from the root key in Roboform.

**Provenance:** read, code-reviewer, P9, r1, phases/P9/code_review_r1.md F1
**Disposition:** Please advise — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested close (rewritten in Ansible 43b88c5; only unrun)

</details>

### ~~S26 — Ansible design-philosophy.md: 'only the Python tools under support/ carry unit tests' misses tools/ai_workflow/test_track_build.py · nit~~ — resolved by consult 1 (Ansible ca536a6): design-philosophy.md says the support/ tools' unit tests are root's, and that tools/ai_workflow/test_track_build.py is a unit test no gate runs (checked against .kubecoder/project.yaml's test: keys); kc project lint green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

P9's rewrite of 'What tested means here' (docs/design-philosophy.md:61-62) says root's gate runs every unit test and all of them are under support/. tools/ai_workflow/test_track_build.py is a tracked unit test, and root's test: (.kubecoder/project.yaml:18-20) does not run it.

**Consequence:** A reader of the binding change doc takes root's green as covering track_build.py, and it does not.

**Provenance:** read, code-reviewer, P9, r1, phases/P9/code_review_r1.md F2
**Disposition:**

</details>

### ~~S27 — Ansible kubecoder-cutover.md: the P3 record cites argocd.md producer steps 2, 4 and 5, which P9 renumbered and removed · nit~~ — resolved by consult 1 (Ansible ca536a6): kubecoder-cutover.md's P3 record now says its step numbers are the argocd.md section's at the time of the run, and that slice 029 removed the handover proof and flip and renumbered the rest; the record's own steps are unchanged; struck by consult 1

<details><summary>struck — body kept for the record</summary>

argocd.md's 'Giving an app its own architecture producer' lost its handover proof and flip in P9, and its steps are now 1-4 (docs/runbooks/argocd.md:381-405). kubecoder-cutover.md:803-815 still follows 'steps 2, 4 and 5' and calls step 2 the handover equality check, whose command is gone from argocd.md. The file is marked as a finished run's record (:8-12).

**Consequence:** A reader of the cutover record who follows its step numbers into argocd.md lands on the wrong steps. Nothing is re-run from it.

**Provenance:** read, code-reviewer, P9, r1, phases/P9/code_review_r1.md F3
**Disposition:**

</details>

### ~~S28 — Ansible k8s-rebuild.md says HelmCharts' configs/dev tree already went into its archive · nit~~ — resolved by consult 1 (Ansible ca536a6): k8s-rebuild.md says HelmCharts' configs/dev tree goes into its archive with the repo (D65), no longer that it went; struck by consult 1

<details><summary>struck — body kept for the record</summary>

docs/runbooks/k8s-rebuild.md:258 says 'since HelmCharts' configs/dev tree went into its archive (argo-cd D65)'. The archive is ANS-122, after this slice. D65 says the tree goes into it, and /work/HelmCharts/configs/dev/ is live today.

**Consequence:** The runbook states a future event as done. Per the F1 ruling nothing waits on it.

**Provenance:** read, code-reviewer, P9, r1, phases/P9/code_review_r1.md F4
**Disposition:**

</details>

### ~~S29 — Architecture's kc project test does not reproduce the Docker image build's file layout, so a test can pass locally and fail the CI build · minor~~ — closed by the operator, 2026-09-29

<details><summary>struck — body kept for the record</summary>

The viewer's `kc project test` runs `npm test` inside the repo tree, where `../../../` from `viewer/src/` is the repo root. The Dockerfile's `build-viewer` stage runs the same suite in a tree with only what it COPYs. The two layouts diverged for P2's test, and only the push showed it. A gate step `kaniko --context . --no-push --target build-viewer` (about 90 seconds) in Architecture's root component would catch that class before a push; `--target build-service` does the same for the service stage.

**Consequence:** The next test that reads a repo file from viewer/ or service/ repeats the P2 failure: green gate, red CI build after the push.

**Provenance:** witnessed, test-agent, phase test, round 1, AaC/Architecture #2068
**Disposition:** Please advise — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested close

</details>

### ~~S30 — OpenBao's jenkins policy still grants the HelmCharts deploy's three leaves: shared/prd/ceph-csi, shared/prd/ceph-rgw/s3 and eso/prd/iac-provisioner/api/token · minor~~ — fixed in Ansible 687a80e (applies on the operator's site-openbao.yml run)

<details><summary>struck — body kept for the record</summary>

Ansible ansible/inventories/prd/group_vars/openbao.yml, openbao_jenkins_kv_paths, grants the three leaves its comment attributes to the HelmCharts deploy pipeline's homelab TF provider. IaC/HelmCharts is deleted. The same comment's history (022 P6 code review r1) says artifact-upload pipelines read the RGW admin key too, and no Jenkinsfile in the checked-out repos names these paths, so which pipelines still read them is unsettled. The iac-agent policy's copy of these grants was removed on 2026-09-28 (Ansible 35d9e3e).

**Consequence:** Jenkins keeps read access to the prd cephx user, the RGW admin key and the iac-provisioner token, whether or not any pipeline still needs them.

**Provenance:** witnessed, the operator's session after the registry switch, 2026-09-28; ansible/inventories/prd/group_vars/openbao.yml
**Disposition:** PLease advise — the operator, 2026-09-29: "Agreed on the rest. Please execute and push when done." — suggested fix now — Ansible 687a80e, AnsibleSpecs 4ae5126; applied by the operator's site-openbao.yml run, 2026-09-30 (the jenkins policy was the only change)

</details>

### ~~S31 — The iac-agent policy still grants eso/prd/postgres-pas/terraform-admin and eso/prd/storage/prd/backup-server, which secrets.example.yaml never references · nit~~ — closed under the operator's nit rule, 2026-09-29

<details><summary>struck — body kept for the record</summary>

Added 2026-06-17 (Ansible ca536a6, f8031b6) with no stated consumer, during the HelmCharts deploy harness work; terraform/prd reads the backup-server token from kv/iac/backup-server instead. Whether srviac's live /etc/iac/secrets.yaml references them settles it: sudo grep -n 'postgres-pas\|storage/prd' /etc/iac/secrets.yaml.

**Consequence:** If unused, the iac agent keeps read access to the Terraform PostgreSQL admin credential and the storage backup-server token for no job.

**Provenance:** witnessed, the operator's session after the registry switch, 2026-09-28; openbao policy read iac-agent
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29: settling it needs a read of srviac's live /etc/iac/secrets.yaml; it goes with S30 if that one is acted on

</details>

### ~~S32 — Ansible support/iac-image/Dockerfile: the poetry and uv install comments still justify them by the HelmCharts deploy CLI and pipeline · nit~~ — closed under the operator's nit rule, 2026-09-29

<details><summary>struck — body kept for the record</summary>

support/iac-image/Dockerfile around line 55: poetry is kept for 'the HelmCharts deploy CLI' (cd /work/HelmCharts && poetry install), and uv 'because the HelmCharts pipeline ... spins up a fresh container per release'. Left unedited on 2026-09-28 because a comment-only change rebuilds the image; poetry is still used (this repo's own lint runs through it), uv may no longer be.

**Consequence:** A reader of the iac image is told it serves a deploy path that is gone, and the uv install may be dead weight in every image build.

**Provenance:** witnessed, the operator's session after the registry switch, 2026-09-28; support/iac-image/Dockerfile
**Disposition:** Close — Claude's ruling under the operator's nit rule (fix inline if small and clear, else close), 2026-09-29: a comment-only edit rebuilds the iac image, and whether uv can go is not settled

</details>
