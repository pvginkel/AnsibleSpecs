# P1 code review — round 2

Range: DockerImages `8ea9e12..df8448d` on `phase/023-P1` (one commit, `backup-server/src/internal/handler/handler_test.go` only).

**Readiness.** Ready to merge. The only blocking finding from round 1 was F1: no test held V06's clause "metadata written only after the backup has landed". It is resolved. The in-memory backend now logs every `Upload` target in call order, failed calls included (`handler_test.go:31-32`, `:40-42`, `:80-84`). `TestUpload_ValidForWritesMetadata` now asserts the backup is uploaded first and its metadata second (`:431-433`). The new `TestUpload_BackendFailureWritesNoMetadata` (`:479-496`) declares `valid_for=52h`, makes the backup upload fail, and asserts three things: a 500, an empty backend, and no metadata write attempted. The handler code is unchanged, so the ordering at `handler.go:112-136` is what these tests now pin.

No gate is recorded green for `df8448d`. I ran targeted checks in a scratch copy (`go` container, go1.26.5). `go vet ./...` and `gofmt -l .` were clean, and `go test -race -count=1 ./internal/handler/ ./internal/pipeline/` passed. I ran two mutations:

- Round 1's mutation: the `if declared { … WriteMetadata … }` block moved ahead of `pipeline.Upload`. It now fails both `TestUpload_ValidForWritesMetadata` (`uploads = [….metadata.json …age]`) and `TestUpload_BackendFailureWritesNoMetadata`.
- Metadata written before the upload error is checked, with the failure path cleaning both objects so the backend ends up empty. It fails `TestUpload_BackendFailureWritesNoMetadata` at `:493`. The call-order log catches this case even though the snapshot check alone would not.

The fix commit introduces nothing new. The log is appended under the backend mutex, and `-race` is clean. The prune goroutine only lists and deletes, so the exact two-entry assertion at `:431` is deterministic. No existing test was changed except for that added assertion.

Round 1's advisory F2 (a malformed `valid_for` escape is silently dropped) was left unfixed, as the protocol allows. It is already in the close-out report as B3.

No new findings.
