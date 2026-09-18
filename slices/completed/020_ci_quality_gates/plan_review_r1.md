# Slice 020 — plan review, round 1

Verdict: **issues**. There is one blocking finding, and it is about the text of the rulings section, not what the plan does. There is also one advisory. The plan covers everything slice.md asks for, and the facts it depends on held when checked against the code.

## Blocking

### B1 — The "binds the plan" grounding still says storage's lint failure needs no fix, and the round-two rulings broke the settled list

**Problem.** The Q1 and Q2 rulings were added in commit `451f68e`. They changed the plan, but the grounding section still states what they overturned, and the way they were inserted broke the list around them.

**Evidence.**
- `plan.md:33`, under "Grounding — verified 2026-09-15, binds the plan", still says all three charts that fail default-value lint (`media`, `mosquitto`, `storage`) fail only because of defaults: "the failures are default-value artifacts, and a fix would not change deployed output." For `storage` that is the claim the Q1 ruling (`plan.md:21`) overturned: it fails `helm lint` with its prd values too, and P4 fixes it (`plan.md:97`).
- `plan.md:41` says `tools/deploy/deploy_cli template` is "plain `helm template` with its values". The code does more. `template` builds its command in `_helm_invocation` (`HelmCharts/tools/deploy/deploy_cli/helmops.py:173-193`), which adds `global.environment`, the chart's post-renderer and the release's `helm_args`. P4 (`plan.md:105`) says this correctly, so the grounding contradicts the phase that depends on it.
- `plan.md:21-25`: commit `451f68e` put the Q1 and Q2 rulings between the sub-bullets of "Settled at refinement". Three settled items now sit indented under the Q2 kubeconform ruling: the gate covers only releases about to deploy, `media` is the reference chart, and images are pinned by digest.

**Impact.** Every later session reads a section labelled binding that contradicts P4 and the Q1 ruling on whether `storage` needs a chart change. Those sessions are the P4 and P5 code-writers, the P4 reviewer, the test agent and the doc-writer, which works from the rulings. It also says rendering is plain `helm template`, which undercuts P4's "rendered with what it is deployed with". Three settled positions also read as part of the wrong ruling. Rulings are edited in place, not left beside their corrections.

## Advisory

### A1 — P4 points kubeconform at a sibling container but never says that container can see only host paths

**Problem.** P4 says kubeconform runs from a digest-pinned image, launched as a sibling container through the agent's host docker socket (`plan.md:107`). It never says what that container can see. It sees host paths only. It cannot see the agent's workspace, or the iac container's clone where the manifests are rendered.

**Evidence.**
- The agent's work directory is `/home/jenkins/agent` inside the agent container (`Ansible/support/iac-agent/bin/jenkins-agent-launch.sh:15`). The agent's `docker run` mounts the docker socket, the docker binary and the `iac` shims, not that directory (`:59-66`).
- `iac` mounts only the secrets file and helper scripts into its container (`Ansible/support/iac-agent/bin/iac:44-50`). The HelmCharts clone is private to each `iac -c` container (`HelmCharts/Jenkinsfile:33-42`).
- P4 itself notes that the Jenkinsfile cannot be checked before the push (`plan.md:47`, `:109`).

**Impact (failure scenario, reasoned from the mounts above, not run).**
1. A Jenkinsfile bind-mounts the rendered manifests from the agent workspace or from inside the iac container.
2. That path does not exist on the host, so docker creates it as an empty directory.
3. kubeconform finds no files, reports 0 resources and exits 0.
4. The chart gate goes green without validating anything.

The first real build, which V18 relies on as proof, would also be green. The only sign is a "0 resources found" line in the log.

## What was checked and holds

- **Acceptance criteria are complete.** Each clause of R1 has its own criterion, and so does each ruling:
  - ansible-lint strict → V01
  - yamllint and syntax-check → V02
  - terraform fmt/validate → V03
  - "before anything mutates, cheap first" → V04
  - go vet/test → V05, V06
  - helm lint and kubeconform → V07–V11
  - the values schema → V12, V13
  - trivy and the alert ruling → V14–V16
  - digest pins → V17
  - the push ruling → V18

  Nothing is dropped or softened. The two substitutions are both ruled: lint uses prd values instead of chart defaults, and trivy alerts without changing build status. The two corrected card premises are handled as the grounding says: "fmt fails today" and "fix 6 findings". There are no doc-truth universals, and no criterion is left to the doc phase.
- **Task shape.** `cross-cutting` is right. The requirement spans four repos' pipelines, and slice.md settles none of the integration design.
- **Targets.** `ansible` and `root` are real components in `kc project list`. `../HomelabTerraformProvider`, `../HelmCharts` and `../DockerImages` exist, and each phase is aimed where its work lands.
- **Phases.** Six phases, each about PR-sized, with the strict lint flip before the push job that enforces it. There is no planned end-to-end test phase or doc pass. There are no attachments and no doc-deliverable content.
- **Checked myself (2026-09-15):**
  - `ansible-lint --strict` in the iac sidecar fails on exactly one violation: `jinja[spacing]` at `roles/microk8s/tasks/elect-primary.yml:44`. That is P1's premise.
  - The `storage` separator problem follows from the trim markers in `charts/storage/templates/storage-cronjobs.yaml:1-4,54-56`: iteration two starts `---apiVersion:`.
  - The r1 kubeconform check skipped post-renderers. I rendered the three charts that have one (`mosquitto`, `grafana`, `prometheus`) through their `post-render.sh` with prd values. All three pass kubeconform 1.35 `-strict`. So P4's "every prd release passes the gate" also holds for what is actually deployed.
  - prd is pinned to `1.35/stable` at `ansible/inventories/prd/group_vars/k8s_prd.yml:26`. P4 cites the role default, which has the same value.
  - `args` is non-empty only when a live digest moved (`HelmCharts/tools/chart_tools/resolve_helm_args.py:129-157`), which fits "gated set = deployed set".
  - `configs/prd/media/_shared` holds no values file, so P5's list of legitimate value sources is complete.
  - DockerImages has 53 variants over 53 images and no matrix images today, so "one alert per image" is unambiguous.
  - The iac image gets its Ansible collections from the `ansible` package in `pyproject.toml`.
  - `terraform/prd` reads `ansible/` through `file()` (`main.tf:15`, `vms.tf:377`), which is why `validate` needs the whole clone.

## Close-out

- S2 (cosmetic) is appended. The comment above the provider Jenkinsfile's publish stage describes delivery stages that no longer exist.
