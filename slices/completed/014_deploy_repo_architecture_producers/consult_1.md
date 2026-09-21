# Consult 1: completion check for slice 014

**Outcome: complete.**

## Acceptance criteria against the repos

| AC | Implementing work, as checked on main |
| --- | --- |
| V01 | HelmCharts' diff is one test (0c37dbb, `tests/test_gen_architecture.py` only), so its static file and generator are untouched. KubeCoderDeploy a8d3e4f carries the copied layer and the `kubecoder-deploy` producer. |
| V02 | KubeCoderDeploy `Jenkinsfile.architecture` runs `git branch: 'prd'` and `--stage prd`. No pipeline or gate makes a dev artifact. `architecture.yaml` sets `introduced: '2026-06-17'`. |
| V03 | P4 and P5 both recorded the handover check as green: 9/16 on each side, 4 ARCH-13 exclusions, and the tunnel-reclaim gap. The test phase re-runs it. |
| V04 | HelmCharts `test_a_release_deploy_config_reports_no_chart_for_is_left_out_of_the_artifact`. It was witnessed red under two mutations. No patch was needed. |
| V05 | Both repos have `Jenkinsfile.architecture` (aac-tools container, generate, `arch-validate`, archive `docs/architecture/*.yaml`) and `/docs/architecture/` gitignored. Each `.architecturerc` has exactly three keys: `generated`, `sources: [architecture.yaml, chart/, config/prd/]` and `instructions`. |
| V06 | ArgoCDDeploy owns `ss:argo-cd` and `ss:redis`. The relay is `app:webhook-relay` with two upstream wires (server and applicationset-controller). 15 elements, 25 relations, zero gaps, validated. |
| V07 | `docs/runbooks/argocd.md` § "Giving an app its own architecture producer" covers steps 1–6, the `<app>-deploy` rule, `.architecturerc`, registering with `repo:` after the first green build, registering before the flip at a handover, and the promotion-branch gap stated as a fact of today. |
| V08 | No phase touches `pipeline-producers.yaml` or creates a job. Close-out A1 and A2 carry the jobs and the `repo:` registrations. |
| V09 | JenkinsPipelineUtils a4d5ba1 adds `aac_tools(name)`, the `python` entry's shape with `registry:5000/aac-tools` as the floating image. |
| V10 | ArgoCDTools bdd280e deletes the fixture, `--annotations` and `HandoverFixtureTests`. The successor is named in the P5 record, and nothing references the fixture any more. |
| V11 | Both repos' `test` verbs end with the two `cexec aac-tools` statements. The sweep is GREEN for both. |
| V12 | Two regenerations were byte-identical in both P2 and P4. |
| V13 | `argo-cd/decisions.md` has D50, and O2 says `gen-architecture` is decided. `design.md` and `phases.md` cite D50. Slice 012's "Hard ordering against slice 014" states D2's order. |
| V14 | The DockerImages 78f31ba header is corrected. P3 recorded the parsed YAML as identical. |

## Rulings

R1–R7, D1, D2, the settled ruling and the review rulings Q1, B1, A1 and A2 are each carried by a phase. None of the eight done-records admits a leftover. P1's missing gate is the planned canary, which A1 carries.

## Residue fixed in this session

- **S8** was a sentence in `docs/runbooks/argocd.md`, a file P7 touched. It gave a new app's dating rule as the repo's first commit, while its ArgoCDDeploy worked example uses the first commit adding `chart/`. I aligned the sentence with the example. This is a doc correction with no behaviour change: `introduced` feeds no id. Committed as Ansible 7c4b8e6, unpushed. Root has no lint statements. I struck S8 with that commit.

## Close-out reconciliation

- **A1 and A2:** each has a note on its push precondition. JenkinsPipelineUtils a4d5ba1, ArgoCDDeploy 844ed05 and KubeCoderDeploy a8d3e4f were unpushed on local main at this consult. None of them is push-held, so the run's push step carries them.
- **A3 (new):** the operator pushes the two held repos, ArgoCDTools bdd280e and DockerImages 78f31ba. Neither push gates A1 or A2: ff7e443, the list form, is already on origin.
- **S5:** noted that the how-to already names where the schema lives. What remains is a design call between carrying the contract and pointing at it, so I left it for the operator.
- **S1, S2, S4, S7:** kept. S1 and S4 are generator limits, and S1 is explicitly out of scope. S2 is the environment manifest, outside this slice's diff. S7 would add a new retirement procedure, not correct an error. None is owed by the plan, and each costs the operator one word.
- **S3 and S6:** already struck by their code-writers, each superseded by the entry that follows it.

## Commits the sweep has not seen

- Ansible 7c4b8e6, a one-sentence runbook change. The driver's sweep re-runs on it.
