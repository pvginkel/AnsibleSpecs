# P11 — code review r1

`git diff dc5300723a678b84a24a3ff3212d042956becc75..HEAD` on `phase/007-P11`, six files, documents
only.

## Readiness

**The phase's outcome holds and every factual claim it added checks out against the shipped
repos.** I verified each one rather than taking the done-record's word: D31's new inventory
(`decisions.md:240-257`) and design.md's ArgoCDTools paragraph (`:88-93`) name exactly what
`/work/ArgoCDTools/Dockerfile` bakes — `python3` (`:37`), `librados2`/`librbd1` (`:35-36`, with the
build-time `CDLL` assertion at `:89`), `image/terraform.rc` behind `TF_CLI_CONFIG_FILE` (`:16,70`)
and the step-ca root (`:62`) — and the reason attached to each matches the Dockerfile's own account
of it (`:23-29`, `:58-61`, `:66-69`), including the apply-not-init failure mode. The release-identity
sentence in flow step 4 (`design.md:342-348`) matches the code it describes: `presync/cli.py:36`
calls `terraform.release_identity()` before `terraform.init()` at `:44`, `presync/terraform.py:56-57`
sets `TF_VAR_stage`/`TF_VAR_namespace` and nothing else, and no `TF_VAR_cluster` is exported
anywhere. The two supporting claims are true independently: `_providers/providers.tf:76-92` declares
`cluster`/`stage`/`namespace` with `default = ""`, and `var.cluster` is read by nothing under
`/work/HelmCharts/configs/` (the only `var.cluster*` hits in the tree are `var.cluster_id` in
`terraform-modules/static-{rbd,cephfs}-pv/main.tf`), so the attachment's `:73-76` bullet and
design.md's `:347-348` stand. The `argo-cd` set carries no other statement of the image's contents
or of the run's inputs that this diff left stale — I grepped the whole set (excluding `archive/`) for
the old inventory phrasing, for `TF_VAR`/`tfvars`/`envFrom`, and for line-numbered cross-references.
P7 r2 F3, which this phase absorbs, is fully discharged: all four things it named are now in D31.

Two judgement calls I checked and accept. **Editing `verification.json` in place** is not
goalpost-moving here: V09's description quoted the very sentence this phase exists to correct, the
plan anticipated the coupling (`plan.md:940-941`), P3/P10 set the precedent in this slice, and the
criterion's bar survives intact — "nothing general-purpose", "nothing cloned at runtime except the
deploy repo", Terraform unpinned, terraform-backend-git pinned, `support/iac-image/` untouched. The
renumbered pointers land on the right passages (V02 `:331-334`, V04 `:339-340`, V06 `:349-351`, V09
`decisions.md:240-257`, V16 `:334-343`/`:360-377`, V21 `:271-288`), and several were *stale before*
this phase rather than merely shifted, so this is a correction and not just a rebase of numbers.
**Writing D31 as if it had always been true**, keeping its 2026-08-12 attribution while carrying what
P4 discovered on 08-14, is what the plan's voice bullet asked for. `history.md` gaining no new arc is
right for the same reason: no position moved.

**Gate state is unverified for this commit** and `/work/AnsibleSpecs` has no `.kubecoder` tooling, so
there is nothing to re-run. I checked the two mechanical properties the done-record claims instead:
`verification.json` parses (22 items), and no added line in a `.md` file exceeds 100 columns.

Both findings below are Minor and advisory; nothing here blocks the merge.

## Findings

### F1 — Two places still say the Secret is the whole of a run's environment

**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

The sentence this phase added to flow step 4 contradicts the clause it was appended to.
`design.md:339-343` reads "with `config/<stage>/*.tfvars` from the clone (D14) **and the whole of the
rest of its environment** … from the single `argocd-hook-credentials` Secret", immediately followed
by "The run's own identity comes from neither: the entrypoint exports … `TF_VAR_stage` and
`TF_VAR_namespace`". Both cannot be true, and the code says which one is not:
`presync/terraform.py:56-57` writes those two variables into the run's environment itself, from argv,
with no Secret involved. The same overstatement sits uncorrected 60 lines further down in the
credentials-and-identity table, where the `argocd-hook-credentials` row's scope is "The whole of a
run's environment" (`design.md:404`) — that one has no adjacent sentence walking it back.

This is the same class of imprecision the phase exists to remove: the attachment's old *"reach the
run as Job arguments, not Secret keys"* is called out in the plan (`plan.md:944-946`) as the reading
that produced P9's gap, and "the Secret is the whole of a run's environment" is that reading stated
from the other side. It is advisory because nothing is built from it — a slice-009 author writing the
ExternalSecret takes the key list from this slice's attachment, which is explicit that `stage` and
`namespace` are not Secret keys, and a B.1 author reading flow step 4 gets the corrective sentence in
the same breath.

**Failure scenario.** None traced. A reader who reaches only the table at `design.md:400-407` — the
row that says "the complete inventory" — concludes a run's Terraform sees exactly what ESO composed,
and would look for `TF_VAR_stage` among the Secret's keys before finding it in `terraform.py`.

### F2 — V20's renumbered pointer stops one line short of the expression the criterion names

**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

V20 requires "the ApplicationSet `parameters:` block, with the namespace carrying the same
`<app>-<stage>` expression the set already computes for `destination.namespace`". Its renumbered
evidence pointer is `design.md:196-203` (`verification.json:211`). The block runs 196-**204**: line
203 is `- name: hook.namespace` and line 204 is `value: '{{ index .path.segments 2 }}-{{ index
.path.segments 3 }}'` — the expression the criterion is about. The pointer therefore excludes the one
line that proves the half of V20 it was renumbered for; the neighbouring `:205-207` covers the
`destination:` block, not the parameters block, so nothing else in the set closes the gap. The
pre-existing `decisions.md:218-222` in the same entry lands short the same way — D29's "the Job is
handed as an argument" completes at `:223-224` — though that pointer neither moved nor was touched
here.

**Failure scenario.** None traced; a test agent checking V20 off reads the surrounding block anyway.
The cost is that a pointer pass whose whole purpose was accuracy leaves the criterion's load-bearing
line outside the range it cites.
