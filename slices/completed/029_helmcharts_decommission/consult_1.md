# Consult 1: completion

**Outcome: complete.**

## AC → delivering work

| AC | Delivered by |
|---|---|
| V01, V03 | Pre-planning work (HelmCharts eeceac0/6e8a054/91ce931, DockerImages 6041476/cbf7771, VersionPollerDeploy 9846433); the test phase re-checks it |
| V02, V06, V17 | P1: D44 amended (spot-checked: "Amended 2026-09-26 (slice 029): the module stays in the archived HelmCharts"), D63/D64/D65 |
| V04, V05 | P2: Architecture a4402f6 + d7c4878 |
| V21 | P3: JenkinsPipelineUtils 6f87d09, with V21 amended by the mid-run ruling (ANS-144) |
| V10, V11, V12 | P4: ArgoCDDeploy 19e40d3/50fd69a, `tools/registry-equivalence.py` passed against prd |
| V13 | P5: ArgoCDDeploy 4afb8fb |
| V14 | P6: `docs/runbooks/registry-switch.md` (eleven steps, the dead-after list); D64 and phases.md name its path (AnsibleSpecs d05e22d) |
| V16, V19 | P7: Ansible b56fc9a; `stuck_fields.py` runs from `support/argo-migrate/`, and nothing runs it from `handovers/` |
| V07, V08, V09 | P8: Ansible 8b8fdff/f7877e4 |
| V18, V19, V20 | P9: Ansible 5cfdb0c; step 11's grep finds six notes. N3: the handover flip was removed, not left without a note |
| V22, V23 | P2 + P3; HelmCharts has no commit since the pre-planning cleanup |
| V15, V24 | Owed after the operator's registry switch (A1, A2) |

All phases are merged on each repo's `main` and not pushed.

## Residue fixed in this session

- Ansible `ca536a6`, docs only; `kc project lint` is green:
  - k8s-rebuild.md: the `configs/dev` archive is still to come (S28).
  - design-philosophy.md: names `tools/ai_workflow/test_track_build.py`, the unit test no gate runs (S26).
  - kubecoder-cutover.md: its P3 step numbers are dated (S27), and its slice 012 link points at `completed/` (part of S22).
- AnsibleSpecs `150fb1a`: the estate register's seven moved links (S6).

## Close-out reconciliation

- Struck: S6, S26, S27, S28.
- Noted:
  - S22: the link is fixed. slice-testing-strategy.md and CLAUDE.md's KubeCoderDeploy line stay open.
  - S25: stage-manifests.yaml renders a fifth Secret, `step-ca-ssh-host-ca-password`. The chart's `ca.json` uses `/home/step/...` pod paths and carries `ssh.hostKey`, so a local `ca.json` cannot be dropped in as it is. The fix is procedure work, not mechanical.
  - N1: the ruling came in, and its Consequence line is historical.
  - S8: P6's AnsibleSpecs edits landed as d05e22d.

## Not appended

S25 is the closest candidate. It is a regression P9 introduced into an R7 runbook. It is still a defect in delivered work, not an undelivered requirement, and the P9 reviewer rated it Minor advisory because the ceremony only runs after a CA loss. A phase would cost an executor round, a review and a consult. The close-out entry costs the operator one word, and its note now carries the facts the fix needs.
