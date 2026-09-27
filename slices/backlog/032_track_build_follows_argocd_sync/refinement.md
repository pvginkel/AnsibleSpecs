# Slice 032 — refinement

## D1 — When a deploy repo's clone is missing from an environment, does this slice add it to the environments that lack one, or leave it to the tracker's stop message?

**Context.** Since the Argo CD cutover, a green build only commits image pins to the app's deploy repo, and Argo CD rolls that commit afterwards. The build tracker agents run after a push returns at the green build, so an agent that starts its live checks then is testing the previous build. This slice makes the tracker follow the pin commit into the Argo CD sync of every app it touches — on by default, for every Argo-deployed repo, prd promotions included. You ruled that the tracker answers its git questions only from the deploy repo's clone under /work, and that when the clone isn't there it stops with a message saying the repo isn't there and should be added.

**The ask.** "Should be added" names no one. The question is whether this slice also declares the missing deploy repos in the environments that lack them, or whether the stop message is the whole mechanism and each environment gets its clone the first time the tracker stops there.

**Background.** Ten pipelines push pins. Six of their environments — ElectronicsInventory, FieldnotesApp, IoTSupport, ZigbeeControl, Architecture and the app template — declare no deploy-repo clone; FieldnotesDeploy is declared in AIWorkflow's environment rather than FieldnotesApp's. So on the day this ships, the tracker stops after a green build in about six environments. A hand git clone into /work satisfies the check at once. A declaration in an environment's config takes effect only at that environment's next restart, and an agent that restarts its own environment ends its session.

**Why yours.** It's a rollout choice that touches six other repos' environment configs, and you may want the estate consistent before the tracker ships rather than patched as it goes.

**Recommendation.** Don't pre-add. The tracker stops with a distinct exit status — the build was green, the deploy is untracked — and its message names the missing deploy repo, gives the exact git clone line to run now, and says to declare the repo in the environment's config for next time. Trade-off: the first tracked push in each of those six environments stops once and costs that agent one clone before its checks.

**The other way.** The slice also declares the deploy repo in each of the six environments' configs — six more repos edited and pushed, each needing an environment restart that nobody in this slice can run for them, so the benefit lands only after each restart on your side.

**If this is wrong.** One extra clone per environment, or six small config commits later. Nothing breaks.

**Operator.** D1: Correct. (2026-09-27, in chat)

## Open facts — questions only you can answer

None.

## Settled

- The slice assumed dev and prd apps share a deploy-repo branch and differ only by which values file they read; that holds for the keycloak pair, but the KubeCoder prd app follows a separate prd branch that only the promote pipeline advances — so a KubeCoder build's pin commit, though it also rewrites the prd values file on main, correctly waits on the dev app only; matching apps by repo, branch and values file covers both shapes, and nothing in the plan changes.
- The tracker reads Argo CD state straight from the Kubernetes API with the environment's default read-only kubeconfig rather than shelling out to kubectl, because every environment has that kubeconfig but only some have the infrastructure sidecar where kubectl lives, and the Argo CD web API would need a login; read access is verified, and the script cannot modify Applications.
- Ansible's identical copy of the script and its test are deleted: DockerImages' local-home image is the only source (it is what reaches every environment's PATH, and nothing in Ansible calls its copy), the Ansible doc paragraph that says the copy "looks dead and is not" is rewritten to point at DockerImages, and the script's tests in DockerImages are wired into that repo's test entry point, since no gate runs them today.
- KubeCoder's deploy-operations section "A green build is not a rolled dev", which has agents confirm the roll by hand, is updated to say the tracker now waits for the roll.
- For prd promotions, the only promote pipeline in the estate is KubeCoderDeploy's; it gains one handoff line in the same shape as the pin line — repo, commit and the prd branch — so the tracker can follow it, with no shared-library change.
- A build that prints no pin line (a repo that doesn't deploy, or a pipeline missing the line) gets a remark, and the tracker exits with the build's own result, not a failure.
- The tracker stops rather than hangs when Argo CD never picks up the commit within a deadline (webhooks are the only trigger, so a dropped one is silent), on a sync error, or when the app has automatic sync off; on a failed or unhealthy roll it saves the sync message, conditions, failing resources and the Terraform pre-sync hook job's log next to the saved console logs, as it does for failed builds today.
- Size: about four phases across DockerImages (the script and its tests), KubeCoderDeploy (the promote handoff line), Ansible (drop the copy, fix its doc) and KubeCoder (one docs paragraph); no push holds.
