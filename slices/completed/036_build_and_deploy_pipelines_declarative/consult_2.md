# Consult 2 — slice 036, after P12

**Outcome: complete.**

## What was checked

- **P12 against its brief.**
  - JenkinsPipelineUtils `0a0d472`: POD-3 requires `yamlMergeStrategy merge()` for `kaniko` and
    `jenkins-agent-large`, and its **Why** says what each template holds.
  - The eight firmware clones each carry the merge on their amended commit.
- **The ledger against the clones.** For all 42 rows:
  - the branch's tip is the ledger's SHA;
  - the clone is exactly one commit ahead of its origin branch (`main`, `test` for TrelloMcp,
    `master` for the four repos to be renamed);
  - the working tree is clean.
- **Placement kept (V21).**
  - Every migrated file inherits the same templates as its parent commit's file.
  - All 12 `jenkins-agent-large` files declare the merge. All `kaniko` files do too: the ledger's,
    `Architecture/Jenkinsfile` and `Ansible/Jenkinsfile.iac-image`.
  - The live pod templates were read from the Script Console (read-only): `jenkins-agent` has no
    YAML and no containers. So the files that inherit only `jenkins-agent` and write their own
    YAML without the merge lose nothing: IoTSupport's and the renamed repos'
    `Jenkinsfile.architecture`, ScanToPdfServer, YouTrackConfiguration, Promote-PRD and HA Fleet.
- **The acceptance criteria.** Consult 1's mapping still holds, and P12 closed the one gap it
  found (B2).
  - The live halves of V03, V04, V11, V12, V13, V16 and V18 are the test phase's.
  - V23–V25 are `owed_after` (A2–A4).

## Residue fixed

- **Close-out P11** was the KubeCoderConfig `jenkins-pipelines` skill's POD-3 brief, which named
  the merge only for `kaniko`.
  - It went stale when P12 landed, in a file P10 had already touched.
  - It is fixed in KubeCoderConfig `9e26934`, with the repo's required plugin bump to 0.10.3.
    `kc project lint` is green.
  - It rides the one push, so no later KubeCoderConfig push is needed. P11 is struck as resolved.

## Left in the report

- **P6, P7, P9 and P10** are stale stage-label mentions in files the slice's commits did not
  touch: HomelabTerraformProvider's README, KubeCoder's docs and scripts, and Ansible's runbooks.
  They are not residue. P10 and the Ansible half of P7 are the doc phase's.
- **P8** corrects guidance that predates the slice.
- **I1** is a true comment in four P5 files. Dropping it would cost four more amends and four
  ledger edits before the push, for no change in behaviour.
- **B1, T1, P1, P4 and P5** stand as written.
