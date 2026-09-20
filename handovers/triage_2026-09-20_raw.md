# Triage 2026-09-20 — raw material

Scope: **not the intake queue.** A re-cut of backlog slice 014
(`014_deploy_repo_architecture_producers`, ANS-36), out of an interactive design session the
operator opened on slice 010's close-out entry **S1**. No tracker card is an input.

Inputs:

1. The operator's chat messages of that session, verbatim, in order (below). The assistant's turns
   are not reproduced; where an operator message answers a numbered list, the list's subjects are
   given in brackets.
2. Slice 010's close-out entry S1, verbatim (below).
3. Slice 014's `slice.md` — the whole file, including its section "Carried in from the 2026-09-20
   design session (slice 010 close-out S1)", which records the session's findings and rulings
   (AnsibleSpecs `d006680`, `3157ee4`, `c424498`). Pointer, not copied:
   `slices/backlog/014_deploy_repo_architecture_producers/slice.md`.
4. Slice 012's `slice.md`, section "Carried in from the 2026-09-20 design session" (the ordering
   line). Pointer: `slices/backlog/012_kubecoder_argo_cutover/slice.md`.

## Operator chat, verbatim

### M1

This is not a close out session.

I'm working through the close out of slice 010 and I'm reading S1. This one is important. It reads like we have some optional thing that may break. That's not how I want to run this project. The architecture file is a first class element the current HelmCharts setup. Actually, it's two parts: the static files and the generator. Both absolutely need to keep working as we switch over.

Can you have a look, understand what's there today, and work with me to figure out how we bring it over.

### M2

Cross app references will need to work in a different way. We always had the issue of circular references. The way this works is:

App A deploys partial architecture -> Publish aggregated set -> App B uses published set and builds its own -> Publish aggregated set -> App A can deploy its complete set

We can do the same with our migration. We just have to make sure that we keep the published set in a valid state as we migrate stuff.

As for the branch we describe that's based on the branch we use as a trigger for the Jenkins pipeline. If (and we should) use the prd branch, that means we're publishing the right thing.

As for tools distribution I would suggest a container. Jenkins can pull those in and it means we have a fully managed system for this. It also means we don't need the scripts in the repo anymore. The place? ArgoCDTools is fine.

Please comment on the above.

### M3

[Answering three numbered comments: 1 = cross-app references through the published set, incl. that nothing triggers app A's second pass; 2 = which branch/stage a producer describes; 3 = the container in ArgoCDTools. The assistant's message before it had firmly recommended keeping the UUIDs rather than re-minting, and asked floating vs pinned tag.]

1.

I understand that nothing triggers A's second pass, but in practice this shouldn't have to be an issue. The apps are deployed today, so today we're good. And when we hit something like this for a new app, we manage this bootstrapping manually. It's not something we have to account for now.

2.

Do we push architecture for dev? Implicitly, yes, today, but I have no need for it in my architecture manifest. Can't we just not publish dev architecture and only deploy architecture for kubecoder-prd?

3.

I saw there's a Dockerfile in the root. Please rework that. Preference is to just name it Dockerfile.argocd-hook, but putting it in a folder is fine also. Maybe that depends on the shape of the new one.

I don't understand your point about HelmCharts not being able to go fully script-free. Did you think I wanted to move all scripts over? I'm now thinking the container should be some pipeline utilities thing, with one app being generating the architecture file or something like that. But we do have to understand what we do locally. There's this arch-validate.py script that's copied all over the place. That's already a painful problem. And if we want to be able to validate the generated architecture as part of local validation, we need to be able to generate the architecture locally.

I agree on the rest.

Yes on the floating tag.

Please come back with your response on the above before we proceed.

### M4

[The closing numbered list answers the assistant's four questions: 1 = prd-only as a generator-wide rule or KubeCoder only; 2 = one folder per image in ArgoCDTools; 3 = where the image lives; 4 = is a KubeCoder catalog toolchain acceptable as the way to run the tools locally.]

Don't make it a generator rule. I may have different needs for other apps. I would be open to having a parameter somewhere so that I don't accidentally publish the wrong stage. Something like `--allowed-stages dev,prd`. If I set that to `--allowed-stages prd` and by accident I'm publishing dev, it just bails with a nice error message. Yes, that means that the arguments become something like `--stage dev --allowed-stages prd`, but because this is a multi branch pipeline, the verbosity I think is justified.

Ow, and one thing to realize. I can only ever publish one stage really. The artifact is attached to the pipeline. If the pipeline listens to dev and prd, the architecture would flap. That means that if we ever want to support multiple stages, that single pipeline would have to produce the architecture for both stages. Since we're using branches, I don't see how we can make this to work.

Ok, this means that we can't even have a check like the above. Well, we could just have a `--stage prd` argument, and have that check with the branch we're deploying and just fail the build if it mismatches. Maybe that's the right shape.

After we add the toolchain, we need to do a cross repo scan for the arch-validate.py script and migrate repos over (be it removing the script alltogether, or to use the toolchain). Name the toolchain `argocd-utils`. Possibly this is the name instead of `pipeline-utils`. The tools aren't pipeline specific. If we want to trial run the generation, we need it as a tool in KubeCoder just the same.

We are messing stuff up a little bit putting the script into the Argo CD repo. The architecture stuff really isn't Argo CD specific. The alternative would be to add another container. Or, maybe we just name it `build-utils`. Or maybe `pipeline-utils` was the right shape in the first place. I can't think of a better name, so maybe that is best.

Put it in ArgoCDTools. The reason is that most of the complexity is around the Kubernetes based architecture generation stuff. The agent has that context in this repo. We can move it later if we want.

1. Discussed.
2. Yes.
3. Discussed.
4. I'd say it's a requirement.

### M5

Well, I wasn't thinking it checks the branch name. It knows the stage, right? It has to build it to build the namespace. Can't we use that?

Grrr. We're only putting AaC stuff in it. pipeline-utils invites a grab bag of different things. Yeah, go with aac-tools.

Can you come back on this before we proceed?

### M6

[Answering the assistant's proposal: the guard is a required, single-valued `--stage` and nothing else, no branch check; then re-cut slice 014.]

Go

## Slice 010 close-out, entry S1, verbatim

Demoted one heading level.

#### S1 — HelmCharts architecture generator reads charts/kubecoder/architecture.yaml, which slice 012 deletes

`gen_architecture.py` walks the registry's releases. For each one it reads the chart's image-to-product mapping from `charts/<chart>/architecture.yaml` (`/work/HelmCharts/tools/chart_tools/gen_architecture.py:574,585`).

KubeCoderDeploy's copy of the chart leaves that file behind (plan.md P3), because it is generator input, not chart content. Slice 012 then deletes `charts/kubecoder/` (its requirement 13) and flips the registry entry to `reconciler: argo-cd`. After that, nothing in the tree carries KubeCoder's mapping.

Slice 012's planning should decide where an Argo-managed app's architecture mapping lives.

consult 1, 2026-09-13 — Backlog slice 014 (slices/backlog/014_deploy_repo_architecture_producers/slice.md:44-46) already plans a KubeCoderDeploy architecture producer as a handover from HelmCharts, which models kubecoder today and must stop. The open point is ordering: either 014 lands before slice 012 deletes charts/kubecoder/, or 012 keeps architecture.yaml until 014 lands.

**Consequence:** Once slice 012 lands, the published architecture model may lose the KubeCoder workload-to-product mapping.

**Provenance:** read — plan-writer, plan pass r1; HelmCharts tools/chart_tools/gen_architecture.py:574,585
**Disposition:**
