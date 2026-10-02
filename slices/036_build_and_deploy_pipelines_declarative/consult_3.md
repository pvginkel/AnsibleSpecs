# Consult 3 — slice 036, after P13 and P14

**Outcome: bail.** One acceptance criterion, V11, cannot be met inside the plan's rulings, and
leaving it as it is harms the product. It needs an operator ruling, not a phase.

## What blocks: close-out B3, V11

Test round 1 found that none of the eight jobs on the renamed repos built after the push:
`MyDownloads/MyDownloadsClient`, `MyDownloads/MyDownloadsServer`, `ScanToPdf/ScanToPdfClient`,
`ScanToPdf/ScanToPdfServer` and their four `AaC/*` twins. It recorded this as B3 and did not start
them by hand.

I read the cause from each job's GitHub Hook Log (`<job>/GitHubPollLog/`, read-only). I read five
of the eight logs, and all five show the same thing. For the 10:57 redelivery:

```
[poll] Last Built Revision: Revision e5238675… (refs/remotes/origin/master)
 > git ls-remote -h -- https://github.com/pvginkel/MyDownloadsClient.git
Found 1 remote heads …
No changes
```

- A Pipeline job polls with the SCMs its **last successful build** recorded. Here that is the old
  file's `*/master` checkout, not the job's new `*/main` definition.
- `master` no longer exists on GitHub, so every hook poll finds no matching head and starts
  nothing. This holds for any push.
- Each job's `lastBuild` is still the pre-rename build from 2026-10-01 ~13:17.

So B3's Consequence ("the next push … may be the first") understates the problem. No push will
ever start these eight jobs again. CI for MyDownloadsClient, MyDownloadsServer, ScanToPdfClient
and ScanToPdfServer, and their architecture producers, is dead, and nothing reports it. The slice
caused this with R11's rename. I added this to B3 as a note.

The fix is one build of each job on `main`, which records the new checkout. Only a hand start can
give that build: Build Now, or `/git/notifyCommit` with `sha1=`. The plan forbids it:

- Ordering constraints: "AaC/Architecture's build is the only one started by hand".
- V18: "No other build was started by hand".
- Not in scope: "Starting a job by hand to prove its file".

A phase cannot do it without the operator, so this consult bails rather than appends.

## Ruling asked for

May the run start each of the eight jobs once by hand, to re-baseline its polling on `main`, and
read V11 from those builds?

- Recommended: yes.
- When: in the test phase's next round, after the P13/P14 push is quiet.
- V18 would gain a second named hand-start exception, beside AaC/Architecture.
- The four `AaC/*` twins' builds start AaC/Architecture downstream, as any producer build does.

## The rest is covered

- **V02, V18 and V21's other failures.** P13 (YouTrackConfiguration `23cb808`) and P14
  (ElectronicsInventory `0eb150ab`) fix the two red builds. Their push and builds are the test
  phase's next round. The gate sweep is green, and EI's tests are waived to its Jenkins build by
  Ruling R1.
- **Acceptance criteria.** Consults 1 and 2 mapped every criterion to a phase, and that mapping
  still holds. V23–V25 are `owed_after`, with close-out actions A2–A4.
- **Close-out.** B3 has the witnessed cause as a note. No other entry changed, and there was no
  mechanical residue to fix.
