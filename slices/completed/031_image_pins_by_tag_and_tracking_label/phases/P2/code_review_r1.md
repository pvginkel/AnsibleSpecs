# P2 code review, round 1: KubeCoderDeploy pins kube-coder-tunnel-reclaim to a build

Range: `21438b1..3de9ea8` on `phase/031-P2` (KubeCoderDeploy). Gate: green on `3de9ea8` (`gate_r1.log`).

**Readiness.** The phase delivers what it set out to do, and it can merge. `:latest` is gone. Both
stage files pin `images.tunnelReclaim: ":2565"`, and the live registry confirms that build is the
newest (`2565`), with the same digest as `latest` (`sha256:f8fe4025…`). So when the test phase
pushes, kubecoder-dev rolls onto the image it already runs.

- **The chart.** It names no default (`images: {}`), `required`-guards the key
  (`controller-deployment.yaml:228`), and pulls `IfNotPresent` like the other five pinned
  containers (`:229`).
- **The float and its assertions.** The "deliberate float" comment is gone, and so are the render
  test's three `:latest`/`Always` assertions.
- **The render gate.** Five mutations, each run in a throwaway worktree, all failed it: pull
  policy set back to `Always`, a chart default of `:latest`, prd on a different build, the
  `required` guard dropped, and both stages set to `:latest`. So the new checks are real.
- **Promotion.** `Jenkinsfile.promote`'s `prdPins` reads only the seven `kubecoder-*` paths
  (`Jenkinsfile.promote:183-193`), so the bare build number never reaches its `prd-<n>` check.
  prd gets the pin by promotion, as the plan says.
- **The pin writer.** `cicd.writeVersionPins`' `applyPins` skips the comment lines above the key
  and resolves `images.tunnelReclaim` to exactly one line in each stage file
  (`JenkinsPipelineUtils/vars/cicd.groovy:190-245`). So P6's pin list will land.

The executor's plan edit only makes P6's pin-list bullet concrete. It does not change scope.

One exposure is already on record and is not re-reported: prd's pin is refreshed only by
promotion, which puts it within reach of the keep-newest cap. That is close-out Q1.

## Findings

### F1 — Minor · advisory · comment-prose · anchor: none · confidence: high

`chart/values.yaml:7` now opens with "The chart names no default for any image (D47): every image
pin lives in config/<stage>/values.yaml". The same file contradicts it: it names image defaults at
`:112` (`registry:5000/kube-coder-dev:latest`), `:164` (`postgres:18`), `:203`, `:234`, `:262` and
`:294`. The comment it replaced (`21438b1:chart/values.yaml:8-10`) made the claim only for
Build-Main's seven pins, and there it held. The sentence is wrong as written. It has no effect on
the product.

## Note for the doc phase (not a finding)

`README.md:63-67` still says each stage file "names exactly Build-Main's seven image pins" and that
five containers declare `IfNotPresent`. The render gate now asserts eight pins and six containers.
