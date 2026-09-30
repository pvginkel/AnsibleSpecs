# P5 code review — round 2

Branch `phase/034-P5` in JenkinsPipelineUtils. This round covers `b37b8ba..d21017c`. Gate: green on `d21017c` (`gate_r2.log`).

**Readiness.** The phase is ready. The only blocking finding from round 1 is resolved, and the fix
adds no new problem. **F1** (Checkout missing from two reference examples) is fixed.
`vars/podYaml.md:15-20` and `vars/cicd.md:54-59` now open their `stages {}` block with
`stage('Checkout') { steps { checkout scm } }`. That is the form CHK-1 requires
(`docs/pages/guide/checkout.md:5-9`), and it is exactly the Checkout stage in
`docs/examples/image-build.groovy:39-43` and `iac-controller.groovy:55-59`. `grep` finds no other
`stages {}` block on any reference page. I checked the executor's linter claim myself. I put each
fixed snippet into a complete declarative file: podYaml's with the standard `options {}`, and
cicd's with a `podYaml(templates: ['k8s'])` agent. I posted both to
`/pipeline-model-converter/validate`, and both answered "Jenkinsfile successfully validated." The
done-record in `plan.md:623-627` names the fix and its commit correctly. `docs/site/` is gitignored,
so there is no committed build to regenerate.

I considered one more point and it is not a finding. podYaml's first example shows `agent {}` and
`stages {}` but no `options {}` block, so it does not show `skipDefaultCheckout()`. The snippet
never claimed to be the file's whole `options {}`. So nothing in it contradicts CHK-1's
`skipDefaultCheckout()` half, or PROP-2, and a file built from it still takes those from their own
pages. Round 1's advisory findings F2 and F3 are already in the close-out report (T1, P10), and I
do not re-raise them.

No findings.
