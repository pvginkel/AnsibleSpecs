# P2 code review — round 1

Range: DockerImages `df8448d..88e329f` on `phase/023-P2` (one commit, `backup-server/`).

**Readiness.** Not ready. The watcher is otherwise sound. The stream model matches the rulings: a stream is scope + file name, it is watched while any kept backup declares, and its valid-until is the newest landing plus the newest declared validity. Orphans are never read, and each stream reads only its newest declaring metadata file, once. Refreshes are serialized, and the post-upload refresh runs after the prune. Metrics sit on their own `:8081` mux, and a scrape reads no storage. Tests pin most of these edges. One defect breaks the phase's stated guarantee. When a refresh's `rclone lsjson` call fails with an error from a common class (a DNS "no such host", a missing rclone config, a Drive 404), the watcher treats it as an empty listing. It then drops every stream and records a successful refresh. The overdue series vanish, and the reads-working signal says healthy while nothing is being read. No gate is recorded green for `88e329f`. I ran targeted checks in the `go` container (go1.26.5). `go build ./...`, `go vet ./...`, `gofmt -l .` and `go mod tidy -diff` were clean. `go test -race -count=3` over `internal/freshness`, `internal/handler` and `internal/pipeline` passed. I did not run the rest of the suite.

## F1 — Major · blocking · anchor: failing-test · confidence: high

**A failed cloud-storage read counts as an empty remote: every stream is dropped and the refresh counts as a success.**

`RcloneBackend.lsjson` (`backup-server/src/internal/pipeline/backend.go:94-98`) returns `nil, nil` whenever rclone fails and its stderr contains `not found` or `no such`. That mapping predates this phase and is harmless for prune, where empty means nothing to prune. P2 routes the watcher's reads through it: the root listing (`ListDirs`, `:85-87`, called at `internal/freshness/watcher.go:97`) and each scope listing (`watcher.go:162`). In `Refresh`, an empty root listing means no scopes and no errors. So `w.streams` is replaced with an empty map (`watcher.go:122`) and `w.lastSuccess` advances (`watcher.go:123-125`). In `RefreshScope`, an empty scope listing deletes that scope's streams (`watcher.go:150-153`).

Failures whose stderr matches those substrings:
- Go's DNS error `lookup www.googleapis.com …: no such host`.
- rclone's `NOTICE: Config file "/data/rclone.conf" not found - using defaults`, printed ahead of the real failure when the config file is missing.
- A Drive `Error 404: File not found`.

Repro, run in a scratch copy with a stub `rclone` on `PATH` that prints each of the first two stderr texts and exits 1. `freshness.New(pipeline.NewRcloneBackend(""), "gdrive-pieter:Homelab Backups")` first refreshes against a healthy listing and publishes 1 stream. The failing refresh then returns `err=<nil>`, publishes 0 streams, and advances last success, in both cases:
```
dns: err=<nil>, 0 streams, last success advanced=true
noconf: err=<nil>, 0 streams, last success advanced=true
--- FAIL: TestProbe_FailedRootListingIsNotSuccess/dns
--- FAIL: TestProbe_FailedRootListingIsNotSuccess/noconf
```

Why it matters. The ruling says backup-server "keeps the last values it read, so a stalled refresh cannot hide an overdue backup while scraping works" (plan.md:64-68, restated for P2 at :283-286; V09). The dead-watcher alert must fire when "backup-server cannot read cloud storage" (plan.md:77-82; V13). The done-record also claims "a failed root listing keeps everything" (plan.md:325). Under this failure class all three are false:
- `backup_server_stream_valid_until_timestamp_seconds` loses every series, so an overdue alert that is firing resolves.
- `backup_server_refresh_last_success_timestamp_seconds` keeps advancing hourly, so P5's dead-watcher expression never fires.

The effect lasts as long as the failure does. That is R1's silent dead backup, reintroduced by the watcher meant to catch it. The existing failure tests use an in-memory fake that returns an error value (`watcher_test.go` `failDirs`/`failList`), so the real backend's error classification is untested.

## F2 — Minor · advisory · anchor: coverage-gap · confidence: high

**Two behaviours in the phase outcome have no test that pins them.** Both survived a mutation run over `internal/handler` and `internal/freshness`.
- The post-upload refresh runs "once that upload's prune has run" (plan.md:250). Swapping the order in `Handler.afterUpload` (`internal/handler/handler.go:163-168`) to refresh first and prune second leaves every test green.
- The metrics are not answered on the port nginx proxies (plan.md:287-290; V10). Registering `GET /metrics` on the `:8080` mux in `Handler.Routes` (`handler.go:47-58`) leaves every test green. `TestMetrics` checks only the other direction, that the metrics handler serves nothing else.

The current code is correct on both points, so nothing breaks today. A regression would go unnoticed. For the ordering, the cost is small: a stream pruned away by an upload keeps publishing until the next hourly refresh.
