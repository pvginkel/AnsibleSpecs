# P2 code review — round 1

HelmCharts `cd51a9c..e9820f9` on `phase/018-P2`.

**Readiness: sign off.** The phase meets its outcome. The rendered Alertmanager config (chart
alertmanager-1.43.3, v0.34.1) passes `amtool check-config`, and the same check rejects a misspelled
`chat_id_file` key, so 0.34.1 parses the file-based chat id strictly. Routing is correct: critical
alerts go to the loud receiver, everything else goes to the silent one. The inhibit rule matches only
`NodeMemoryStallCounterWedged` as the source and only the two stall alerts as targets, on `equal: [node]`.
The bot token and chat id exist only as files from the ESO Secret, so the rendered config holds paths, not
values. The dev release, ingress and SMTP are untouched.

Deploy wiring checks out:
- `helmops.install` applies `manifests.yaml` after `helm upgrade` (`tools/deploy/deploy_cli/helmops.py:198-203`).
- Neither the CLI nor the `Jenkinsfile:81` invocation passes `--wait`, and Helm 4.3 defaults to `hookOnly`. So the pod waiting on the Secret cannot deadlock the upgrade.
- The chart renders `subPath:` as null in the new volumeMount. A server-side-apply dry run of that shape in `development` was accepted.
- The `eso/prd/*` ESO policy (Ansible `inventories/prd/group_vars/openbao.yml:106`) covers the new leaf.

The template renders cleanly for node-keyed, instance-keyed and resolved alerts. The tests are not
vacuous: route selection, receiver flags, secret-file wiring and inhibition scope are all asserted
against the real rules. The one finding is an advisory edge in how the D2 inhibition and V07's
resolved notices interact.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**A stall alert delivered before its node's wedge warning fires never gets a `[RESOLVED]` notice.**

The inhibit rule (`configs/prd/prometheus/prd/values.yaml:278-281`) mutes a target alert's resolve
as well as its firing. The plan accepts that a wedged node's stall alerts are not inhibited until the
wedge first qualifies: up to ~44 h on average on srvk8s1 (plan P1, "First detection is slow").

So a corroborated `NodeMemoryStalled` in that window goes out loud as `[FIRING]`. Then the wedge
warning fires, and the stall alert's later resolve is filtered out. Alertmanager drops the resolved
alert after that muted flush, so nothing is sent even after the wedge warning resolves. The chat is
left with a loud critical that never closes.

I witnessed this on a local Alertmanager 0.34.1 running this config, with the executor's fake
Telegram and shortened group timers. The sequence was: stall firing, then wedge firing, then stall
resolved, then wedge resolved. It produced `[FIRING] NodeMemoryStalled` (no `disable_notification`),
`[FIRING] NodeMemoryStallCounterWedged` and `[RESOLVED] NodeMemoryStallCounterWedged`, and no resolve
for the stall alert.

This matters now because srvk8s1 is wedged (close-out A1) and has not yet qualified after deploy.
It is still unlikely: P1's replay found the corroborated stall alerts matching no minute on any node
over the retained week. The consequence is a misleading chat history, not a missed alert.
