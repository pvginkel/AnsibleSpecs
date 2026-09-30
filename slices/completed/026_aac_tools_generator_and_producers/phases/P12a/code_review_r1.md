# P12a code review — round 1

**Readiness: sign off, no findings.** The Ansible range `b92d01a..HEAD` is empty, as the plan's
done-record says it is. P12a's work is ten single-commit pushes: the eight planned carriers and the
ScanToPdf and MyDownloads packagers. Each carrier's `Jenkinsfile.architecture` now runs
`arch-validate` in `containerTemplates.aac_tools('aac-tools')`, and its local `lint` runs
`cexec aac-tools arch-validate docs/architecture/*.yaml` (YouTrackMCPServer had no local gate).
Every file that named the script at `HEAD~1` is migrated, `scripts/arch-validate.py` is gone, and
each environment that hosts a migrated gate declares `aac-tools`, with the restarts in close-out
A5. The pushes kept to D1, F1 and F5. The packager pushes fall under D1's authorisation for repos
the sweep touches, and N6 records them.

## Findings

None.

## What the sign-off rests on

The executor's claims were checked independently, not taken from its record:

- **Diff:** `git show HEAD` in each of the ten clones under `/work/scratch/`. `git grep` at
  `HEAD~1` lists every file that named the script, and each one is in its repo's commit. At `HEAD`,
  no instruction names `scripts/arch-validate.py`. The remaining `scripts` mentions are
  `.dockerignore` entries and SEED-NOTES history.
- **Lint-only drift:** each deleted copy was compared with Architecture's canonical script. Six are
  byte-identical. GitblitMCPServer's copy drops an `open(…, "r")` argument, and NewsFilter's uses
  `max(status, 1)` twice. The sidecar's `/usr/local/bin/arch-validate` is byte-identical to the
  canonical script.
- **Gate shape:** `cexec aac-tools arch-validate docs/architecture/*.yaml` passes from
  `/work/scratch/GitblitMCPSupportPlugin` (`✓`, exit 0). `cexec` propagates exit code 2, so the
  exit-code comment in GitblitMCPSupportPlugin's `project.yaml` still holds.
- **F1:** each commit's parent was already the remote head from an earlier push, according to
  GitHub's push events and the history. Each clone's `HEAD` equals GitHub's branch head, and the
  default branches match: `master` for ScanToPdfServer and MyDownloadsServer.
- **V12 (these repos):** GitHub's recursive trees at all ten pushed heads are complete (not
  truncated) and hold no `arch-validate` path.
- **F5/V13:** the architecture consoles for AaC/Ginbov #12, MyDownloadsServer #3,
  GitblitMCPSupportPlugin #16, ScanToPdfServer #14 and YouTrackMCPServer #16 each check out the
  pushed sha. Each runs `+ arch-validate docs/architecture/architecture.yaml` in the `aac-tools`
  container, and each ends `Finished: SUCCESS`.
- **Batch order:**
  - The canary's log closes at 00:45:10, and batch 2 was pushed at 00:45:31.
  - Batch 2's logs close by 00:55:52, and batch 3 plus the ScanToPdf packager were pushed at
    00:56:14.
  - Batch 3's logs close at 01:07:27, and the MyDownloads packager was pushed alone at 01:07:39.

  No batch pairs two carriers that pin the same deploy repo.
- **Rollouts:** all seven Applications are Synced and Healthy now: git-sync, youtrack-mcp,
  ginbov-nl, newsfilter, scantopdf, webathome-org and media, each `-prd`.
