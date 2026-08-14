# Plan review — slice 007, round 1

Scope: `slice.md` R1–R3 against `plan.md`'s phase queue, `verification.json`'s 19 criteria, and
`attachments/credential-inventory.md`, with the load-bearing citations checked against the code.

**What holds.** Every file:line citation in the plan and the attachment was opened and checked —
across `/work/Charts`, `/work/HelmCharts`, `/work/Ansible` and the `argo-cd/` document set — and
they support the sentences they are attached to. Notably: `design.md:321/:361-363/:372/:190-199`
really do state three arguments; `_tf-presync-hook.tpl:40-44` really is the pin plus three
`required`-guarded args and `hook.namespace` appears nowhere in `/work/Charts`; D33 really does
list the dedicated AppRole in what ESO provisions and D41 really does name it first among what
bounds a hook run; `iac-impl:309-349` really is a background daemon inheriting the process
environment with a bounded port wait, and `:322` really does map `GITHUB_TOKEN` from
`GIT_API_TOKEN`; `iac-image/Dockerfile:100-115` really installs Terraform unpinned from the
`noble` suite and `:129-130` pins terraform-backend-git to v0.1.11. Independently derived and
agreeing with the plan: the `eso` AppRole's `shared/prd/*` and `eso/prd/*` globs do cover all five
provider-credential leaves (a trailing `*` in an OpenBao ACL matches across `/`), and
`iac/tf-backend` is genuinely absent from `openbao_eso_kv_paths` while present in
`openbao_iac_agent_kv_paths` — so P6's premise that the age keypair is the slice's one OpenBao
policy change is correct. P1's environment claims were re-verified this pass: 6061 is bound in
this container and `terraform-backend-git` is not on `PATH` in the `iac` sidecar.

Task shape (`cross-cutting`), the six `Target:` lines, phase sizing and ordering, and the
attachment's altitude are all sound — see "Checked and clean" at the end.

---

## F1 — P5's pin-correction fallback does not exist under the plan's own ordering

**Problem.** V11 requires the library chart's pin to "name the actual first `IaC/ArgoCDTools`
build". P5 (`plan.md:373-374`) provides for the case where it is not `1`: *"the correction rides
this same bump rather than earning a 0.3.0."* That fallback is not available. Correcting the pin
means editing `charts/homelab-shared/values.yaml`, which changes the packaged chart, which means
re-packaging `dist/homelab-shared-0.2.0.tgz` — and by then that tarball is already committed and
tracked.

**Evidence.**
- The first build number only comes into existence after `ArgoCDTools` is pushed, and the plan
  places that push in the **test phase**: *"must be hand-wired by the operator before the test
  phase pushes `ArgoCDTools`"* (`plan.md:200-203`). The test phase runs after P1–P6, so at P5 time
  the number is unknowable.
- `/work/Charts/tests/publish.sh:111-116` fails on `git status --porcelain -- 'dist/*.tgz'` for any
  already-tracked tarball (it filters out only `??`, `A `, `AM` — i.e. newly added ones), and
  `:118-123` re-checks history with `--diff-filter=MDR`. A modification to a committed 0.2.0
  tarball fails both.
- Confirmed by precedent that the risk is real but small: slice 006's verification record settles
  on *"IaC/Charts #1 SUCCESS, image pushed"* — a hand-created job's first build is `#1`. So
  `imageTag: "1"` is likely right; what is wrong is the plan's stated escape hatch if it isn't.

**Impact.** If the first build is not `1` (an operator test-run of the new job before wiring is
enough), the test phase meets a red `publish.sh` with no ruled path through it: the only way to
satisfy V11 is the 0.3.0 bump P5 says it is avoiding. Operator-decidable, because the choice —
accept the `#1` assumption, or restructure so the pin is set after the first build — is a
sequencing call, not a mechanical one.

## F2 — the `argo-cd/` doc-set amendments are load-bearing for slice 009 and no criterion covers them

**Problem.** Two rulings make amendments to the authoritative document set a deliverable of this
slice, and `verification.json` asserts none of them.

**Evidence.**
- `plan.md:118-126` requires `design.md` to change from three arguments to four in four named
  places (`:321`, `:361-363`, `:372`, `:190-199`), the ApplicationSet to gain `hook.namespace`, and
  D29/D33 to gain a note that the namespace is passed rather than derived. `plan.md:128-136`
  requires `phases.md` A.2, D33 and D41 to move to the enumerated-leaves model.
- The plan states the failure mode itself: *"slice 009's planner reads design.md, builds a
  three-parameter ApplicationSet, and every migrated app fails to render against a
  `required`-guarded argument nothing supplies — a failure landing in the wrong slice with nothing
  pointing back here."*
- All 19 criteria were read. None mentions `design.md`, `phases.md`, D29, D33 or D41. V12 asserts
  only that the entrypoint and the **library chart template** agree on four arguments — `/work/Charts`,
  not the document set.
- Scope ambiguity compounds it: `/work/Ansible/docs/slice-doc-plan.md` enumerates five surfaces and
  `argo-cd/` is not among them. Its surface 1, `/work/AnsibleSpecs/decisions.md`, is the 89 KB
  homelab-doctrine file — a different file from the 27 KB `/work/AnsibleSpecs/argo-cd/decisions.md`
  that holds D1–D46.
- **Mitigating, and it matters:** slice 006's doc phase did commit `a75dda6 006 docs(argo-cd): the
  library chart as it shipped`, so the doc-writer does in practice reach this set, and the rulings
  are specific enough to execute from.

**Impact.** The single cross-slice contract this slice exports rests on a phase whose governing doc
does not name the file set, with nothing verifying the result. The consequence surfaces in slice
009 as a render failure with no pointer back. Operator-decidable: add a criterion, or accept the
006 precedent as sufficient.

## F3 — the committed non-secret cluster configuration ships with no criterion and no anti-drift mechanism

**Problem.** The attachment's §"Non-secret, committed in `ArgoCDTools`" specifies roughly a dozen
values — four `HOMELAB_*` provider settings, six `TF_VAR_*` inputs, `GIT_USERNAME`,
`TF_BACKEND_HTTP_ENCRYPTION_PROVIDER`, `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` — to be copied into
`ArgoCDTools` from `/work/HelmCharts/_providers/clusters.yaml:12-42` (verified: all ten named keys
are present in that range). Nothing verifies the copy.

**Evidence.** P2 (`plan.md:278-285`) lands them and argues the carrier choice against the
alternatives. Of the 19 criteria, V04 covers tfvars from the clone, V05 the synthesised kubeconfig,
V14 the env-var delivery shape and V15 the *inventory's* completeness — none asserts that the
committed configuration exists in `ArgoCDTools`, is complete, or agrees with `clusters.yaml`.

**Impact.** This is production cluster fact duplicated into a second repo with no test binding the
copies. A later `clusters.yaml` edit leaves the hook applying against stale Ceph/S3/backup
endpoints, discovered at sync time in whichever app syncs first. The plan names drift as the reason
*not* to duplicate into 45 deploy repos, then duplicates once without a guard.

## F4 — the age public key's carrier is left open, inside the operator handover

**Problem.** A decision the plan leaves explicitly unmade determines what the operator must run.

**Evidence.** `attachments/credential-inventory.md:63-65` says of
`TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS`: *"Public halves are not secrets, so either carrier works"* —
unresolved. Then `:100-105` hands the operator a keystroke conditioned on that same open question:
*"If the recipient (public half) is to reach the Secret through ESO rather than through committed
configuration, the leaf needs to carry it"*, followed by a `bao kv patch ... age_public_key=`
command. V17 asserts one keypair in one leaf but is silent on the recipient's carrier.

**Impact.** The operator's keystroke list — the one artifact R3 says is this slice's to hand over —
contains an `if` the operator cannot resolve without re-deriving the design. It also moves P6's
boundary: under one answer P6 is an `openbao_eso_kv_paths` entry, under the other it is that plus a
`kv patch` on a leaf whose property does not yet exist.

---

## Advisory

- **A1 — over-spanned citation.** `plan.md:83-84` cites `openbao.yml:91-104` for the `eso`
  AppRole's globs; `openbao_eso_kv_paths` ends at `:96` and `:97-104` is the separate
  `openbao_eso_dev_kv_paths`. The claim is correct and P6 and the attachment both cite `:91-96`
  properly — only this one range is loose.
- **A2 — wrong reason, right instruction.** The ordering constraint (`plan.md:206-208`) calls
  `render-consumer.sh:104-106` a second place asserting "the rendered strings". It asserts only the
  image line under `--set hook.imageTag=42`. It does still need attention — it re-renders the same
  fixture, so a `required`-guarded fourth argument breaks it until `tests/consumer/values.yaml`
  carries `hook.namespace` — but not for the reason given.

## Checked and clean

- **AC completeness.** R1 → V01–V09, R2 → V10–V13, R3 → V14–V18, plus V19 on scope. No requirement
  is dropped or softened without a ruling. R3's bolded **dedicated AppRole** clause *is* dropped,
  but under an explicit, dated, well-argued ruling (`plan.md:34-65`) that records the operator's
  challenge, three grounds and three accepted costs — the supersession is edited in place at R3
  rather than chained as a correction, which is the right shape. No doc-truth universals.
- **Task shape.** `cross-cutting` is correct and rests on facts that hold: `/work/ArgoCDTools` has
  no commits, R2 lands in `/work/Charts`, R3 in `ansible`'s OpenBao configuration.
- **`Target:` lines.** `../ArgoCDTools` and `../Charts` are real sibling repos; `ansible` is a real
  `kc project list` component and the right one for `roles/openbao`. P1's admission that the target
  has no deterministic gate until `project.yaml` exists is honest and correctly placed.
- **Phase boundaries.** Six phases, producers-first (contract → apply → reattach → image → chart →
  OpenBao), each judgeable on its own diff. No testing or doc phase is planned — the loop owns
  those.
- **Attachment altitude.** `credential-inventory.md` is a key/leaf/property contract plus PAT
  permissions plus `bao` commands — genuinely underivable estate facts that slice 009 consumes. No
  prescribed symbol names, no pseudo-code, no specced implementation. Correct altitude; F4 is about
  one unresolved decision inside it, not its existence.
- **No doc-phase content.** The plan carries no doc-deliverable section and no drafted prose; the
  document amendments live in the rulings, which is their right home.
