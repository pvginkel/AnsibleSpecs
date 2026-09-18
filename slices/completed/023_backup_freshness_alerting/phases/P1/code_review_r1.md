# P1 code review — round 1

Range: DockerImages `beac1e2..8ea9e12` on `phase/023-P1` (one commit, `backup-server/src/internal/`).

**Readiness.** The code does what the phase asks. `POST /upload` accepts an optional `valid_for`, rejects
anything but a positive Go duration with 400 before it reads the body (`handler.go:91-98`), and writes
`<object>.metadata.json` as compact plain JSON only after `pipeline.Upload` returns success
(`handler.go:127-136`). A failed metadata write removes both objects and returns 500. Prune now
partitions names into backups and metadata, counts only backups, and deletes the metadata of every
backup it does not keep, orphans included (`prune.go:25-45`). No gate was recorded green for this
commit, so I probed it directly in a scratch copy (`go` container, go1.26.5). `go vet ./...` and
`gofmt -l .` came back clean. `go test -race -count=1 ./internal/pipeline/ ./internal/handler/` passed.
Mutations against the new prune and validation logic (metadata counted again, orphans not cleared,
empty `valid_for=` treated as undeclared) are each caught by a new test. One clause of V06 has no
test: "written only after the backup has landed". A mutation that breaks it passes the suite (F1).
`api.md` and `README.md` do not describe `valid_for` or the new prune rule yet. They are prose, so the
doc phase handles them, and they are not a finding here.

## F1 — Major · blocking · anchor: coverage-gap · confidence: high

**No test checks that the metadata file is written only after the backup has landed.**

V06 (`verification.json`) and the phase outcome (`plan.md:196`, "only once the backup has landed")
require the metadata write to come after a successful backup upload. The code gets this right:
`handler.go:112-125` returns on any upload error before the `if declared` block at `:127`. No test
holds it, though. `TestUpload_BackendFailureCleans` (`handler_test.go:342-354`) makes the backup fail
without declaring `valid_for`. `TestUpload_MetadataFailureCleans` (`handler_test.go:465-477`) makes
only the metadata write fail. No test makes the backup upload fail while `valid_for` is declared.

Mutation run: I moved the `if declared { … WriteMetadata … }` block ahead of `pipeline.Upload` and left
the backup-failure path cleaning only `target`. In that version the metadata is written first and
survives a failed backup. `go test -count=1 ./internal/handler/` still passes (`ok
backup-server/internal/handler`). A regression to a metadata-first order would leave a stray
`.metadata.json` after every failed upload, and nothing in the suite would notice.

## F2 — Minor · advisory · anchor: none · confidence: high

**A malformed `valid_for` value is dropped silently, and the upload is stored as undeclared with 201.**

`handler.go:76` parses with `r.URL.Query()`, which throws away any key/value pair whose percent-escape is
malformed. The value never reaches `query.Has("valid_for")` at `:91`. I probed this with a scratch test:
`valid_for=52h%zz` and `valid_for=%3` each returned 201 and stored the backup with no metadata file. The
log line reads `valid_for=` (empty). An uploader whose URL-building bug leaves a stray `%` believes it
declared a validity, but its stream is never watched. That is the silent failure mode R1 is about. It is
advisory: the uploaders P4 and P6 will send a literal `52h`, and the same parse already drops a
malformed `filename` pair (that path answers 400 "missing filename").
