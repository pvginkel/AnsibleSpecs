# P7 review — round 1

**Readiness.** The phase does the thing it exists to do, and does it carefully: the fourth
argument lands in all four places `design.md` said three (`design.md:203-204`, `:225-226`,
`:328-330`, `:376`, `:385`), the order matches both shipped halves of the contract — the chart
template's `repo, revision, stage, namespace` and `presync/cli.py:22-25` — and D29/D33 now say the
reattach's namespace is handed rather than found. The credential model reaches every place the
plan named it (`phases.md:39-43`, `decisions.md:271-280`, `:357-369`, `design.md:398-409`), D41's
new paragraph states the tightening as a live comparison rather than a supersession notice, and
the register carries no "formerly…" scars anywhere. `history.md`'s new arc is the right altitude
and the stale "with a dedicated AppRole" clause is gone from the in-cluster arc. Two settlements
beyond the plan's bullets — D32's key scheme and phases.md B.4 reading the key off it — are
defensible and correct against `presync/backend.py:52-54`. One finding blocks: a sentence this
diff added to `design.md` asserts the hook image carries no estate facts and that everything a run
needs beyond its clone arrives as environment variables, and the image shipped in P4 contradicts
both halves. No deterministic gate is recorded green for this commit; this repo has no tooling, so
I verified the diff by reading — the >100-column lines in the changed files are all pre-existing or
table rows, and no link was touched, so the done-record's gate claim holds.

---

## F1 — `design.md` asserts the image carries no estate facts; the shipped image bakes two

**Severity: Major · Impact: blocking · Anchor: contradiction · Confidence: high**

This diff added to `argo-cd/design.md:90-93`:

> The image carries no credential material and no estate facts: everything a run needs beyond its
> own clone arrives as plain environment variables from the hook namespace's Secret (D33), so the
> container knows nothing of OpenBao, ESO or any cluster's endpoints.

The image P4 shipped carries two estate facts, both of them things a run needs and neither of them
arriving as an environment variable:

- `/work/ArgoCDTools/image/terraform.rc:3` — `url = "https://tfmirror.home/"`, copied to
  `/etc/terraform.rc` and pointed at by `TF_CLI_CONFIG_FILE` (`Dockerfile:16`, `:69`). An estate
  hostname, baked in; grep confirms it is the only such string in the repo.
- `/work/ArgoCDTools/image/homelab-root.crt`, installed into the trust store at
  `Dockerfile:60-63`. The homelab step-ca root, without which the mirror's leaf does not verify.

P4's own done-record (plan.md:555-559) records both as riding beyond D31's list precisely because
`terraform init` cannot work without them. The sentence under review is not inherited wording —
the diff introduced it — and it is the passage a reader consults for what the image contains,
sitting one clause after `design.md:88-90`'s "nothing else (D31)".

**Failure scenario.** The homelab step-ca root is rotated (or `tfmirror.home` is readdressed). An
engineer sweeps for consumers, reaches `argo-cd/design.md` — the authoritative model for the
migration, and by P7's own premise the only document a planner reads — and finds the hook image
declared free of estate facts and fully environment-driven. ArgoCDTools is not rebuilt. Its
`/etc/terraform.rc` still names the old mirror and its trust store still carries the retired root,
so `terraform init` cannot resolve `registry.terraform.io/pvginkel/homelab` — which every deploy
repo's Terraform declares — and every migrated app's PreSync hook fails on every sync, with
nothing in the document set pointing at the image as the cause.

This contradicts the phase's stated outcome (plan.md:687-689): the set describes the hook *as it
now is*. Note the neighbouring D31 contents list (`decisions.md:241-243`, "Terraform,
terraform-backend-git, git, and the presync scripts … nothing else") is stale in the same
direction — `librados2`/`librbd1` ride there too (`Dockerfile:35-36`) — but that text is
pre-existing and outside this phase's content mandate; the added sentence is not.

## F2 — the set names an inventory it gives no way to find

**Severity: Minor · Impact: advisory · Anchor: none · Confidence: medium**

`phases.md:44-47` adds an A.2 checkbox owing "the inventory of a run's whole environment", and
`phases.md:67-71` has A.4 author the ExternalSecret "from A.2's enumerated leaves". The inventory
that satisfies both already exists, at
`slices/007_argocd_tools_presync_hook/attachments/credential-inventory.md` — nine env keys, each
with its leaf and property. Nothing in the `argo-cd/` set cites it: `grep -rn "credential-inventory\|attachments/" argo-cd/`
returns nothing. The phase's own premise is a planner working from `argo-cd/` alone, and V21 pairs
the set with "this slice's inventory" as the two inputs to the ExternalSecret; the second input is
reachable only by knowing to look under `slices/`. No product consequence beyond a planner having
to hunt — recorded once, not as fix work.
