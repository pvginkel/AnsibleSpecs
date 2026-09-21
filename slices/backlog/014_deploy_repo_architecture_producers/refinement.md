# Slice 014 — refinement

## D1 — Argo CD's model carries both of the webhook relay's edges, which needs a generator change pushed and the environment restarted before the run starts

**Context.** The architecture model holds no Argo CD today: HelmCharts' generator silently drops an app whose stage is flipped to Argo CD, and ArgoCDDeploy has no producer of its own (an earlier planning note that the published model still claimed Argo CD was wrong). The Argo CD standup slice's close-out named the consequence and handed it to this slice: the model shows an internet-facing webhook relay pointing at nothing, because nobody models what it forwards to. Pushes to ArgoCDTools, where the generator lives, are held for you, since a push rebuilds and republishes both of its images.

**The ask.** Give ArgoCDDeploy its own producer, so the relay's edges into Argo CD appear in the model.

**Background.** A probe run against a throwaway clone of ArgoCDDeploy shows a short annotation file is enough: the render — Argo CD's server, repo-server, the application, ApplicationSet and notifications controllers, redis and the webhook relay — is valid and passes the validator. The relay forwards GitHub webhooks to two receivers inside that same render, Argo CD's server and its ApplicationSet controller (the slice's "Argo CD and Fieldnotes" framing was wrong here; Fieldnotes runs its own relay, already modelled). But the generator's per-image upstream annotation takes exactly one target and crashes on a list, so today only one of the two edges can be modelled; accepting a list is a small, contained change. The catch: a deploy repo's local gate runs the generator through this environment's toolchain container, which picks up a rebuilt image only after an environment restart — so a generator change made inside the run cannot serve the same run's ArgoCDDeploy phase.

**Why yours.** It adds a pre-run step you perform, or leaves one real dependency out of the model; you could rule either way.

**Recommendation.** Make the generator change now, before the run, as a quick fix outside the slice — the annotation accepts a list as well as the single form, with a test. You push ArgoCDTools and restart the environment; the run then models both edges, and every gate runs against the live image. Trade-off: the change skips the slice's review loop and costs one push-and-restart before the run can start.

**The other way.** Ship the Argo CD model with the relay-to-server edge only and file a card for the list form plus the ApplicationSet edge — no pre-run step, and the model lacks one real dependency until the card is worked.

**If this is wrong.** Nothing breaks either way: one edge absent for a while, or one extra push and restart.

**Operator.** Agree

## D2 — At a handover, the new producer is registered before the app's stage is flipped, not after

**Context.** KubeCoder's cutover to Argo CD (slice 012, not yet planned) flips its stage in HelmCharts; this slice lands before that flip, and the how-to it writes sets the order every later migration follows. Already ruled: the model loses nothing through the cutover; the element ids stay the same and only the producer changes; the Jenkins jobs and the registration in the Architecture repo are yours to do, and registration comes after the producer's first green build. The slice as written has the registration land "with" the flip, without saying which comes first.

**The ask.** Fix the order of the two keystrokes — registering the deploy repo's producer and flipping the app's stage — for the cutover and for the how-to.

**Background.** Verified in the Architecture repo's collector and pipeline. Because the ids are kept, the new producer and HelmCharts declare the same ids until HelmCharts drops the app; the collector fails the merge on an id declared by two producers, and a failed run stops before the viewer image is built or redeployed, so the published model stays at its last good state. The flip removes the app from HelmCharts' artifact on HelmCharts' next architecture build. Registering a producer that has no successful build fails the collector either way, which is why the first green build comes first.

**Why yours.** It is the order of two keystrokes you perform at every migration, and one order leaves the architecture job red for the minutes between them.

**Recommendation.** Register first, then flip. The collector goes red on the duplicate ids while the published model keeps the app as it was; the flip's HelmCharts build clears the duplicates, and the next run is green with the new producer owning the same ids — nothing ever disappears from the model. Trade-off: the architecture job is red between the two steps (minutes, if done back to back), and any other producer's update waits for the flip.

**The other way.** Flip first, register as soon as HelmCharts' architecture build has run — the collector stays green throughout, and the model loses the app for the gap between the two steps.

**If this is wrong.** A few minutes of a red job, or a few minutes of a missing app; nothing is lost permanently either way.

**Operator.** Agree

## Open facts — questions only you can answer

None — nothing this slice needs is known only to you.

## Settled

- The three stale citations of the federation's producer manual the slice wanted fixed are already gone from all three repos' instruction files — that item drops out; nothing to do.
- KubeCoderDeploy has no prd branch yet — the cutover slice creates it — so KubeCoder's producer job can have its first build only then; ArgoCDDeploy's producer, which builds its main branch and is not a handover, is created and registered first and proves the pipeline shape (container template, image pull, the chart repository's trust, the validator, the archive), so the new pipeline does not run for the first time inside the cutover.
- Argo CD's producer is generated from a short annotation file, the same shape as KubeCoder's, not hand-authored, and it owns the Argo CD product element nobody publishes today — which closes the slice's open question.
- The producer ids are kubecoder-deploy and argocd-deploy: the repo names in kebab case, as the HelmCharts and DockerImages producers already are; kubecoder is already the app repo's.
- KubeCoder's annotation file is copied into KubeCoderDeploy now, with its introduction date, and HelmCharts' copy stays until the cutover slice deletes the chart, because HelmCharts publishes KubeCoder until the prd flip.
- The handover check in ArgoCDTools you asked to fold in stops carrying its own copy of KubeCoder's annotation file and reads the one KubeCoderDeploy commits; its running green is the acceptance for kept ids.
- The how-to is a section of the Argo CD runbook, beside registering an app, carrying the steps and the order from D2 — not a separate document.
- The run pushes KubeCoderDeploy, ArgoCDDeploy, the shared Jenkins library, HelmCharts, this repo and AnsibleSpecs; none deploys anything on push (nothing tracks KubeCoderDeploy yet, Argo CD's own app syncs by hand, the HelmCharts change is a test with no release). ArgoCDTools stays held, as before, because its push rebuilds and republishes both images. The shared Jenkins library has no local gate and every pipeline loads it: the new entry copies an existing entry's shape and the first Argo CD producer build is its canary, so a mistake there breaks every pipeline using the library until reverted — the same trade an earlier slice accepted.
- Size: about seven phases across seven repos — the shared Jenkins library, KubeCoderDeploy, ArgoCDTools, ArgoCDDeploy, HelmCharts, this repo's Argo CD runbook and the Argo CD decision record in AnsibleSpecs — with possibly a one-comment correction in DockerImages.
