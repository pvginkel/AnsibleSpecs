# P4 code review — round 1

Range: HelmCharts `341969509e5e..2ada3db` on `phase/023-P4` (one commit).

**Readiness: ready to merge, no findings.** Each database's upload from the `postgres-backup` script now
carries `valid_for=52h` beside `filename=<db>.dump`
(`charts/postgres-pas/templates/backup-configmap.yaml:30,48-49`). That is the parameter P1's server reads
(DockerImages `backup-server/src/internal/handler/handler.go:94-95`) in the Go-duration form the plan
requires, so the phase outcome, V04 and the Postgres half of V05 are met. The stream key is unchanged
(`<db>.dump`, `:69`). Excluded databases still never upload (`values.yaml` `excludeDatabases`: `postgres`,
`app`), so the done-record's hand-off to P5/V19 is accurate. Switching from `quote` to `urlencode`
(`quote_plus`) changes nothing for any file name backup-server accepts, and Go's query parser decodes `+`
and `%20` the same way. The new comment gives the 52 h rationale, which matches the ruling (48 h per
missed night, so one miss stays quiet and two alert). The docstring's "one stream per database" matches
the ruling that a stream is scope + file name.

The new test is not vacuous. I ran `tests/test_postgres_pas_backup.py` in the `iac` container against
scratch copies of the ConfigMap. It passes on the phase's script and fails on each of four mutations:
`valid_for` dropped from the query, `VALID_FOR = "2d"`, the pre-phase upload line restored, and a second
`&valid_for=48h` appended. It loads the real script from the chart template. It stubs `subprocess.run`
and `urlopen`, so it stays hermetic, as HelmCharts CLAUDE.md requires. It also checks the path, host,
bearer header and exclusion list along with the query. The gate log records only the suite's OK line,
so I made the targeted run above to confirm this test actually executes and discriminates.

I checked two more things and found no issue. First, no generated artifact describes the upload's
query: `charts/postgres-pas/architecture.yaml:22-27` records only `served_by svc:backup-server`. Second,
the YouTrack uploader the done-record flags (`charts/youtrack/files/backup/backup.py:105`, no
`valid_for`) is outside P4's outcome and is already close-out Q1.

## Findings

None.
