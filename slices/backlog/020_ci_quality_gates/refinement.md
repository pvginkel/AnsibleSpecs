# Slice 020 — refinement

## D1 — When trivy finds a fixable critical in an image DockerImages just built, does the build go silently yellow, or page you?

**Context.** The DockerImages pipeline builds only the images whose directory changed (53 image directories), pushes them, and triggers a HelmCharts redeploy; nothing scans them. The requirement asks for trivy "warn-only". The bundle behind it said warn-only first, fail-on-critical later, with reports going to the Telegram IaC bot once it exists — that bot does not exist yet and its bundle is still open. Jenkins signals here are fixed: a failed build pages Telegram for every job; a yellow (unstable) build is silent unless the pipeline raises an alert itself, and the estate already uses silent yellow as its convention for an expected condition. Your standing preference for scheduled signals is red only when there is something to act on.

**The ask.** Add a trivy stage to the DockerImages pipeline that reports on each image the build produced and never fails the build — the open question is what "warn" looks like on Jenkins and whether it reaches your phone.

**Background.** Update-train doctrine treats a critical CVE with a fix available as the one thing that breaks cadence for a single image. Not verified: how many of the 53 images carry such a CVE today — nothing in the dev environment can run trivy, so the noise level on the first run is unknown, and the cost of the alternative rests on that number.

**Why yours.** It changes what shows on Jenkins and whether anything pages you.

**Recommendation.** Trivy scans each image the build produced and prints its critical and high findings in the build log; the build turns yellow — silently, no page — only when an image has a critical vulnerability with a fix available; anything else leaves it green; nothing fails the build. Trade-off: a fixable critical can sit as a yellow build nobody looks at until you open Jenkins — acceptable because this is the warn-only first step and the report destination belongs to the Telegram bot's bundle.

**The other way.** The same, plus a Telegram warning page for each fixable critical, making trivy a real cadence interrupt now; it costs a page on every rebuild of an image whose upstream has not shipped the fix, at a first-run volume nobody has measured.

**If this is wrong.** Nothing breaks: either a critical goes unnoticed for a while or the pages get noisy — a one-line change either way.

**Operator.** Your assumption is incorrect. Builds are stamped and rebuilt on a schedule. So it's not as bad as you make it sound. There is an alert system in JenkinsPipelineUtils. I would suggest we start raising alerts like that, but I do not agree that it should make the build go red/yellow. I want to start with just raising alerts like this. Before we proceed with this: what's the lift on this? If it's easy to integrate trivy, go for it! But if this requires a large investment, then I want to know what the impact is and reconsider. Note that this is done by the version-poller app in DockerImages.
Chat, 2026-09-15, after the lift answer (low: one DockerImages pipeline stage plus a trivy container in its build pod, no shared-library change; scheduled rebuilds from version-poller run through the same job): "Agree" — trivy scans each image right after it is pushed and prints critical and high findings in the log; an image with a critical that has a fix available raises one alert through the existing alert system; the build status never changes; trivy pinned by digest.

## D2 — Provider: gate publish on go vet and the unit tests as filed, even though that gate would not have caught June's two regressions?

**Context.** Every push to the provider repo builds and publishes a new provider version with no test step. The Ansible repo pins exact provider versions in its lock files, so a bad publish reaches it only when someone bumps the lock; the HelmCharts deploy tooling floats onto every new publish automatically — pinning there belongs to the update-train bundle, not this slice. The provider has 51 unit tests and 9 acceptance tests; the acceptance tests run only when explicitly enabled and need a live Ceph/S3 endpoint (and ZFS for the dataset case). go vet and the unit tests pass today.

**The ask.** Run go vet and the tests before publish so a failure stops the publish — the requirement's "currently untested binaries ship".

**Background.** History has real harm here, but not of the kind this gate sees. In June 2026 two provider releases broke real applies for four to five days each. One was config-validation logic no test covers, before or after; the other — an inconsistent result after apply on ZFS datasets — only an acceptance test against live storage sees. A go vet and unit-test gate would have passed both.

**Why yours.** Closing the gap that actually hurt means putting storage credentials and a live-storage dependency into the publish path — a risk and a cost you carry.

**Recommendation.** As filed: go vet and the unit tests run before publish and a failure stops it; the acceptance tests stay a manual run. Trade-off: the class of bug that actually hurt in June still ships; this gate only keeps the existing unit tests honest from here on.

**The other way.** Also run the acceptance tests against live storage before every publish; it costs storage credentials in the build pod, real resources created and destroyed on each push, and publishes blocked whenever Ceph is unhealthy — to catch one of the two June regressions (the other had no test at all).

**If this is wrong.** A provider regression ships as it did in June and is found at the next apply or HelmCharts deploy.

**Operator.** Agreed

## D3 — May the run push all four repos itself, including the HelmCharts and DockerImages pipeline changes?

**Context.** The run loop pushes each repo in its test phase, unattended. For the Ansible repo a push plans only, no converge. For the provider it publishes a new version of unchanged code, which is harmless. For HelmCharts a pipeline-only change deploys nothing, and adding the values schema to the media chart redeploys the media release in prd with identical manifests. For DockerImages a pipeline-only change builds no images, so the push does not exercise the trivy stage at all (the open fact below asks which image to rebuild for that proof). Pipeline files cannot be checked from the dev environment — Jenkins needs a login and there is no Groovy toolchain — so a real build is the only proof.

**The ask.** The run needs to prove each gate works, and for the two pipelines that drive prd deploys the only proof is a push to main.

**Background.** A pipeline that breaks fails its build, which pages Telegram like any failed build; for HelmCharts that halts prd chart deploys — including the ones DockerImages triggers — until someone pushes a fix. Live state does not change either way, because every gate runs before any deploy or publish.

**Why yours.** It is a procedure and a risk you carry: an unattended push to two pipelines that drive prd deploys.

**Recommendation.** Let the run push all four. Each pipeline change is proven only by a real build, and the gates sit ahead of any deploy or publish, so a broken pipeline fails loudly without touching live state. Trade-off: if the HelmCharts pipeline breaks while nobody is watching, prd chart deploys stop until someone pushes a fix.

**The other way.** Hold the HelmCharts and DockerImages pushes for you to push while watching; it costs the run its proof of those two gates, and their acceptance checks are left owed to you.

**If this is wrong.** At worst a halted HelmCharts pipeline with a Telegram page, fixed by one push; no prd state changes.

**Operator.** Agreed

## Open facts — questions only you can answer

**F1.** Proving the trivy stage needs a real image build, which no pipeline-only push triggers, and any rebuilt image redeploys its app in prd by digest. Which image can be rebuilt for that proof without you caring that its app redeploys — ideally one not deployed at all? It settles how the test phase exercises trivy.

**Operator.** I don't know.
(Resolved by the facts, 2026-09-15: version-poller's scheduled rebuilds run through the same DockerImages job, so the test phase proves the scan on the next real image build — no image needs choosing.)

## Settled

- The card says terraform fmt fails today; it was fixed the same day the bundle was written and fmt and validate pass on both Terraform roots, so the Terraform gate lands green and nothing already-red turns red.
- The card's "fix 6 findings" is done: the six ansible-lint findings were fixed in July by a lint-baseline cleanup, one Jinja spacing warning remains, and flipping strict turns that one fatal, so the slice fixes one finding, not six.
- Bare helm lint with chart defaults is not green — three of the forty charts (media, mosquitto, storage) fail it, all three live prd releases that render cleanly with the values actually deployed — so the chart gate lints and renders each release with its prd values and then runs kubeconform on the output against prd's Kubernetes 1.35 (HelmCharts deploys prd only; there is no dev deploy), which lands green today, catches the render class too, and redeploys no prd release just to satisfy the gate.
- The chart gate runs over the releases the build is about to deploy and fails the whole build before anything deploys, so a broken chart blocks its own deploy and pages like any failed build while an unchanged chart never blocks someone else's push.
- The reference chart for the values schema is media — where a wrong key went unnoticed for 23 days; the schema rejects unknown keys, which is the property that catches that class, and its values surface is small (eight top-level keys).
- The Ansible and Terraform gates go into the push job ahead of the Terraform plan; the manual apply job is untouched, since it runs a commit the push job already gated and gating it too would block a break-glass converge on a style rule.
- History found no defect the Ansible lint, Terraform fmt/validate or trivy gates would have caught — the slice stands on the review's principle of zero gates on the push path, not on incidents — and they stay as ruled because each is one cheap stage and the lint baseline did drift dirty unnoticed once.
- Scanner and validator images are pinned by digest, as the bundle asks.
- Size: about six to seven phases — the Ansible-repo gates (lint, yamllint, syntax-check, strict flip; Terraform fmt and validate), the provider gate, the HelmCharts gate, the values schema on the reference chart, the trivy stage — across the Ansible repo, the provider repo, HelmCharts and DockerImages.
