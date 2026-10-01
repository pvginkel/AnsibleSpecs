# P5 code review — round 1

**Range:** AnsibleSpecs `2981171..638d9cb` (`phase/035-P5`): `reviews/2026-09-jenkinsfile-review/`
`inventory.md`, `report.md`, `plan.md`, and the P5 done-record in the slice's `plan.md`.

**Readiness.** Ready to merge. V15's three asks are met: `inventory.md` types the five apps'
producers as T1 and PipelinesDeploy's as T2 and counts 78 (T1 28, T2 50, 120 typed jobs).
`report.md` has a dated status note under J01, J16, J24 and Q9. `plan.md` records 035 in "where
things stand" and names the second slice as the next cut. I checked the facts behind the records
against the code, not the done-record. All 77 ledger files at their ledger commits, plus Ansible's
`5b4b984`, declare `disableConcurrentBuilds(abortPrevious: true)` and `githubPush()`, use
`checkout scm` with no `git branch:`/`credentialsId:`, and call `architectureProducer.validate` and
`.archive`. All 50 deploy files also call `.generate`, and each repo is one commit ahead of origin.
The new variant descriptions (DHCPApp/ZigbeeControl, ElectronicsInventory, FieldnotesApp,
IoTSupport `:13`/`:37`, PipelinesDeploy) match the pre-migration `origin/main` bodies. Appendix A
does hold 77 `AaC/*` producer rows (79 `AaC/*` rows, less Architecture and Home Assistant Fleet).
`vars/architectureProducer.groovy` matches the J16 note's account of the three steps. The members
lists add up to 28 and 50. No test gate is recorded for this commit, and the specs repo has none.
For prose records that has no bearing; the one probe that applies, added lines ≤ 100 columns,
holds except for the two pre-existing type-table rows.

The records write the slice's change as done before the test phase's push. P5's section asks for
exactly that ("These records state what the slice changed", plan.md:467-468), so it is not a
finding.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

`report.md:807-809` (J16's *Delivered* note): "Each producer stays a full declarative file of
about 40 lines: header, library line, and `pipeline {}` … The operator accepted that length."
The files as committed are 47 lines (the 22 single-model app files and Ansible's), 59
(DHCPApp, ZigbeeControl, ElectronicsInventory, DockerImages), 62 (48 deploy files, e.g.
`ChartsDeploy` `bff8260`), 69 and 70 (ArgoCDDeploy, KubeCoderDeploy) and 93 (IoTSupport
`07401c8`). 51 of the 78 run 62 lines or more. "~40" is Ruling D2's estimate
(`slices/035…/plan.md:91`), and the record restates it as the files' measured length. No
product consequence: it misstates how long the files are in the review's record.

Entered in the close-out as P5 (P4 was a miscounted first entry, struck).
