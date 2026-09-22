# Consult 1 (completion): complete

**Outcome: nothing outstanding.** Every item the plan owes has shipped. What is left is the
operator's live cutover, which is out of scope by the plan's own terms.

## Each criterion and the work that meets it

- **V16, V17: done by P1** (KubeCoderDeploy `4bb7823`).
  - The five pinned containers declare `IfNotPresent`, and the gate asserts the declared value.
  - The replay goes up to `fb49c5c`, and the README records that copy point.
- **V15: done by P2** (`f6a8fba`), `Jenkinsfile.promote`.
  - It runs D47's order: retag, then fast-forward `prd`, then `release-<m>`.
  - Every refusal happens before the registry is touched.
  - It holds the GitHub credential only.
- **Every other criterion: done by P3** (Ansible `a411915`), `docs/runbooks/kubecoder-cutover.md`.

| Criterion | Where the runbook meets it |
| --- | --- |
| V01–V03 | The state surgery; the Facts table; D4's relay-webhook check |
| V04 | The no-destroy plan, which uses the Q1 credential route; B3 checks the hook's Terraform version |
| V05 | B1 and the chart replay check, which runs before each diff review |
| V06 | D2 and P4 spell out the entries in full. X2 comes after prd's surgery and gives the audit's actual listing (B1) |
| V07 | D2 |
| V08 | The pre-flight runs after the replay and before the review. The review expects P1's change and gives prd's set. argocd.md's table and residue note are corrected |
| V09 | D8, and P10, which the operator does alone and which names its resume point |
| V10 | D9 and P11 |
| V11 | D10 |
| V12 | P13: a promotion, a real pin-commit revert, and a roll-forward |
| V13 | X1–X3 |
| V14 | D1 and P12 |
| V18 | The sequence: B2 before D8, D1 before D2, the flip before the surgery, and P2 → P3 → P4 |
| V19 | "Let it sit" |
| V20 | Conventions and the plan's command (see B2 below) |
| V21 | Its own file. Each stop names the state and the way back (WB-1 to WB-3) |
| V22 | Exit, points 1–3 |

## What stays open, and why none of it is a phase

- **The live execution** of every step belongs to the operator (plan, "Not in scope").
- **Q1** is already a ruling for the operator. B3 stops as the estate stands, and the runbook
  names both ways forward.
- **B2** bears on V20. Only the no-destroy plan is covered by "loaded inside the operator's own
  command". The pre-flight also writes the stage's ESO Secrets to a file, and the runbook does not
  say whose keystroke that is. The values reach a file, not a transcript, and the fix is one
  sentence or one filter. That makes it a one-word ruling for the operator, not a phase. I added a
  note to B2.
- **B4, S6's F2 note and S9** are small command corrections in files this slice touched. Each one
  changes a step, not a comment, so they stay in the report for the operator.
- **A1, B1, N1, S1–S3, S5, S7 and S8** are out of scope or advisory. I added a note to S5: the
  README carries no false claim, and the false sentence is only in `project.yaml`, which this
  slice did not touch.

## Mechanical residue, fixed in this session

- **KubeCoderDeploy `a340167`.** The images comment in `chart/values.yaml` now says the five
  pinned containers declare `IfNotPresent`. This was S4, now struck. `kc project lint` and `test`
  are green.
- **Ansible `2b873dc`.** X1 of `kubecoder-cutover.md` now expects Helm's header row from
  `helm list`, not empty output. This was B3, now struck. `kc project lint` is green.
