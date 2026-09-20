# Slice 024 — refinement

## D1 — Port the whole HelmCharts generator into the image, or only what the first migrating app needs?

**Context.** The homelab's architecture model is generated: a generator in HelmCharts walks that repo and publishes a machine-readable picture of what runs where. As apps move out of HelmCharts into per-app deploy repos that Argo CD syncs, that generator stops seeing them. You have ruled that the tools ship as one container image, aac-tools, built in ArgoCDTools, and that HelmCharts keeps its own generator and is only patched — so the image's generator starts as a copy of HelmCharts', adapted to the deploy-repo layout. That generator is about 1300 lines; roughly eight places tie it to HelmCharts' folder layout, and everything else works on rendered Kubernetes documents, a per-app annotation layer and the published model.

**The ask.** Decide how much of the copy the port carries: all of it, or only the parts the first migrating app exercises, with the rest added as later migrations need it.

**Background.** Beyond the core loop that emits one element per container, the generator carries five post-render passes — exposed services, environment-variable bindings between components, upstream-proxy annotations, secret stores and client bindings — plus a pass that models managed Postgres clusters and one that classifies Ceph volumes. (The slice counts four passes and a two-entry cross-producer lookup table; it is five and three, and the omitted pass is substantial with its own failure class — this matters only for sizing.) The first migrating app needs the core loop, the exposed-services pass, the binding pass and, because it uses external secrets, probably the secret-store pass; it needs neither the Postgres, Ceph nor upstream-proxy pass. Most other candidate apps do use Ceph volumes, and several use managed Postgres.

**Why yours.** It is the slice's biggest sizing lever, and you have said you want to limit work — you may prefer the smaller port.

**Recommendation.** Port the whole generator: strip only the eight layout couplings and add the new command-line surface. The trade-off: roughly a fifth of the code ships unexercised by the first consumer, and bugs in that fifth surface at the second migration rather than now.

**The other way.** Port only what the first app needs and grow it per migration — smaller now, but the dropped passes are exactly what the second migration needs, and their absence is silent: an app with a Ceph volume or a Postgres cluster simply emits nothing for it, with no error to catch it.

**If this is wrong.** Full port: a larger slice carrying some dead code for a while. Narrow port: the image is reopened at the second migration, and a silently incomplete model ships in the meantime.

**Operator.** _agree, or comment here_

## D2 — How the register's "scanner and validator images are pinned by digest" line is rewritten now that aac-tools floats

**Context.** The decision register closes its section on push-pipeline checks with one sentence: scanner and validator images are pinned by digest. You ruled at triage that aac-tools is referenced by a floating tag, and the image carries a validator — so the sentence collides with the ruling, and the project's decision discipline has the record move rather than be annotated around elsewhere.

**The ask.** Choose the line the register draws instead, so a future reader knows which images pin and which float.

**Background.** Two images in the estate are digest-pinned today: a third-party vulnerability scanner and a third-party manifest validator. The scanner runs as a pod sidecar the platform force-repulls on every start, so its pin is policy, not mechanism. The validator is run by a plain container-run command on a long-lived build agent, where a floating tag really can serve a stale cached copy — there the pin does mechanical work. Every first-party toolchain image in the estate already floats, so your ruling matches existing practice rather than excepting it.

**Why yours.** The register is your doctrine, and the two candidate lines draw it on different grounds.

**Recommendation.** Narrow by provenance: third-party scanner and validator images are pinned by digest; first-party images we build ourselves follow the estate's floating-tag norm. The trade-off: it draws the line by who built the image rather than by the mechanism that actually makes a stale pull possible, so it is slightly coarser than the truth.

**The other way.** Draw it by mechanism — pin where an image is pulled by a bare container-run on a long-lived agent, float where the platform force-repulls. More accurate, but it makes the existing scanner pin look unnecessary and invites re-litigating a pin that is currently harmless.

**If this is wrong.** Nothing breaks either way; the cost is a later re-edit of one sentence.

**Operator.** _agree, or comment here_

## D3 — Does this slice prove the ported generator reproduces the first app's published elements, identifiers included, or does the next slice?

**Context.** You ruled that element identifiers are kept across a handover: an app moved to a deploy repo keeps its ids and only its owner changes, so nothing that points at it dangles. That makes a strong acceptance check possible — the new producer's output for the first migrating app (KubeCoder) should equal that app's slice of today's published model, same identifiers, only the producing repo's name differing. The next slice is the one that actually installs generation in the deploy repo, and a manual step sits between the two.

**The ask.** Decide whether that equality check is this slice's acceptance or the next slice's.

**Background.** The premise nobody had checked holds: the app already runs in the namespace the new scheme gives it, and its workload names are fixed strings in the chart rather than derived from the release name — so identical output is genuinely achievable, not aspirational. This environment has no container runtime: the image can be built here but not run, so the check would run the ported generator from source in the infrastructure sidecar, which has the right Python, Helm and libraries, against the real deploy-repo checkout, with a test fixture standing in for the small annotation file the deploy repo does not carry yet.

**Why yours.** It decides which slice carries the risk, across a gate that stays manual whichever way D4 goes.

**Recommendation.** Prove it here: the equality check is this slice's acceptance, with the annotation fixture living in ArgoCDTools so no file lands in the deploy repo. The trade-off: one more phase, and the check is pinned to today's published model, so it needs refreshing if that model changes before the slice runs.

**The other way.** Ship with unit tests only and let the next slice prove equality when it wires the deploy repo up — smaller here, but a wrong generator sits undetected until that slice can start, and identifier mistakes are the expensive kind: every reference to a renamed element dangles.

**If this is wrong.** Proving here: a phase spent on a check the next slice would have done anyway. Not proving here: a silently wrong model discovered late, after the work that depends on it has been scheduled.

**Operator.** _agree, or comment here_

## D4 — Does this slice also add the aac-tools toolchain to the KubeCoder catalog, or leave that to the KubeCoder project as planned?

**Context.** You ruled that the tools must run locally as a KubeCoder toolchain, from the same image. The slice, the run order and the KubeCoder project's own card all treat the catalog entry as that project's work — and it is the reason this had to be a separate slice at all: between the image and any repo that gates on it locally sits a step no run loop can take.

**The ask.** Decide whether this slice writes the catalog entry itself, so that the wait between this slice and the next collapses to steps you run by hand.

**Background.** The catalog is not in the KubeCoder project's repo. It is about ten lines of values in HelmCharts, beside the other toolchain entries — a declaration, no code. The KubeCoder card is unstarted; the one question it asks back, what a catalog toolchain requires of an image, I have answered from that project's own reference documentation, so the image can be built to fit without waiting on it. If this slice adds the entry, what remains of the gate is: deploy HelmCharts, then restart the environments that want the tool.

**Why yours.** It puts a change into HelmCharts, which you have asked to keep work out of, and it changes the sequence of manual steps you run between this slice and the next.

**Recommendation.** Add the entry here. The trade-off: it is a HelmCharts change against your stated wish to limit work there — though it is a values declaration, not the generator work that wish was about.

**The other way.** Leave it to the KubeCoder project as planned — HelmCharts stays untouched, but the entry cannot be written or tested there any more cheaply, and the wait it creates is the reason the work was split into two slices in the first place.

**If this is wrong.** If the KubeCoder side has already started the entry, a small duplicate to reconcile — which is what the fact question below is for.

**Operator.** _agree, or comment here_

## Open facts — questions only you can answer

**F1.** Has anything already been started on the KubeCoder side for this toolchain — a catalog entry drafted, or the environment definitions touched? It settles whether the catalog entry stays with the KubeCoder project or comes into this slice.

**Operator.** _answer here_

## Settled

- The slice recorded as open whether the estate's shared image-build helper can build from a subfolder; it can — it takes a Dockerfile path and a build-context path, and the one repo that already builds several images does exactly this — so the one-folder-per-image rework needs no change to the shared build library, which removes the only real risk in that requirement.
- The slice says the folder move touches one recorded path, the root-certificate copy named in the decision register; it touches four places across two repos — the register, two entries in the certificate-rotation runbook, and two more for a second file in the same folder in that runbook and the operator-workstation runbook — all updated by this slice.
- The Architecture repo — which holds the written contract for generated producers (deterministic identifiers, how unmappable things are reported, a marker file each generated producer carries), the canonical validator script and the registry of who produces what — is not checked out here but is reachable; this slice clones it into the workspace, adds it to this environment's repo list, and the port honours that contract.
- HelmCharts' own generator still emits elements for a release already handed to Argo CD, because it never learned to read the key that marks such releases; that is a live, small defect in today's published model, recorded for the follow-on slice that patches HelmCharts, not fixed here.
- The image is built here to smoke-test it but cannot run here, so every gate in this slice exercises the tools from source; image packaging is covered by the build succeeding plus static assertions about the image, the pattern the repo already uses for its existing image.
- The new producer keeps the existing producer's identifier namespace constant verbatim, HelmCharts name and all, because that is the only way kept identifiers work; it carries a comment saying so.
- The producer name the deploy repo publishes under cannot be the obvious one — the registry already gives that name to the app's own source repo — so the image takes the producer name as an argument, and choosing it belongs to the next slice.
- The per-app annotation file sits at the deploy repo's root and generated output goes in a conventional docs folder, uncommitted, matching how the existing generator and the published contract both work.
- The validator ships into the image as the canonical copy, byte for byte; the estate's four existing copies, and the written contract that tells repos to copy the script, are left to your own separate migration task.
- The image carries Python, Helm, git and one YAML library and needs outbound access to the chart repository and the architecture service; it does not carry HelmCharts' deployment tooling, since a deploy repo renders its chart with plain Helm, as its own gate already does.
- Size: five authored phases plus the pipeline's test and documentation phases — seven; repos touched are ArgoCDTools (the folder rework and the new image), AnsibleSpecs (one sentence of the decision register), Ansible (two runbooks and one line of this environment's definition) and, only if D4 is agreed, HelmCharts (the catalog entry).
