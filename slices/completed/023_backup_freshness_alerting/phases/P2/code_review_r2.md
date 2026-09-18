# P2 code review — round 2

Range: DockerImages `88e329f..0af47c9` on `phase/023-P2`: one fix commit, touching `backup-server/src/internal/pipeline/backend.go` and a new `backend_test.go`. The rest of the branch was reviewed in round 1 and is context here.

**Readiness.** Ready to merge. Round 1's blocking finding, F1, is resolved. `lsjson` no longer decides from stderr text. Only rclone's directory-not-found exit code 3 counts as "missing", and only `List` turns that into an empty listing (`backend.go:80-99`, `:108-111`). `ListDirs`, the watcher's remote-root read, returns it as an error. Every other rclone failure is an error.

**How F1 was checked.**
- **Real rclone v1.75.1.** A missing directory exits 3, on both the local backend and an HTTP 404. A DNS "no such host" exits 1, and so does a missing config section, whose output includes the "Config file … not found" notice. So the exit code separates the two classes that the stderr text mixed up.
- **Round 1's repro, replayed.** I ran it in a scratch copy: the real `RcloneBackend` driven by a stub `rclone` on `PATH`. The watcher published 1 stream. Then I made each read fail: a DNS failure on the root, a missing config on the root, and a DNS failure on only the scope. In every case `Refresh` returns an error, keeps the stream, and leaves last-success where it was. `RefreshScope` also returns an error and keeps the stream. The one change is a scope folder that rclone reports missing (exit 3): `RefreshScope` drops it. That matches the ruling that a stream whose backups are all gone drops out.
- **Mutations.** I put back round 1's substring matching in `lsjson`, and `TestRcloneListingFailures` fails on its dns, no-config and drive-404 cases. I then let `ListDirs` also map exit 3 to empty, and the directory-not-found case fails. The new test pins both halves of the fix.

**Interaction with the rest of the branch.**
- Prune also calls `List` (`prune.go:21`). A network or config failure now fails the prune instead of silently pruning nothing. A missing scope folder is still a no-op.
- A missing remote root now fails every full refresh, so the dead-watcher signal would fire. That is the conservative reading of "cannot read cloud storage", and production's root already exists.
- The done-record addition (plan.md:326-328) states the fix's behaviour accurately.

**Gate state.** No gate is recorded green for `0af47c9`. I ran targeted checks in the `go` container (go1.26.5):
- `gofmt -l .` is clean.
- `go vet` is clean over `internal/pipeline`, `internal/freshness` and `internal/handler`.
- `go build ./...` succeeds.
- `go test -race -count=2` passes over the same three packages.

I did not run the rest of the suite. The fix does not touch it.

Round 1's F2, the advisory coverage gap, is unchanged and already in the close-out report as S3. The executor logged `Delete`'s matching problem, the same substring issue outside this fix, as B4.

## Findings

None.
