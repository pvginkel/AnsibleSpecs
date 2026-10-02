# Consult 1 — slice 036, after P11

**Outcome: appended (P12).**

## What was checked

- Each of the 26 acceptance criteria in `verification.json` against the phase that implements it.
  - V01–V10, V14, V15, V17, V19, V20, V22 and V26 have a phase's commits behind them (P1–P11).
  - The live halves of V03, V04, V11, V12, V13, V16 and V18 are the test phase's, by the plan's
    Ordering constraints: the snapshot, the renames, the pause, the push, quiet, the check, the
    `KEYCLOAK_*` deletion and the closing diff.
  - V23–V25 are `owed_after` and have close-out actions A2–A4.
- A sweep of the 52 migrated files (the ledger's 42 rows, Architecture's 2, Ansible's 7):
  - every one is a `pipeline {}` file;
  - each has the 60-minute timeout, except DockerImages (180 minutes) and the six iac-controller
    files (4 hours);
  - none declares `buildDiscarder`;
  - only `Architecture/Jenkinsfile` calls `properties`;
  - none calls a `containerTemplates.` describable or the positional `helmCharts.kaniko(`.
- The close-out report's open entries.

## What is owed: B2

The eight firmware files P4 wrote inherit `jenkins-agent-large` with their own `yaml podYaml(...)`
and no `yamlMergeStrategy merge()`. The guide's two firmware reference files, which the files copy,
have the same shape: `docs/examples/firmware.groovy:15` and `firmware-versions.groovy:14`.

- The template is YAML only: a required node affinity on `homelab.local/performance=high` and a
  toleration for its taint. Only srvk8s4 carries the label and the taint.
- The plugin's default strategy, Override, drops that YAML. P5 review r1 witnessed this, and P5
  round 2 confirmed it in the Script Console.
- The old scripted files kept the YAML. After the push the firmware builds would run on srvk8s1-3,
  beside prd's workloads, with nothing saying so.
- That breaks V21 (behaviour kept) and the purpose of POD-3, which names the firmware jobs as
  `jenkins-agent-large` jobs.
- P5 fixed its own four files. B2 recorded the rest, and no phase fixed them.

A phase costs one executor round and one review round. The alternative is to fix it after the
push: that means eight more firmware pushes, each one an OTA re-flash, and an operator OK for each.
So the fix comes before the push, as P12, targeting `../JenkinsPipelineUtils`:

- POD-3 and its **Why**;
- podYaml's page, the firmware type page and `espFirmware`'s snippet;
- both firmware reference files;
- the eight ledger commits amended in their clones, with the ledger's SHAs updated.

## Close-out reconciliation

- **B2:** struck, absorbed by P12 (AnsibleSpecs `b6f69b8`).
- **P2 and P3:** struck, resolved as mechanical residue in JenkinsPipelineUtils `1fa9853`. These
  were the stale internals lists on `vars/podYaml.md` (`containerName`) and `vars/modernApp.md`
  (`secretsScript`); `kc project lint` is green.
- **P11, new:** the KubeCoderConfig `jenkins-pipelines` skill's POD-3 brief (`SKILL.md:101-103`)
  names the merge only for `kaniko`. That becomes stale once P12 lands, and no later phase targets
  KubeCoderConfig.
- The other entries stand as written. P4–P10 are prose in repos or files P12 does not touch, B1 is
  a nit outside the plan's text, and T1 predates the slice.
