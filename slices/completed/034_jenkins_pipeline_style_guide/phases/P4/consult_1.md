# Consult 1 — slice 034, P4, after review round 2

**Outcome: fix_round** (F7 only).

## Why F7 clears the bar

The bar at round 2 funds only findings whose merge would harm the product. P4's product is
`rulings.md`, the page the operator rules from cold at P5's start, the run's one planned pause.
The pause comes right after this merge. What the page says there is what P5, P6 and P8 get
built from. It acts as a contract that the rest of the slice builds against, so it is more than
prose that someone reads once.

I checked the review's evidence:

- `podYaml.sidecars()` holds only `k8s` and `modern-app-toolchain`. Any other template name
  throws `IllegalArgumentException` (`JenkinsPipelineUtils/vars/podYaml.groovy:37-39`, `:69-73`).
- P8's precedent, `ChartsDeploy/Jenkinsfile.architecture`, runs the whole producer in
  `containerTemplates.aac_tools`.
- P8 writes PipelinesDeploy's `Jenkinsfile.architecture` "to the guide" (plan.md P8).
- V14 requires `AaC/PipelinesDeploy`'s first build to be green, and the test-phase ordering
  holds the Architecture and ArgoCDDeploy pushes behind it.
- V19 forbids any library var from changing what it does.

Say the operator follows the lean, (a), with the page as written. The first build of the slice's
own live deliverable then throws in `podYaml`, and the slice has to come back to the operator in
the middle of the run. Its choices then are two exits the page never showed: add the template in
this slice, which runs into V19, or let the first guide-conformant file depart from the guide.
That is a broken flow. It is also the unasked mid-run decision that the rulings page and the
planned pause exist to prevent.

Recording F7 in the close-out report at merge would not help. The operator reads that report at
the end of the slice, after they have already ruled on §5. The fix is one correction to the
text of option (a): say that the gap also reaches this slice's own P8 producer and V14. The
same correction resolves the conflict with §12's "names only calls that exist" argument. That
correction is cheap for round 2 of 5.

## F8

F8 is Minor and advisory. The review already entered it as close-out P9, so this round does not
fund it. The executor may fix it along the way, since it is a one-line path form in §14 step 4.
