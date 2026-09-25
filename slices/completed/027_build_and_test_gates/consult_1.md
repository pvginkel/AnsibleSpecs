# Consult 1 — completion (slice 027)

Outcome: **complete**.

## Acceptance criteria → implementing work

| AC | Work | Checked |
|---|---|---|
| V01 | P1 `e7f51bc` | `tests/pom.xml`: groovy-cps `4376.v30c8c00684a_3`, groovy-all 2.4.21, groovy-sandbox 1.34.1, guava transitive, repo.jenkins-ci.org only; trusted shell per the done-record |
| V02, V03 | P1 | both reds and the `vars/gateProbe.groovy` 11th case witnessed (done-record) |
| V04 | P1 | tracked files are `.gitignore`, `.kubecoder/`, `tests/…`; `/tests/target/` ignored |
| V15 | P1 | one `<properties>` block, comment ties it to the controller's workflow-cps |
| V08, V14 | P2 `a43f45e` | `iac_toolchain` at `vars/containerTemplates.groovy:46`, `modern_app_dev` still at `:89` |
| V05, V06 | P3 `8bf2d0f` | `Test` stage in `container('iac')` between clone and both kaniko stages |
| V07 | test phase | live first-run witness after the push; not a plan phase |
| V09–V12 | P4 `5a680b4` | `tests/alert-rules.sh` + 5 rule-group files; node-memory file carries all six 018 scenarios (starvation, wedge + dip, reboot, healthy tight node, helm_sh_chart overlap, no carry-over after reboot) |
| V13 | P5 `4e91587` | D61 rewritten |

## Why nothing was appended

- S4, the major-fault paths' mutation gap, sits beyond the D2 ruling's bar of every alert with a
  firing and a quiet case. The P4 reviewer rated it advisory and signed off. It stays a suggestion,
  and the consult's reasoning is noted on the entry.
- S2 (the `invokeMethod` false-green) is hypothetical and matches no file today. It stays a
  suggestion.
- Q1 needs the operator's ruling, not a phase.

## Fixed here (mechanical residue)

- ArgoCDTools `c32a27c`: the Jenkinsfile comment named helm as a suite dependency. It now names
  git, openssl and terraform, since `argocd-hook/tests/test_terraform.py:142` runs terraform. This
  resolves S3, which named only git and openssl.
- AnsibleSpecs `7844b5c`: D61 "PrometheusDeploy's checks" now reads "PrometheusDeploy's test verb
  checks", with the rest of the paragraph rewrapped (S5).

## For the doc phase (from the done-records, not re-filed)

- ArgoCDTools README `:45` and `:263` still describe the job as one stage per image, with no test
  stage (P3).
- The s3-mirror, youtrack-backup and backup-freshness comments in PrometheusDeploy
  `config/prd/values.yaml` still name HelmCharts' retired tests as the ones that walk the edges
  (P4). The operator set them in `d4faa57`.

## Close-out reconciliation

Struck: S3 and S5 (fixed here), and A1 (done before P1 r2). Noted: A2 (028 has not run, and
PrometheusDeploy is ahead of origin by `5a680b4` alone) and S4 (why it is not a phase). Left open:
A3, N1, Q1, S1, S2 and S4.
