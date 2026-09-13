# Consult 1 — completion: `complete`

## Acceptance criteria against delivered work

| AC | Delivered by |
| --- | --- |
| V01 layout, V02 copy + recorded commit, V03 library dependency, V04–V05 deployment identity, V06 `global.environment`, V07 Namespace, V08 hook Job, V09 whitelist check | P3 (KubeCoderDeploy `86656d7`, `32520a2`). HelmCharts `charts/kubecoder` and `configs/prd/kubecoder` have no commits since `65ca9db` and no `release.yaml`; the README records `65ca9db` and a replay command. |
| V15–V18 pins, V19 chart-side always-pull drop | P4 (`6002b64`), pinned to `dev-511` |
| V10 Terraform (F2 `zfs_pools`), V11 webhook | P5 (`9d6c448`) |
| V12 webhook secret in the hook environment, V13 no namespace grant | P1 (ArgoCDDeploy `d2aa093`) |
| V20 reconciler-aware orphan audit | P2 (HelmCharts `869e19b`) |
| V21 diff-preview procedure | P7 (Ansible `3194f3f`, `77ef98d`). The operator's run is A3. |
| V14 manifests | KubeCoder `1e523e79`, on `origin/main`, done before the run (settled 13). The Ansible-side line is A1. |
| V22 no `prd` branch | KubeCoderDeploy has only `main` |
| V23 boundaries | `/work/Charts` has no commits since 2026-09-12, and no phase targets KubeCoder |
| V24 gates | KubeCoderDeploy `.kubecoder/project.yaml` (deps, `helm lint` per stage, render test, `fmt`/`validate`/`terraform test`). All sweep rows green. |

The plan has no P6. Plan review F1 removed the KubeCoder-manifest phase because its gate cannot run here, and settled 13 records the line as pushed before the run. Nothing depends on it.

## Close-out reconciliation

- **S5**: struck. It was mechanical comment residue in a file this slice touched. Fixed in KubeCoderDeploy `021cc1b` as a comment-only change with line numbering kept; `kc project lint` and `test` both re-ran green.
- **S1**: noted. Backlog slice 014 already plans KubeCoderDeploy's architecture producer. The open point is ordering it against 012's deletion of `charts/kubecoder/`.
- **S11**: noted. Ruling D3 makes this slice's R14 acceptance the chart render only. Slice 012 still expects the `Always` drop to show at cutover and has to choose how to make it live.
- **S10**: checked, left as filed. KubeCoder's chart and the library read no `.Release.Name`, so P7's "renders as the generated Application will" holds for KubeCoder. The entry is for later migrations.
- **S3, S8**: gate hardening that no AC requires (V20 and V24 are met). They stay as suggestions.
- **S9**: a correction to slice 012's text, not this slice's files. Left for the operator's triage.
- **B1, S2, S4, S6, S7**: out of scope or inputs for later slices. Unchanged.

## For the close

These repos are ahead of their origins and not pushed: KubeCoderDeploy (+5, including `021cc1b`), ArgoCDDeploy (+1), Ansible (+2) and AnsibleSpecs. Local HelmCharts `main` is also one commit behind `origin/main` (`db24d33`, an unrelated elasticsearch probe change), so it needs a rebase before its push. A3 cannot run until KubeCoderDeploy is pushed.
