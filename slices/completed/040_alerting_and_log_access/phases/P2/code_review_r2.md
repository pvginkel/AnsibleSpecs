# P2 code review — round 2

PrometheusDeploy `017c71f..6199854` (`phase/040-P2`), the fix for r1 F1. The gate is green on
`6199854`, taken as given.

**Readiness: signoff.** F1 is resolved. `LoadBalancerNotAnnounced` used to be silenced by "any
`metallb_speaker_announced` series exists". Its guard is now "some speaker `up` is 1"
(`config/prd/values.yaml:463`), and `MetalLBAnnouncementsBlind` now fires when no speaker
`up` is 1 (`:480`). MetalLB withdrawing every Service while its speakers are scraped and up
now fires critical on every Service except KubeCoder environments'. A speaker whose scrape
fails still reads as announcing nothing, and the rule stays silent only when no speaker is
scraped up. I re-checked this against the code and live state, not the done-record:

- **Live labels match the selector.** On prd, `up{job="kubernetes-pods",
  namespace="metallb-system"}` has four series with `component="speaker"` (srvk8s1–4) and
  one with `component="controller"`. The controller is excluded, which matters because it is
  up independently. Live, `absent(up{…component="speaker"} == 1)` returns empty.
- **The new test witnesses r1's repro.** `tests/alert-rules/loadbalancers.yml:115-140` has a
  speaker that is up, has withdrawn dhcp and announces nothing. dhcp fires at 15 m and 60 m,
  the KubeCoder environment stays quiet, and the blind warning stays quiet.
- **Mutations of the new guard each fail a test** (targeted `tests/alert-rules.sh` runs in a
  scratch copy):
  - Restoring the old `and on () metallb_speaker_announced` guard: `got:[]` for dhcp at 15 m.
  - Dropping `== 1` from the rule's guard: the rule fires at 40 m while every speaker is down or
    gone.
  - Dropping `== 1` from `absent`: no blind warning at 50 m.
  - Dropping `component="speaker"`, so the controller's `up` satisfies both: the rule fires at 40 m.

The first test now mixes the three ways a speaker can go dark: srvk8s4's scrape fails from
5 m, srvk8s2's target is gone at 40 m, and srvk8s3's scrape fails at 40 m. The rule stays
firing while any speaker is up, and it goes silent with the blind warning following 10 m
later. The revised comments (`values.yaml:440-446`, the test header) match the expressions.

One trade-off is inherent and not a finding. The guard can no longer tell "the speakers
announce nothing" from "the speakers stopped exporting `metallb_speaker_announced` while
staying up", as a metric rename in a MetalLB upgrade would. The rule then fires critical on
every non-environment Service. That failure is loud, not silent. r1 F1 showed the series
alone cannot separate these cases, and a scrape gap, which is the case the plan's constraint
(`plan.md:265-266`) guards, still reads as a gap.

Live, the 42 KubeCoder-environment Services still match, because the KSM allow-list this
phase adds is not yet synced. That is expected, and the plan's post-sync check (`plan.md:293-294`) covers it.

## Findings

None. r1's advisory F2 and F3 are unchanged and stay where r1 recorded them.
