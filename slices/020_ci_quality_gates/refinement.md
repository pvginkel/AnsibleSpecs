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

## D4 — Fix the storage chart's document separator now, which redeploys storage in prd once at the run's push?

**Context.** The plan stands at six phases; everything but the chart-gate phase is settled. That gate lints and renders exactly the releases a build is about to deploy, with their prd values, and fails the whole build — deploying nothing — if any of them fails. You were told in the first round that the three charts failing bare helm lint (media, mosquitto, storage) fail only with chart defaults and render cleanly with their deployed values, so all three are left alone and no prd release is redeployed just to satisfy the gate. That was wrong for storage. The plan-writer re-ran lint with each release's real prd values and the session verified the result: media and mosquitto pass; storage fails lint with its real values too. Its scheduled-jobs template emits a document separator whose whitespace trimming glues the next document onto the separator line — helm template and helm upgrade split that leniently, which is why storage deploys fine, but helm lint rejects it. The earlier grounding had checked storage by render, not by lint; that is how the settled item got it wrong.

**The ask.** Fix the separator in the chart-gate phase — a storage chart change, so the push redeploys storage in prd once: the one redeploy the first round said the gate would not cause.

**Background.** The gate will select storage within days of landing whatever we do: storage is selected whenever its chart or config changes, whenever the shared Terraform surface changes (which selects every release), or whenever the live digest of any of its four images (debian, rclone-backup, samba, backup-server) moves — and those images carry the weekly rebuild stamp that version-poller acts on. A storage deploy is routine: it was last deployed on the 14th by an earlier slice, and every storage deploy restarts its two deployment pods (samba and backup-server) because the chart stamps a render-time annotation. The fix changes no rendered object.

**Why yours.** It overturns what you were told — no prd release redeployed for the gate — and puts a samba and backup-server restart at the run's push rather than at a moment you pick.

**Recommendation.** Fix the separator in the chart-gate phase. The rendered objects do not change; the push redeploys storage in prd once and its two pods restart, as on every storage deploy. Trade-off: that restart happens at the run's push, which the run's test phase watches, not at a time you choose.

**The other way.** Leave storage alone: the gate goes red the first time a build is about to deploy storage — most likely the next weekly rebuild of one of its images, unattended — and that failed build deploys nothing, every other release it selected included, until someone fixes the template. It does not avoid the storage redeploy; it only moves it.

**If this is wrong.** A brief samba and backup-server pod restart at an unplanned moment. Not verified: how long a samba restart interrupts the share.

**Operator.** Agree

## D5 — kubeconform in strict mode, which rejects unknown fields and duplicate keys, or in default mode?

**Context.** The chart gate, settled in the first round, renders each release a build is about to deploy with its prd values and runs kubeconform on the output against prd's Kubernetes 1.35 — with nothing said about strictness. Strict mode additionally rejects fields the schema does not know and keys set twice; default mode lets both through. Chart CI is the gate you said you had no strong feelings about.

**The ask.** Pick the mode the gate runs in — which decides whether it also catches a Kubernetes field a template misspells or places at the wrong level, and whether it lands green without touching another chart.

**Background.** The plan-writer ran both modes over all 43 rendered prd releases, and the session re-verified the one hit. Default mode: every release passes (341 resources valid; 96 custom resources skipped for lack of published schemas). Strict mode: one fails — the Home Assistant MCP server's deployment sets its container command twice, and Kubernetes keeps the second, which is what the live pod runs (read from prd). Deleting the dead first line leaves the live command unchanged. That chart was last deployed on the 14th, and its pod restarts on every deploy because it stamps the same render-time annotation.

**Why yours.** Strict mode is the one that catches the wrong-key class in rendered manifests, but it costs a change and a redeploy of an otherwise-untouched chart — coverage against churn on a gate you were indifferent to is your call.

**Recommendation.** Strict mode, and delete the dead first command line in the chart-gate phase. The gate then also rejects a Kubernetes field a template misspells or puts at the wrong level — the class that cost 23 days in 2024, caught in rendered manifests rather than in values. Trade-off: one redeploy and pod restart of the Home Assistant MCP server at the run's push, with no change to its configuration.

**The other way.** Default mode: lands green with no chart change; a misspelled or misplaced Kubernetes field in a template passes the gate.

**If this is wrong.** In strict mode, a future chart edit Kubernetes would have tolerated turns a build red until the template is corrected; in default mode, a misplaced field ships silently.

**Operator.** Agree

## Open facts — questions only you can answer

**F1.** Proving the trivy stage needs a real image build, which no pipeline-only push triggers, and any rebuilt image redeploys its app in prd by digest. Which image can be rebuilt for that proof without you caring that its app redeploys — ideally one not deployed at all? It settles how the test phase exercises trivy.

**Operator.** I don't know.
(Resolved by the facts, 2026-09-15: version-poller's scheduled rebuilds run through the same DockerImages job, so the test phase proves the scan on the next real image build — no image needs choosing.)

## Settled

- The card says terraform fmt fails today; it was fixed the same day the bundle was written and fmt and validate pass on both Terraform roots, so the Terraform gate lands green and nothing already-red turns red.
- The card's "fix 6 findings" is done: the six ansible-lint findings were fixed in July by a lint-baseline cleanup, one Jinja spacing warning remains, and flipping strict turns that one fatal, so the slice fixes one finding, not six.
- *Corrected 2026-09-15 — see D4: storage fails helm lint with its real prd values too (media and mosquitto do pass), so the gate does not land green without one chart fix and one storage redeploy.* Bare helm lint with chart defaults is not green — three of the forty charts (media, mosquitto, storage) fail it, all three live prd releases that render cleanly with the values actually deployed — so the chart gate lints and renders each release with its prd values and then runs kubeconform on the output against prd's Kubernetes 1.35 (HelmCharts deploys prd only; there is no dev deploy), which lands green today, catches the render class too, and redeploys no prd release just to satisfy the gate.
- The chart gate runs over the releases the build is about to deploy and fails the whole build before anything deploys, so a broken chart blocks its own deploy and pages like any failed build while an unchanged chart never blocks someone else's push.
- The reference chart for the values schema is media — where a wrong key went unnoticed for 23 days; the schema rejects unknown keys, which is the property that catches that class, and its values surface is small (eight top-level keys).
- The Ansible and Terraform gates go into the push job ahead of the Terraform plan; the manual apply job is untouched, since it runs a commit the push job already gated and gating it too would block a break-glass converge on a style rule.
- History found no defect the Ansible lint, Terraform fmt/validate or trivy gates would have caught — the slice stands on the review's principle of zero gates on the push path, not on incidents — and they stay as ruled because each is one cheap stage and the lint baseline did drift dirty unnoticed once.
- Scanner and validator images are pinned by digest, as the bundle asks.
- Size: about six to seven phases — the Ansible-repo gates (lint, yamllint, syntax-check, strict flip; Terraform fmt and validate), the provider gate, the HelmCharts gate, the values schema on the reference chart, the trivy stage — across the Ansible repo, the provider repo, HelmCharts and DockerImages.
