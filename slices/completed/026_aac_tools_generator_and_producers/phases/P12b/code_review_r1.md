# P12b code review — round 1

**Readiness: ready to merge, with no findings.** The branch diff in the phase's `Target: root`
(`b92d01a..HEAD` on `phase/026-P12b`) is empty, as the attachment's § The push sweep expects. So
this review covers the six carrier commits the phase pushed and the ledger rows that record them.

Each carrier commit swaps `containerTemplates.python` for `containerTemplates.aac_tools` in
`Jenkinsfile.architecture` and runs `arch-validate` there. Each also runs
`cexec aac-tools arch-validate` in whatever local gate called the copy: IntercomServer's and
ScanToPdfClient's `lint`, MyDownloadsClient's `lint`, and SSEGateway's second `lint` step. Every
`scripts/arch-validate.py` is deleted, including both of DHCPApp's copies. The stdlib-only
comments that described the copy are gone too. The commits are IntercomServer `4a08ad1`,
FieldnotesApp `1ee1929`, DHCPApp `9bae8d6`, ScanToPdfClient `215e107`, SSEGateway `41cf1b5` and
MyDownloadsClient `fc6c74b`.

At the pre-migration parent of each commit, every reference to the script other than the
`SEED-NOTES.md` history lines is replaced at `origin/HEAD`. The P11 ruling keeps those history
lines. No pushed default branch still holds an `arch-validate.py` file.

IntercomServer and SSEGateway declare `aac-tools` in their environment config, and close-out A6
records their restarts. ScanToPdfClient and MyDownloadsClient gate in the ScanToPdf and MyDownloads
packager environments. Both packagers declare `aac-tools` at `origin/HEAD`.

**What I checked against the live systems:**

- **Only the slice's commit was pushed (Ruling F1).** Each push was one commit on top of the
  cloned or fetched origin, per the clone reflogs. FieldnotesApp's later `97777d7` is the
  operator's push.
- **Architecture builds.** The consoles of `AaC/FieldnotesApp` #5 (`1ee1929`) and #6, of
  `AaC/SSEGateway` #19 and of `AaC/DHCPApp` #29 each run `+ arch-validate …` inside the
  `aac-tools` container and finish SUCCESS. DHCPApp's runs twice, once for backend and once for
  frontend.
- **FieldnotesApp.** `FieldnotesApp` #40 errored at `Validation failed: exit code 1`, before
  kaniko, so no image was built and nothing was pinned. `FieldnotesApp` #41 built `97777d7`, a
  descendant of `1ee1929`. It finished SUCCESS and pinned FieldnotesDeploy `b7daf6f`.
- **Rollouts.** Every Application the ledger names is Synced/Healthy right now at the revision
  the ledger records: `intercom-prd`, `fieldnotes-prd`, `dnsmasq-prd`, `scantopdf-prd`,
  `electronics-inventory-prd`, `iot-prd`, `zigbee2mqtt-prd`, `media-prd` and
  `webathome-org-prd`. `webathome-org-prd` is at the latest site pin, `526219d`.
- **The migrated gate command.** I ran `cexec aac-tools arch-validate docs/architecture/*.yaml`
  in the IntercomServer, SSEGateway, ScanToPdfClient and MyDownloadsClient clones. It validates
  each artifact and exits 0.
- **The stop rule and Ruling D5.** The run stopped at #40's red, with SSEGateway and
  MyDownloadsClient still unpushed. It resumed only after the operator's D5 answer.

The run did not rebuild `1ee1929`, which D5 names. Instead it accepted the operator's green #41
on a descendant that carries the migration. That still gives D5's condition, a green FieldnotesApp
build with its rollout healthy, before the sweep carried on. Close-out N8 records the deviation,
so it is not a finding.

## Findings

None.
