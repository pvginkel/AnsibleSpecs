# Straightforward changes from triage, 2026-08-16

**Cards covered:** #616, #619, #583, #618, #576.

**Do not close these cards.** They stay in the Triage Inbox with their rubric labels on. Close them
out once the work below is done and committed — that is a separate, explicit step at the end.

This document is self-contained on purpose: it was written in a triage session you did not see, and
it carries every fact you need. Where it cites a line number, read the file first — the numbers are
from 2026-08-16 and edits shift them.

Three repos are touched: `/work/Ansible`, `/work/AnsibleSpecs`, `/work/ArgoCDTools`. Each is its own
git repo; commit in each. Run `kc project lint` in `/work/Ansible` before proposing its commit —
linting there is manual, there is no pre-commit hook.

Ordering does not matter; the items are independent.

---

## 1. #616 — generalise the kubeconfig limitation sentence

**File:** `/work/Ansible/docs/live-infra-access.md`

**What is wrong.** The doc states the mounted kubeconfigs' write limitation only for the `nodes`
resource, which reads as a narrow exception. The real limit is broader.

**The fact to write.** `~/.kube/config-prd-write` is the `kubecoder-rw` identity: a namespaced-edit
identity with **no cluster-scoped verb whatsoever**. It cannot get, list or patch PersistentVolumes,
and it cannot create namespaces, on prd. `nodes` is one instance of the general rule, not the rule.

**Why it matters, for the sentence's tone.** Slice 007 planned its PV reattach proof around that
write path and found it could not do the job; the fixture's cluster-scoped objects had to be created
over SSH (`sudo microk8s kubectl` on srvk8s1) instead. The next slice should plan against the real
limit, so the sentence needs to generalise rather than list a second exception.

**Verify:** the doc no longer implies `nodes` is special, and a reader learns that cluster-scoped
operations need the SSH path.

---

## 2. #619 — make the credential inventory findable from the argo-cd set

**Files:** under `/work/AnsibleSpecs/argo-cd/` — `phases.md` (items A.2 and A.4)

**What is wrong.** phases.md A.2 and A.4 both owe, and refer to, "the inventory of a run's whole
environment". That inventory exists at

```
/work/AnsibleSpecs/slices/completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md
```

and is cited nowhere under `argo-cd/`.

**Why it matters.** Slice 009 plans from the `argo-cd/` documents, not from slice 007's `plan.md`. As
things stand a planner reading the set cannot find the inventory the set tells it to use.

**What to do.** Two acceptable fixes; the card left the choice open.

- **Preferred — cite it.** Add an explicit path reference from the A.2/A.4 items (or from the set's
  index) to the attachment path above. Cheapest, and keeps one copy as the source of truth.
- **Alternative — promote it.** Move the inventory into `argo-cd/` and leave a pointer behind in the
  slice attachments folder. Choose this only if you judge slice attachments too unstable to cite.

**Verify:** starting from `argo-cd/phases.md` alone, a reader can reach the inventory.

---

## 3. #583 — correct a false comment in the managed-vm Terraform module

**File:** `/work/Ansible/terraform/modules/managed-vm/versions.tf`, around lines 9-11

**What is wrong.** The comment says the homelab provider binary is "baked into the modern-app-dev
image, which is the version source of truth", and cites
`slices/completed/embed-homelab-provider.md`. Both halves are false, and were verified false three
separate times during slice 013 (PC r1, PC r2, and the doc phase).

**The truth.** Neither `support/iac-image/Dockerfile` nor `DockerImages/modern-app-dev/Dockerfile`
bakes a provider or a filesystem mirror. Both resolve `registry.terraform.io/pvginkel/*` from the
`tfmirror.home` network mirror via `/etc/terraform.rc`.

**What to do.** Correct the comment to describe the network mirror, and repoint the citation to
`slices/completed/tf-provider-registry.md`.

**Context you do not need to act on:** the twin claim in `docs/runbooks/operator-workstation.md` was
already fixed by slice 013's doc phase. This one survived because it is a code comment in a Terraform
module, outside that diff's work list.

**Verify:** the comment describes the mirror, and the cited slice file exists.

---

## 4. #618 — the hook image's consumer record (the wide scope)

The operator ruled this **wide**: not just "point at the hook image", but complete both consumer
lists and write the runbook `decisions.md` already promises.

**Already done — do not redo.** The card's original complaint was that D31's contents list was stale.
Commit `97b5313` ("007 P11") fixed that on 2026-08-14. `argo-cd/decisions.md` D31 now spans roughly
lines 240-257 and names `librados2`/`librbd1`, the `TF_CLI_CONFIG_FILE` Terraform CLI config and the
step-ca root explicitly, matching `/work/ArgoCDTools/Dockerfile` item for item.
`argo-cd/design.md` (around lines 88-93) was rewritten in the same commit and is accurate.

### 4a. Stale header comment in the hook image Dockerfile

**File:** `/work/ArgoCDTools/Dockerfile`, lines 1-5

The header comment still carries the pre-P11 four-item list — "The image carries exactly that job
(D31): Terraform, terraform-backend-git, git and the presync entrypoint." — which the file's own body
contradicts about 25 lines below. It is a comment, not an instruction; no build behaviour changes.

Bring it in line with what the Dockerfile actually installs: `ca-certificates`, `curl`, `git`,
`librados2`, `librbd1`, `python3`, `terraform`, `terraform-backend-git` (v0.1.11, via
`COPY --from`), `image/homelab-root.crt` into the trust store, `image/terraform.rc` at
`/etc/terraform.rc` via `TF_CLI_CONFIG_FILE`, and `presync/` into `/app`. Read the file rather than
trusting this list verbatim.

`/work/ArgoCDTools/README.md` (around lines 130-158) is already correct — use it as the model.

### 4b. Complete the step-ca root consumer list

**File:** `/work/AnsibleSpecs/decisions.md`, section "Root rotation mechanism", around lines 157-171

Line 165 is the precedent: a bullet naming, by path, the out-of-repo copies of `homelab-root.crt`
that a rotation must update in the same change window. It currently names two, both in HelmCharts:

- `/work/HelmCharts/homelab-root.crt`
- `/work/HelmCharts/charts/nginx/files/ca/homelab-root.crt`

There are **four** copies, all byte-identical to the Ansible canonical copy (md5 `aa4e1a5c…`). The
two missing ones:

- `/work/ArgoCDTools/image/homelab-root.crt` — the presync hook image
- `/work/DockerImages/kube-coder-dev-base/homelab-root.crt`

Add both to that bullet.

### 4c. Complete the tfmirror.home consumer list

**File:** `/work/Ansible/docs/runbooks/operator-workstation.md`, around line 90

The line reads to the effect of "Both the `modern-app-dev` dev container and the `iac` image set
`TF_CLI_CONFIG_FILE=/etc/terraform.rc`…" — a consumer list of two. There are **four** identical
`terraform.rc` copies (md5 `f2af2394…`):

- `/work/ArgoCDTools/image/terraform.rc` — missing
- `/work/DockerImages/kube-coder-dev-base/terraform.rc` — missing
- `/work/DockerImages/modern-app-dev/terraform.rc` — listed
- `/work/Ansible/support/iac-image/terraform.rc` — listed

Add the two missing consumers, so a readdressing of `tfmirror.home` has something telling it which
images are affected.

### 4d. Write the promised rotation runbook

**File to create:** `/work/Ansible/docs/runbooks/step-ca-root-rotation.md`

`/work/AnsibleSpecs/decisions.md:166` promises this runbook by name and `:169` lists writing it as an
outstanding TODO. It does not exist. `/work/Ansible/docs/runbooks/step-ca-bootstrap.md` covers
intermediate and JWK rotation only and mentions no images at all.

**This is the one item here that is more than a text edit** — it needs the actual rotation procedure,
not just a list. If you cannot ground the procedure from the repo, write the part you *can* ground
— the four-copy consumer inventory from 4b, the four-copy `terraform.rc` inventory from 4c, and the
requirement that all copies move in one change window — and say plainly in the runbook and in your
report that the step-by-step rotation procedure is still owed. Do not invent a procedure. If it
looks like it wants a slice, say so and leave it; the consumer inventory is the part that closes the
card's stated gap.

Match the house style of the other files in `docs/runbooks/`.

**Verify (4a-4d):** a sweep that rotates the step-ca root, or readdresses `tfmirror.home`, can find
every affected artefact from the docs alone.

---

## 5. #576 — record the OIDC-on-the-apiserver ruling

**File:** `/work/AnsibleSpecs/decisions.md`

**What happened.** Card #576 asked a doctrine question: do we want OIDC on the prd microk8s
apiserver at all? The operator ruled **yes**, at triage on 2026-08-16, with the reason: they want
SSO on Headlamp, and Headlamp SSO only works if the apiserver trusts the issuer.

**Why the entry is needed.** The card states the answer belongs in `decisions.md` because it affects
more than Headlamp. Record the decision now; the implementation is separate work and is **not** part
of this document.

**What the decision entails, for the entry's substance.** Headlamp forwards the id_token straight to
the kube-apiserver, so chart flags alone do nothing. Making it work needs, on the prd apiserver:

- `--oidc-issuer-url=https://auth.ginbov.nl/realms/homelab`
- `--oidc-client-id=headlamp`
- a username claim and a groups claim
- RBAC binding the mapped Keycloak group

That is an Ansible/microk8s change plus RBAC; Headlamp SSO follows from it. The rejected alternative
is the status quo: Headlamp on a static admin-user ServiceAccount token pasted into its login form.

**How to write it.** Read the file first and match its existing decision format exactly — numbering,
heading shape, and the "Decided \<date\> (\<who\>, \<context\>)" convention the neighbouring entries
use. Date it 2026-08-16 and attribute it to the operator at triage. Keep it to the ruling and its
rationale; do not design the implementation in the entry.

**Verify:** the entry reads as doctrine, names the four apiserver requirements, and does not read as
a plan.

---

## When the work is done

Commit in each repo you touched. Then close out the five cards — #616, #619, #583, #618, #576 — on
the Triage board (board `6a3d835931a74096c886fdc7`, Inbox list `6a3d8360cc19c8b9736ae580`), each with
a short comment naming what landed. Their rubric labels and the `Ansible` owner tag are already
written; leave both in place.

Note for #576: closing the card records the *ruling*. The implementation it authorises — apiserver
flags, RBAC, Headlamp SSO — is not done and is not tracked by that card. Raise a fresh card for it,
tagged `Ansible`, or say clearly in your report that it is untracked.
