# P1 code review — round 1

Range `74acb1c..326c995` (AnsibleSpecs, `phase/038-P1`): one commit adding **D67** to
`argo-cd/decisions.md` and the P1 done-record to the plan.

**Readiness: ready to merge.** D67 sits where the phase asks: it is the last entry of
"Terraform and the PreSync hook", `argo-cd/decisions.md:574-595`, just before "Promotion and CI"
at `:597`. Its id is the next free one: D66 was the highest, and D67 appears once. It covers
everything the phase outcome lists:

- **The mechanism** (`:576-582`): a non-hook ConfigMap carrying `hook.revision` from
  `$ARGOCD_APP_REVISION`, set per source in a multi-source app (D56).
- **The why** (`:584-589`): hooks are outside the diff, `terraform/` and the tfvars sit outside
  `chart/` (D12/D14), auto-sync fires only on OutOfSync, and no pipeline or credential can start
  a sync (D1).
- **What was turned down** (`:591-594`): the `terraform/` hash in per-stage values (D12) and the
  registry-owned hook (ANS-199).
- **The cost taken**: a sync and an apply on every push, mostly no-op.

I checked each cross-referenced entry against D67: D1 `:26`, D5 `:50`, D12 `:152`, D14 `:163`,
D17 `:180`, D30 `:479`, D33 `:531`, D46 `:365`, D56 `:1027`. Each says what D67 attributes to
it. None states anything D67 makes untrue, so leaving every entry unamended is correct, as the
done-record records. That includes D6's push-only and webhook-first triggering, which D67
assumes rather than contradicts. The plan edits are within bounds: they add the done-record and
D67's id to P3's comment bullet, and change no `###` heading.

The branch's test state is unverified, but nothing here depends on it. AnsibleSpecs is plain
Markdown and has no gate, so I ran no targeted tests.

## Findings

None.
