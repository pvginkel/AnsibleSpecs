# P2 code review, round 1: espFirmware build and upload steps

Range: JenkinsPipelineUtils `15812f9..47cff67` (`phase/036-P2`, one commit).

**Readiness: ready to merge. No findings.** `vars/espFirmware` delivers S1's shape. `build`
(`vars/espFirmware.groovy:27-37`) and `upload` (`:45-60`) are called from the file's own stages
in `script {}`. The IDF version is not an argument: it lives in the image tag of the file's
`idf` entry. The steps do not clone. `upload` puts `withVault` around the upload `sh` alone
(`:50-57`), and no secret goes through the pod. I compared the steps with all eight live
firmware files (`/work/scratch/<Repo>/Jenkinsfile`). Each runs the same commands in the same
order: `safe.directory`, `/opt/esp/entrypoint.sh idf.py [-DHARDWARE_VERSION=n ]build`, `chmod`,
then `scripts/upload.sh https://iot.ginbov.nl`, all in `dir(<Repo>)` and `container('idf')`.
The vault path and the env-var names match too. Intercom's `scripts/upload.sh` takes no
hardware version, so `upload` refusing `hardwareVersion` loses nothing.

Arguments are checked as LIB-3 and the plan ask (`:64-107`). A missing, empty or unknown key is
refused and the error names it. `idfVersion` is refused as unknown. A `hardwareVersion` that is
not a whole number, including `null`, is refused. `EspFirmwareTest` covers each of these. Its
cases are not vacuous: dropping `optional` from the allowed set, loosening the number check, or
the flag's trailing space would each fail a named case.

The test harness runs only the `@NonCPS` helpers. This matches the repo's convention
(`.kubecoder/project.yaml` root `test` comment) and the `ArchitectureProducerTest` precedent. So
nothing tests the literal wiring of the step bodies: the container name, the vault path and the
upload URL. V04's live firmware builds in the test phase are the check on that wiring.

The guide was updated to match. `types/firmware.md` and the library page's J14 row now describe
the steps, with the IDF version in each file's agent. The sentence after the table (`:69`) is
deleted, so nothing stale is left. Both reference files call the steps, and Intercom still
writes out its version stages one by one (GRAN-7). SEC-1's recipe pointed at the firmware
upload, whose `withVault` moved into the library. It now cites `snapshot-producer.groovy:generate`,
which does show `pip install` outside `withVault` (`docs/examples/snapshot-producer.groovy:45-61`).
No page still cites the removed `firmware.groovy:deploy` section. The mkdocs nav has the new
reference page, and the `--strict` build checks anchors (`docs/mkdocs.yml:74-87`), so the
`#upload` link holds.

Gate: green on `47cff67` (input, not re-run). I also ran the docs lint
(`docs/lint_examples.py`): every example and the repo's `Jenkinsfile` validated against the
controller, `firmware.groovy` and `firmware-versions.groovy` included. That is V20's linter
clause.

## Findings

None.
