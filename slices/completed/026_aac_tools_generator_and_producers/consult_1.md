# Consult 1: complete

All eighteen phases are stamped done, and every row of the loop-tail sweep that ran is green. No
requirement or ruling in the plan, and no acceptance criterion, lacks a phase that delivers it.

## Acceptance criteria → delivering work

| Item | Delivered by |
|---|---|
| V01 | P1 (routed-container pick, `InHouseExposureTests`) and P5 (KubeCoderDeploy mapping; prd generation shows no gap and `kubecoder.home` → `svc:kubecoder-controller-api`), pushed in P9b (`c776662`) |
| V02 | Owed after the KubeCoder promotion (close-out A2) |
| V03 | P2 (container scoping, ConfigMap env, the upstream hard fail kept) |
| V04 | P6, pushed in P9a (`65872b9`). The published dataset carries 5 capability Realizations and 3 redis Serving edges (collector #2242) |
| V05 | Ruled out (D2). P4 kept the runbook warning. Closing ANS-85 is close-out A1 |
| V06 | P3 (`--help` is the docstring; `HelpContractTests`) |
| V07 | P4 (runbook, argo-migrate) and P9a–c (48 `.architecturerc` files and 2 headers, all on origin/main with three keys each) |
| V08 | P8 (update-architecture agent, `.kubecoder/config.yaml`) |
| V09 | Owed after the Architecture restart and ARCH-14 (close-out A3) |
| V10 | P3 (49-stage comparison), P4 (F1 check, publication, the stop) and P5 (sidecar `--help` check) |
| V11 | P7, pushed in P9c. The relation is in the dataset after collector #2262 |
| V12 | P10 (28 carriers; gitblit and GitHub agree) and P11–P13b (27 migrated and pushed). The Ansible carrier is `b92d01a` |
| V13 | P9a–P13b ledger rows, all done except Ansible's |
| V14 | P8 |
| V15 | P1–P3 (7 + 5 + 4 + 3 new tests, none deleted). S4 and S6 ask for stronger regression guards, but each behaviour has tests, so they are not owed |

## Left to the test phase (by the plan, not a new phase)

The testing strategy's step 4 pushes what the slice committed. These commits are still
unpushed:

- **Ansible** `8594ab5` (P4) and `b92d01a` (P10). The branch is 4 commits behind origin/main.
  Its push is V12's and V13's last carrier row: AaC/Ansible must build green with the
  toolchain's `arch-validate`.
- **Architecture** `ae5107f` (P8). The branch is 2 commits behind origin/main. The push runs
  AaC/Architecture and redeploys the site.
- **ArgoCDTools** `ef3e662`, this consult's comment-only fix. The push rebuilds and republishes
  aac-tools and argocd-hook and writes no pin.
- **ArgoCDDeploy** `c005fb5`, this consult's comment-only fix at the repo root. The push runs
  AaC/ArgoCDDeploy and a no-op sync.

## Close-out reconciliation

- **Struck:** B1 (fixed by Architecture `a2dabd2`), B2 (P12c `c38bd6f`), S13, S14 (both moot
  once B1 and B2 are struck), S5 (ArgoCDTools `ef3e662`), S9 (ArgoCDDeploy `c005fb5`) and S11
  (P7 review).
- **Noted:** S8 (moot), and S7, left open because it needs a product decision (honour
  `lifecycle` or document the override).
- **Unchanged:** S4, S6 and S7, the regression-guard and contract-wording suggestions, plus S1,
  S2, S3, S10 and S12, which are out of scope. A1–A9 are operator actions.
