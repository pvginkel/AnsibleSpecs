# Consult 4 — slice 036, after Ruling R2

**Outcome: complete.** Every phase is done, and every criterion still marked fail traces to work
that already exists. What is left is the test phase's push and its reading of the builds, not a
phase.

## The criteria that still fail, and what delivers them

| Criterion | Why it failed in test r1 | What delivers it |
|---|---|---|
| V02 | ElectronicsInventory #262 failed on the editor-role Playwright case | P14, `0eb150ab` on `/work/scratch/ElectronicsInventory` `main`, one commit ahead of origin. Its tests are waived to the push's Jenkins build by Ruling R1 |
| V11 | The eight renamed-repo jobs never built after the push, because their polling still baselines on `master` | Ruling R2: the test phase starts each of the eight jobs once by hand from `main`, after the P13/P14 push |
| V18 | EI #262 and YouTrackConfiguration #9 were red, and the eight jobs were unbuilt | P13 and P14, plus R2's builds. V18's text already names R2's exception |
| V21 | Same three causes as V18 | Same as V18 |

- **P13** is `23cb808` on `/work/scratch/YouTrackConfiguration` `main`, one commit ahead of
  origin. P13's done-record names one risk that only the live build can show: the
  webhook-triggers app may not be attached to AU, IS or XF.
- **The migration ledger.** The eight jobs' migrated files have been on origin `main` since test
  r1.
- **V23–V25** stay `owed_after`, with close-out actions A2–A4.
- **The gate sweep.** Sweep r4 is green on every row that ran and no ruling covers.

## The edit made

The plan's `## Not in scope` list still said "AaC/Architecture's one build after the pause is the
exception" to starting a job by hand. The R2 commit (`0e28093`) changed the Ordering constraints
and V18 but missed this line. A test agent reading the list alone could refuse R2's hand starts,
so the line now names both exceptions, as the Ordering constraints do. The edit changes no
behaviour and no criterion.

## The close-out report

- **B3:** noted that R2 covers it. It resolves when the test phase reads the eight builds green.
- **Nothing struck.** No phase was appended, and no entry was resolved this round.
- **No residue fixed.** P10 is in Ansible runbooks the slice did not touch, and it is the doc
  phase's. I1, P6, P7 and P9 sit in scratch clones that were already pushed, and P6 and P7's
  files were not touched. Fixing any of them means another push of that repo, which starts a
  build (KubeCoder's rolls dev outside its devlock). That is not worth it for comments that are
  still true or nit-grade label drift. They stay with the wrap-up.
