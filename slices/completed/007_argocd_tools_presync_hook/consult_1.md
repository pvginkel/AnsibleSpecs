# Consult 1 — slice 007, generation 1

Verdict: **appended** (P9, P10, P11).

## What I judged against

Every phase P1–P8 is stamped done and the loop-tail sweep is green across all three repos. So the
question was not whether the work builds, but whether the plan's own requirements, rulings and
acceptance criteria are covered by work I can point at. I walked V01–V22 against the merged trees,
read every phase's review result, and traced the advisory findings that no later phase picked up.

## The one that matters — the run gives Terraform no release identity

`presync/cli.py:38-44` is the whole of what a run hands Terraform: the three `-backend-config`
flags and the `-var-file` list. The deploy CLI this hook replaces exports three more per invocation
(`/work/HelmCharts/tools/deploy/deploy_cli/release.py:236-239`), and
`/work/HelmCharts/_providers/providers.tf:76-91` declares `cluster`, `stage` and `namespace` with
`default = ""` — so their absence is not an error. The pilot's Terraform, the one phases.md B.1
lifts rather than rewrites, reads them: `configs/prd/kubecoder/_shared/infrastructure.tf:8,19-25`
renders `name = "${var.namespace}-zfs"` as `-zfs` and takes the non-prd branch of the dataset
ternary, giving `kubecoder-` at 20G where `kubecoder` at 80G was meant. The apply succeeds; the hook
exits 0.

P2's reviewer filed this Major-advisory (r1 F1) on the grounds that a deploy repo *may* legitimately
carry `stage`/`namespace` in its tfvars, so merging P2 harmed nothing that day. That reasoning holds
for the merge and not for the slice: nothing after P2 owned it, it was never carded, and this slice's
own contract artifact points the other way. `attachments/credential-inventory.md:70-72` says the two
"reach the run as Job **arguments**, not Secret keys" — which reads as *Terraform sees them*. It is
also the exact hazard the fourth-argument ruling was written to close, one layer down: a value the
ApplicationSet computes, re-derived in a file in the clone, free to drift from the namespace Argo is
actually syncing into.

P9 forwards `TF_VAR_stage` and `TF_VAR_namespace` from the arguments, and deliberately does not
invent a `TF_VAR_cluster`: `var.cluster` is declared and read by nothing under
`/work/HelmCharts/configs/`, the hook is prd-only, and a cluster identity in the container is the
one estate fact the configuration ruling keeps out of the image. `-var-file` outranks `TF_VAR_*`, so
the export is a floor a deploy repo can still override — worth asserting, because the opposite
precedence would make the phase a trap for Phase B.

## The three seams riding along in P9

All from phase reviews, all advisory, none owned by a later phase:

- **P1 r1 F1** — `git.py:26-35` passes `-c credential.helper=<ours>` without emptying the chain
  first. Harmless in the image (no ambient config), but the test phase re-proves V02 *from this
  pod*, where the ambient `store` helper answers the fetch and V02 checks off false-green. This is
  the only one with a deadline: it has to land before the test phase runs its live proof.
- **P3 r1 F1** — `reattach.claimed_by` returns every match, but no fixture ever produces more than
  one, so an implementation patching only the first passes the suite. `postgres-pas-prd`'s three PVs
  in one namespace is the estate's ordinary re-deploy case.
- **P1 r1 F3 / P2 r1 F3** — two assertions that cannot fail.

## P10 — the chart gate cannot see argument order

`tests/render-consumer.sh:63-66` matches each rendered argument line independently. The entrypoint
takes them positionally, and P5's done-record makes the order load-bearing. Swapping two lines in
`_tf-presync-hook.tpl:45-48` passes every existing `expect`. The phase adds a sequence assertion and
the mutation that proves it bites, with no chart file touched — so `dist/homelab-shared-0.2.0.tgz`
stays byte-identical and no 0.3.0 publish is provoked for a test.

## P11 — and why I absorbed a carded finding

D31 (`argo-cd/decisions.md:240-243`) and design.md `:89-90` are the set's only image-contents
statements and both say "nothing else". The shipped image also carries the distro `python3`,
`librados2`/`librbd1`, `image/terraform.rc` and `image/homelab-root.crt` — each required for the job
to run at all, which is what D31 decided; the list is what is stale. Two agents routed this to a
card as "pre-existing text, outside P7's mandate". I disagree with the routing, not their reading:
the text was written on 2026-08-12 when no image existed, *this* slice built the one that deviates,
P8 just made the set a doc surface this slice owns, and V09 is checked against that text — a test
agent reading D31 and the Dockerfile has to adjudicate a contradiction the slice created. It is two
sentences in a document set this slice already edits. Absorbed beats carded.

P11 also lands the release-identity sentence in design.md's flow step 4 and in the inventory
attachment, so Phase B's authors read the contract P9 implements rather than inferring it.

## Fixed in this session (mechanical residue)

- `presync/cli.py`'s reattach-order comment justified apply-then-reattach by "the volumes Terraform
  just declared", which can never be `Released` and so can never match the reattach's own bound
  (P3 r1 F2). Rewritten to the real reason — a failed apply reattaches nothing. Comment only;
  `kc project lint|test` re-run green; ArgoCDTools `main` @ f6b10ec.
- plan.md's P4 done-record claimed the build assertion was mutation-confirmed "when either package
  is dropped"; on noble `librbd1` depends on `librados2`, so dropping `librados2` alone leaves the
  build green (P4 r2 F1). Corrected in place, with the reason named.
- plan.md's last "Not in scope" bullet still called the reattach fixture a dev-cluster PV, which the
  operator's 2026-08-14 amendment replaced outright. Corrected. AnsibleSpecs `main` @ 8e9d15a.

## What I checked and found sound

V01–V09 trace to P1–P4's code and their live proofs; V12/V13 to P5's tarball, guard and mutations;
V17 to P6's single `iac/tf-backend` entry, confirmed against `policy.hcl.j2`'s rendering and `iac`'s
own read of the same leaf; V20–V22 to P7 and P8. The credential inventory's key set matches what
`presync` actually requires by name — `GIT_USERNAME`, `GITHUB_TOKEN`, the
`TF_BACKEND_HTTP_*`/`SOPS_AGE_KEY` trio `backend.provide()` demands before it starts the daemon —
with the kubeconfig the one thing minted in-pod, exactly as the inventory's carrier table says.
V10/V11 are the test phase's and the operator's, and the plan's ordering constraint already names
the Jenkins-job prerequisite.
