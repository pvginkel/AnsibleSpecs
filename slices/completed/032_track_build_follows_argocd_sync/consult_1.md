# Consult 1 — completion, slice 032

**Outcome: complete.**

## Criteria against the work

| V | Implementing work |
|---|---|
| V01 R1 follow | P4: `follow_deploys`, masked `****` owner parsed (`test_the_pin_line_is_read_although_its_owner_is_masked`), per-app summary |
| V02 on by default | P4: `--no-follow-argocd` opt-out; `TestDefaults.test_the_follow_is_on…`, `TestRun.test_a_green_build_is_followed_into_argo_cd_by_default` |
| V03 missing clone | P4: exit 4, one `git clone` line per repo, `.kubecoder/config.yaml` hint (track_build.py:1245-1249); `test_missing_clones_stop_before_anything_is_waited_on` |
| V04 prd promotions | P1: `Jenkinsfile.promote` prints `pushed to prd` / `already on prd: nothing pushed`; P4: `test_a_promotion_follows_kubecoder_prd_to_the_promoted_commit` |
| V05 no handoff line | P4: remark at :1303, build's own exit; `test_no_handoff_line_*` |
| V06 appear timeout | P3: 300 s, help text; `test_appear_timeout_defaults_to_five_minutes` |
| V07 matching | P4: `TestMatching` (KubeCoder dev/prd, keycloak shared branch, three-source `$values`) |
| V08 done means live | P4: OutOfSync-over-finished-op and Synced-no-change tests |
| V09 stops | P4: exits 5/6/7, no-match reported; docstring lists 0,1,3-7 and precedence |
| V10 diagnosis | P5: `argocd_<app>_<sha7>.log`, summary names it; `TestDiagnosis` |
| V11 read-only, no kubectl | P4: urllib + kubeconfig bearer token, GET/LIST only |
| V12 single source | P2: `tools/ai_workflow/` deleted; docs repointed |
| V13 gated suite | P3: `kube-coder-dev-local-home` component; sweep green |
| V14 KubeCoder docs | P6: deploy-operations, slice-test-plan, card-pass, card-runner (+ live-verification) |
| V15 live | P4 record: #551 → exit 0; EI #255 → exit 4; DI #2548 → exit 4 naming nine repos |
| V16 live promote | owed_after the operator's next Promote-PRD, close-out A1 |
| V17 roll deadline | P4 `--roll-timeout` 600; P5 same evidence at the deadline |
| V18 pushed nothing | P4: `TestNothingToWaitFor` (already-carries against main's head, record-only promote) |
| V19 PyYAML | P3: `python3-yaml` in kube-coder-dev-base apt list |

## Leftovers, and why none became a phase

- **B2** (major): a transport error during the follow gives a traceback and exit 1. It is a real
  robustness gap. No requirement or criterion names it, and the Jenkins client had the same hole
  before this slice. Three agents saw it and none blocked on it. Noted with the fix's scope.
- **B3** (minor): V03 (R3) and V18 (F1) meet here. The code takes R3's side, so which rule wins
  is the operator's call. Noted.
- **S2, S3, S4, B1**: advisory or out of scope, and left as they are.
- **Doc-phase items** from done-records: P2's missing mention of the Argo CD follow in
  live-infra-access.md, now folded into the S1 fix, and P6's pipeline-dependencies.md:26, which
  still lists only `$JENKINS_TOKEN`. The latter is the doc phase's own work list.

## Mechanical residue fixed here

- Ansible `94be15b`, docs/live-infra-access.md, a file P2 touched: the tracker "ships in the
  local-home image, built from DockerImages `kube-coder-dev-local-home/`, where its tests live
  too", and the sentence names the Argo CD follow. `kc project lint` green. S1 is struck.
