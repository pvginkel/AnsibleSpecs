# P13 code review — round 1

**Range:** YouTrackConfiguration `c878458..23cb808` (`phase/036-P13`), one commit, `youtrack.yaml` +3.

**Readiness.** Ready to merge. The phase's outcome is that `youtrack.yaml`'s `colors:` covers the three projects build #9 named, in the file's own form. The diff does that. It adds AU `#494B57` (palette id 31), IS `#7BCCCF` (id 24) and XF `#893E13` (id 1), each in key order with the file's comment convention. All three backgrounds are in `docs/palette.md`, so `sync.check`'s off-palette test (`src/ytconfig/sync.py:202`) passes. No other entry in `youtrack.yaml:10-32` uses any of them. With the three entries, the uncoloured test (`sync.py:192-197`) has nothing left for the projects #9 reported. The file holds 22 entries, which matches the Done note. The gate is green, and no test reads the repo's `youtrack.yaml` (the tests write their own copy under `tmp_path`), so the offline load the executor did is the only check this commit can get before the build. The rest of the apply can only be proven by the live build. That covers `unknown` (`sync.py:198`), in case one of the three is archived or renamed before the push, and `plan_webhooks`, which needs the webhook-triggers app on AU, IS and XF (`sync.py:258-262`). Neither the executor nor this review could read the instance: the token here returns `Invalid token` from `issues.webathome.org`. The plan's "Later phases" note for P13 already gives that risk to the test phase, so it is not a finding against this diff.

## Findings

None.
