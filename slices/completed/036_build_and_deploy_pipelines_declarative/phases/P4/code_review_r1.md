# Slice 036 P4 — code review r1

P4 is ready to merge. The phase's `Target: root` diff on Ansible is empty by design. The work is one
unpushed commit in each of 13 `/work/scratch` clones, read through `migration-ledger.md`. All 14 rows
match each clone's `main` head, each clone has exactly that one commit ahead of `origin/main` with a
clean tree, and ModernAppTemplate has no commit.

The eight firmware files are `firmware.groovy` with their own names; ThermostatProxy adds the
`opentherm_library` clone on `master`. Intercom is `firmware-versions.groovy` and ElectronicsInventory
is `modern-app.groovy`, both byte-identical apart from the reference files' section markers.

Every effect of the old files is kept:

- **Firmware:** the same `idf` image, the same esp-libs and opentherm clones into the same
  directories, the same build and upload commands through `espFirmware`, and Intercom's
  build-then-upload order per version. The secret forwarding and the pod-wide `withVault` are gone.
  The four self-clones are now `checkout scm`. Their only git dependency, `CMakeLists.txt:6`
  `git rev-parse --short HEAD`, works on a detached HEAD.
- **Apps:**
  - Each job keeps its images, tags, pin repo, values file and keys.
  - The `modernApp.test` arguments reproduce each old validation Job. I rendered IoTSupport's and
    FieldnotesApp's arguments through `testArguments`/`jobManifest` (groovy-all 2.4.21) and diffed
    them against the old inline YAML. Two differences remain, neither from P4: P3's `job-name`
    pod-template label (Kubernetes sets the same label itself) and the dropped `imagePullPolicy` on
    `rustfs:latest`, which defaults to `Always`.
  - `git-rev` now ends in a newline, and `vite.config.ts:15` trims it.
  - IoTSupport's `withVault` wraps only the `modernApp.test` call, with the admin client in
    `secrets:` (Ruling P3, V22).

**Checked against live state (all read-only):**

- **Keycloak values:** the four inlined values equal the controller's live global variables. No
  other Jenkinsfile in `/work` or `/work/scratch` reads them, so the test phase can delete them.
- **Headers:** every FILE-3 header matches its job's live `config.xml`: URL, `*/main`, script path,
  push trigger, no parameters and no SCM extensions, so the submodules stay uninitialised.
- **Lint:** all 14 files pass the controller's declarative linter.
- **Timeouts:** the controller sets the pipeline-level 60-minute timeout only after `Running on`
  (seen in `AaC/IoTSupport`'s last log). The ~4-hour firmware runs and 40–56-minute app runs in the
  history were agent waits before the first stage. After the agent starts, the longest runs are
  about 32 minutes (ElectronicsInventory) and 3 minutes (firmware), so the 60-minute timeout has
  room.

The Ruling P5 doc lines are fixed, and no `containerTemplates`, positional `helmCharts.kaniko(` or
`Run validation` reference is left in the 13 repos. The Helm-deploy wording is already close-out P4.

## Findings

None.
