# P3 code review — round 1

**Range:** HomelabTerraformProvider `c1badcb..ce5b2bf` (`phase/020-P3`)

**Readiness: ready to merge.** The new `Vet and unit tests` stage (`Jenkinsfile:56-68`) sits between
`Build terraform-provider-homelab` and `Publish to provider registry`. It runs `go vet ./...` and
then `go test ./...` as plain `sh` steps in the `go` container. In a scripted pipeline, a non-zero
exit throws out of the `node` block before the publish stage runs, so V05 holds: a red vet or test
build appends nothing to the registry. It runs after the stage that apt-installs the
librados/librbd headers into the same container (`Jenkinsfile:35`), which cgo needs. Nothing in the
diff, the pod template or the repo sets `TF_ACC`. All nine acceptance tests go through
`resource.Test` (the `internal/*/resource_acc_test.go` files), and it skips them before their
`PreCheck` reads any env var, so V06 holds. The only consumer of Jenkins artifacts is
`scripts/fetch-install.sh`, and it defaults to `lastSuccessfulBuild` (`:24`). That means the
untested binary a red gate leaves archived is never picked up; the done-record already notes this.
No unit test depends on uid, `$HOME` or a local tool, so running as root in CI changes nothing. The
`project.yaml` comment change is accurate. I found one advisory issue and nothing that blocks.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

The done-record's handover to later phases describes a log that does not exist. The P3 "Later
phases" note in `plan.md` says a green provider build's "log shows the unit tests passing and the
`TestAcc*` tests skipping". But the stage runs `go test ./...` without `-v` (`Jenkinsfile:65`), and
that prints one `ok <package> <time>` line per package: no per-test PASS lines and no SKIP lines. I
witnessed this with a targeted run: `go test -count=1 ./internal/s3reader/ ./internal/s3storage/`
printed only two `ok` lines, even though those packages hold `TestAccS3Reader_basic`,
`TestAccS3Storage_basic` and `TestAccS3Storage_readerGrant`. A test phase that uses this note to
prove V06/V18 from the build log would look for skip lines that are never printed. The code itself
is correct. I appended a review note with the actual log shape to P3's "Later phases" in
`plan.md`.
