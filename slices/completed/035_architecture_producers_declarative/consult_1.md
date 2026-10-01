# Consult 1 — slice 035

**Outcome: complete.**

## Acceptance criteria against the work

| AC | Implementing work | Left for |
| -- | ----------------- | -------- |
| V01 | P2 (50), P3 (25), P4 (3): 78 full declarative files | test phase: "on origin" after the push |
| V02 | P3 (five apps in their own repos), P1 (types index); ModernAppTemplate 0 commits ahead | test phase: builds green |
| V03 | P1 `vars/architectureProducer.{groovy,md}` + test; 78 validate/archive, 50 deploy files generate | test phase: on origin |
| V04 | every file declares `disableConcurrentBuilds(abortPrevious: true)` and `githubPush()` | test phase: trackers after the churn |
| V05 | UHC file declares `abortPrevious: true` (P3) | test phase: the hand-started second build (S2) |
| V06 | no `git branch:`/`credentialsId`, `checkout scm` and one library line in all 78 | — |
| V07 | P4: Ansible's file on `jenkins-agent` alone (`5b4b984`) | test phase: AaC/Ansible green |
| V08, V09 | the plan puts the push, the collector pause and the check in the test phase (Ruling P1, Ordering constraints) | test phase |
| V10 | P1: no rule heading in `docs/pages/guide/` changed (diff re-read), references call the steps | — |
| V11 | linter 50/25/3 in P2–P4, reviewers re-ran it | test phase: on origin |
| V12 | P4: `withVault` around the generator's `sh` only | test phase: AaC/IoTSupport green |
| V13 | P2: PipelinesDeploy on the steps | test phase: green |
| V14 | P2: KubeCoderDeploy's commit on `main` | `owed_after` the operator's promotion (close-out A1) |
| V15 | P5 | — |

Re-checked here by script over the ledger's 77 rows: each file exists, lacks `podTemplate`,
`node`, `git branch:`, `credentialsId`, `containerTemplates` and `kaniko`, has `checkout scm`,
the guard, the trigger, exactly one library line, `validate` and `archive`. Each clone is exactly
one commit ahead of origin, with its head equal to the ledger's commit and the file clean. All 77
passed. Ansible's file is checked the same way.

## Fixed in this session (mechanical residue, files the slice touched)

- JenkinsPipelineUtils `0d640cf`: `vars/architectureProducer.md` says `archive` fails only when
  the entries together match no file. With several entries, one that matches nothing is skipped
  (close-out P3). `kc project test docs` passed.
- AnsibleSpecs `d878907`: report.md's J16 note gives the measured 47–93 lines next to Ruling D2's
  ~40-line estimate (close-out P5).

Both commits are local, and the test phase's push takes them with the rest. JenkinsPipelineUtils
is now two commits ahead of origin.

## Not owed, left as routed

- B1 (argo-migrate's producer template): the template is not a producer, so it is outside R1's
  scope. It goes to the wrap-up.
- P2 (Architecture producer manual): this is a repo the slice does not touch. It is a card request.
- B2: closed, because it needs a fault.

## For the test phase

The project's `docs/slice-testing-strategy.md` describes only the `iac-on-push` push. The plan
defines this slice's push and check in Ruling P1, the Ordering constraints and V05, V08 and V09:
- pause AaC/Architecture
- push JenkinsPipelineUtils first, then the ledger's repos and Ansible
- wait for quiet, treating a stuck item as the slot leak
- build UHC by hand
- re-enable the collector and build it once
- run one `lastBuild` pull

The test phase owes that procedure, not a plan phase.
