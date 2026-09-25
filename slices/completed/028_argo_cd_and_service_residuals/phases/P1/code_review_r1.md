# Code review — slice 028, P1, round 1

Range: `c74bd01..3f9a158` on `phase/028-P1` (AnsibleSpecs): `e03a4d8` amends argo-cd D7, and
`3f9a158` appends the done-record.

**Readiness: ready to merge. No findings.** The amendment (`argo-cd/decisions.md:65-76`) sits
directly under D7's body. It uses the file's amendment form, a dated and attributed blockquote
with a bold headline, matching D47's at `:560` and D41's at `:376`. It records each point of the
P1 list in Ruling D1's terms:

- D7 stands (`:66`).
- The notification is the event, and its expiry sends no "resolved" (`:66-69`).
- The standing state comes from Prometheus rules over Argo CD's application metrics, and those
  alerts resolve when the app recovers (`:69-71`).
- The limit: the standing failed-sync alert covers auto-synced apps only. The hand-synced app keeps
  the immediate event, for the stated reason (`:71-74`). Its D3 citation holds: `design.md:98-100`
  ties Argo CD's permanent manual sync to D3.
- The standing degraded alert covers every app (`:74`).
- The two-message trade-off (`:74-76`).

The amendment adds no new decision id and changes no other decision, so V07 is met. The
done-record (`plan.md:182-195`) is accurate. It names the right commit, and its `Later phases:`
note tells P3 that the amendment leaves the no-resolve mechanism to P3. That matches P3's section,
which requires the routing explicitly.

No test gate is recorded for this commit. AnsibleSpecs has no test verb (no `.kubecoder/`), and
the change is prose only, so the unverified gate state has no bearing on this review.
