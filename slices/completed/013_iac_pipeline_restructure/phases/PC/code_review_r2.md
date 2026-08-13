# PC — code review r2

Branch `phase/013-PC` at `60ca07b7`. Re-review scope: `git diff 7461c61..HEAD` — one commit, three
files, comments and one `echo` string. The rest of the branch (`8eba51a..7461c61`) is r1 context.

## Readiness

Ready to merge. All four r1 findings are resolved at the code, checked independently rather than
taken on the executor's word. **F1 (blocking):** no `__pycache__` or `*.pyc` survives anywhere under
`support/iac-agent/` — `find` returns nothing and `git status --porcelain --ignored
support/iac-agent` is empty, so the r6 parity apply no longer ships a build artifact; I re-ran the
phase's own syntax checks (`bash -n bin/iac`, `ast.parse` on `bin/iac-impl`) and confirmed they are
artifact-free, and `plan.md:421-423` now pins that rule for later phases. **F2:**
`etc/cron.d/iac-prune:4-5` now cites `docker run --pull=always`, which is exactly what `bin/iac:40`
builds and `bin/iac:63` executes; the surrounding "`prune -f` is dangling-only" claim still matches
the cron line (`iac-prune:11`, `docker image prune -f`, no `-a`). **F3:** both dead pointers now
resolve — `bin/iac:4` → `phases/completed/iac-agent.md` and `bin/iac-impl:6-7` →
`phases/completed/openbao.md` + `slices/completed/iac-secrets-resolver.md`, all three present on
disk and on `AnsibleSpecs` `origin/main`. **F4:** `bin/iac:27` is location-agnostic again ("run
install.sh from the iac-agent tree"), which is right given `README.md:65`'s `wrkdev` context.

The fix commit's interaction with the branch code it touches is clean. `bin/iac` and `bin/iac-impl`
are both `install_file` targets (`install.sh:47-48`), so a real apply re-copies them, but
`systemd/jenkins-agent.service` is untouched by PC, so `unit_changed` stays `0`, no
`systemctl daemon-reload` fires (`install.sh:67-69`) and the restart guard
`(( unit_changed )) || ! systemctl is-active` (`install.sh:85`) does not trip on a running agent —
the plan's r1-settled claim at `plan.md:434-437` holds as written. The amended parity rule
(`plan.md:428-433`) names exactly the five files `git diff --stat 8eba51a..HEAD` reports, and
correcting PB's "timestamp-only = parity" rule was necessary: PC changed content, so the old rule
would have read a correct apply as a failure. No executable behaviour moved — the sole non-comment
edit in this range is the `echo` message text, and nothing in the repo consumes that string.

The root gate is a no-op here (`gate_r2.log`: "root: no test statements — skipped"), so it certifies
nothing about these files; that is correct for a prose-and-comments phase and not a coverage gap.
Both findings below are advisory.

## Findings

### 1. Minor — the repaired `bin/iac-impl` pointer keeps a section anchor the same move deleted · impact: advisory · confidence: high

`support/iac-agent/bin/iac-impl:6` now reads "Per `/work/AnsibleSpecs/phases/completed/openbao.md`
§Secrets resolver". The directory half of the pointer is fixed; the anchor is not. That file's
headings are `Where the design lives`, `What shipped`, `Operational lessons (carry-forward)`,
`Caveats`, `Followup` — there is no `Secrets resolver` section, and `grep -i 'secrets resolver'`
over it returns nothing.

The anchor died in the very move the fix chases. `AnsibleSpecs` commit `648d922` ("phase 2 (openbao
+ secrets): close to completed/") compressed the 517-line working doc into the as-built
retrospective and relocated it; `git show 648d922^:phases/openbao.md` has `## Secrets resolver —
`!bao` refs (card #40, as-built)` at line 205, and the post-move file has no equivalent. The
surviving `§Secrets resolver`-shaped names now live in `decisions.md` (`decisions.md:112`, "Runtime
secrets — IaC agent resolver"), which is what `phases/completed/openbao.md:18-20` itself points a
reader at.

Failing input: an operator follows the comment to understand the `!bao` resolution order,
opens `phases/completed/openbao.md`, and finds one sentence (line 7) instead of the as-built section
the comment promises. Same class as r1's finding 3 — a pointer to nothing — in the same line the
commit rewrote for pointer accuracy. The second half of the reference
(`slices/completed/iac-secrets-resolver.md`) is correct and does carry the design.

### 2. Minor — the done-record contradicts the shipped error text on the line it describes · impact: advisory · confidence: high

`plan.md:411-413` still states, under "Settled beyond the plan's text": "`bin/iac`'s missing-
`iac-impl` error … Now `/opt/IaCAgent/install.sh`, the path the role syncs it to and the one an
operator on srviac can actually run." The shipped line is `bin/iac:27`, "run install.sh from the
iac-agent tree" — superseded by this round's fix and correctly recorded 30 lines later at
`plan.md:441-443`.

Failing input: the doc phase reads PC's done-record for the tree's prose state, hits the earlier
bullet first, and propagates `/opt/IaCAgent/install.sh` into `docs/runbooks/iac-agent.md` — one of
the files `plan.md:424-425` explicitly hands it. The later "Review-settled (r1)" bullet is the
authority and is unambiguous, so this is a stale sentence in a superseded position rather than a
live wrong instruction; recorded once so the disposition is visible, not as a demand.
