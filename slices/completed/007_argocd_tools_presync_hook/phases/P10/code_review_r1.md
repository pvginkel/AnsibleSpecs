# P10 code review — round 1

**Scope reviewed:** `git diff 9c240e478..3600c2f33` on `phase/007-P10` in `/work/Charts` —
one commit, one file, `tests/render-consumer.sh` (+24/-4).

## Readiness

The phase's outcome is met and I re-proved it rather than taking the done-record's word: with the
chart's own gate run against a scratch copy of the tree, swapping the template's `hook.stage` and
`hook.namespace` lines (`charts/homelab-shared/templates/_tf-presync-hook.tpl:47-48`) fails
`tests/render-consumer.sh` with the expected and rendered blocks printed side by side, and deleting
the `hook.namespace` line fails it too — neither would have failed the four per-line `expect`s this
phase removed. The order the gate now pins (`repo, revision, stage, namespace`,
`tests/render-consumer.sh:79-82`) is the order the entrypoint actually takes positionally
(`/work/ArgoCDTools/presync/cli.py:22-25`), and the comment's `python3 -m presync …` shape matches
the shipped image's `ENTRYPOINT ["python3", "-m", "presync"]` (`/work/ArgoCDTools/Dockerfile:91`) —
no contract drift. Dropping the four `expect`s in favour of the block comparison is a sound
subsumption, not a coverage loss: a changed value fails the new check (it compares the block whole),
a missing value fails it as a length mismatch, and a removed hook template yields an empty block that
also mismatches. The phase's constraint holds — no chart file is touched, so
`dist/homelab-shared-0.2.0.tgz` is byte-identical and `tests/publish.sh`'s immutability check is
untouched — and V12's evidence pointer (`verification.json`) now names
`tests/render-consumer.sh:67-89`, which is where the check actually sits. One advisory observation
below; nothing blocking. **Verdict: signoff.**

## Findings

### F1 — The block reader binds to the render's *first* `args:`, not the hook Job's

- **Severity:** Minor · **Impact:** advisory · **Anchor:** none · **Confidence:** high
- **Evidence:** `tests/render-consumer.sh:73-77`. The awk latch (`!inblock && /args:/ { inblock = 1 }`)
  never resets and `exit`s at the first line that is not a `- ` item, so it reads whichever `args:`
  block appears earliest in `$RENDER` — nothing ties it to `kind: Job` or to the `terraform`
  container. Today that is safe by accident: `charts/homelab-shared/templates/_tf-presync-hook.tpl:44`
  is the only `args:` in the repo.
- **What I ran:** appending a two-item `args:` block to the fixture's Deployment
  (`tests/consumer/templates/consumer-deployment.yaml`) — a manifest helm sorts *ahead* of the Job in
  its output — makes the gate report `FAIL: the hook Job renders the wrong arguments, or renders them
  out of order` and print `"serve" / "--port=8080"` as what the hook Job rendered, while the hook Job
  in fact rendered its four arguments correctly.
- **Why it is advisory, not blocking:** the failure direction is a false *red* with a misleading
  message, never a false green — the assertion cannot be satisfied by a wrong hook Job. It costs a
  future fixture author one confusing debugging session, and only if the fixture grows a second
  workload carrying `args:`. That is an unspecified future edge case, so it funds a card, not a fix
  round.

## Checks that found nothing

- **Mutation bite (the phase's whole premise):** re-run, not reasoned about — swap and delete both
  fail (see above). The gate is green on an unmutated tree in the same scratch copy, so the failures
  are the assertion's, not the harness's.
- **Contract agreement:** the four expected values, in order, against `presync/cli.py`'s positional
  `repo/revision/stage/namespace` — agree.
- **Coverage regression from deleting the four `expect`s:** none. Each old assertion's failure mode is
  a strict subset of the new check's.
- **The `required`-guard half of V12** is P5's, proven there by mutation
  (`plan.md:624-627`); its absence from this diff is not a P10 gap.
- **No chart file in the diff**, so the 0.2.0 tarball immutability constraint
  (`plan.md:897-900`) holds by construction; no 0.3.0 was published for a test.
- **Working tree left clean** after my scratch runs (`git status --porcelain` empty).
