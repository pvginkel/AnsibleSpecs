# The hook's credential map

What the Argo CD PreSync hook needs at runtime, where each item lives in OpenBao, who writes it
and who reads it. Three phases of this slice and one of slice 009 all rest on this table, so it
is written once here rather than derived three times.

Nothing here is a value. Every value is the operator's keystroke (R3).

## Two surfaces, and why they are two

**`kv/eso/prd/argocd-hooks/credentials`** — the four literals ESO materialises into the
`argocd-hook-credentials` Secret in the `argocd-hooks` namespace. It sits under `eso/prd/`
because ESO's AppRole policy globs `eso/prd/*` (`ansible/inventories/prd/group_vars/openbao.yml:96`);
anywhere else and slice 009's ExternalSecret cannot read it without widening that policy.

**`kv/argocd-hooks/…`** — the hook's own namespace, read by the hook's dedicated AppRole after it
logs in. The prefix glob is what makes a future per-app credential a `bao kv put` with no policy
change, the rationale `openbao_iac_agent_kv_paths` already carries at
`ansible/inventories/prd/group_vars/openbao.yml:106-117`.

The split is the bootstrap boundary: the first surface is what the hook needs *before* it can talk
to OpenBao, the second is everything it fetches once it can.

## The bootstrap surface — `kv/eso/prd/argocd-hooks/credentials`

Four keys, the same irreducible-literal set `iac-impl` has
(`support/iac-agent/etc/iac/secrets.example.yaml`, "Irreducible-literal set"), and no more. They
reach the container as environment variables of the same name via `envFrom: secretRef` — the hook
Job supplies no `env:` at all (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:45-47`).

| Key | What it is | Why it cannot be a `!bao` ref |
| --- | --- | --- |
| `OPENBAO_URL` | The OpenBao endpoint, `https://secrets.home/` | It is how you reach OpenBao |
| `OPENBAO_ROLE_ID` | The dedicated AppRole's role_id | Gates the login |
| `OPENBAO_SECRET_ID` | The dedicated AppRole's secret_id | Gates the login |
| `GIT_API_TOKEN` | The scoped GitHub PAT | The clone happens before any resolution |

`GIT_USERNAME` is **not** in the Secret: it is `x-access-token`, a fixed literal any non-empty
string GitHub accepts alongside a PAT, and belongs in the image's baseline manifest.

`role_id` and `secret_id` come out of the Ansible run that creates the AppRole — the openbao role
stages both per consumer for operator capture on a rotation run
(`ansible/roles/openbao/tasks/approle.yml:408-455`). The operator captures them there and writes
them here.

## The runtime surface — `kv/argocd-hooks/…`

Resolved by the entrypoint after the AppRole login, out of the baseline manifest baked into the
image.

| Leaf | Keys | Becomes |
| --- | --- | --- |
| `kv/argocd-hooks/tf-backend` | `age_recipient`, `age_secret_key` | `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS`, `SOPS_AGE_KEY` |

**The age keypair must be the same one `iac` uses today** — the value at
`kv/iac/tf-backend#age_secret_key` and the recipient `iac`'s `secrets.yaml` carries as a literal.
This is not a preference: `iac` and the hook write into the same `pvginkel/TerraformState`
repository (D32), and phases.md B.4 moves existing per-app state into the hook's key scheme with
`terraform state mv`. A second keypair makes state written by one side undecryptable by the other.

It is nonetheless **minted as its own leaf in the hook's namespace** rather than granted out of
`kv/iac/` — R3 says the state encryption key is minted here, and the ruled policy shape keeps the
hook out of srviac's namespace. The named consequence: the value exists in two places, so an age
rotation touches both leaves, and missing one silently breaks decryption on the side that was
missed. Rotation of a tfstate age key already means re-encrypting every state, so this is a rare
and deliberate operation, not a routine one.

The recipient (the age *public* key) is a `!bao` ref here even though `iac` keeps it as a literal.
`iac`'s `secrets.yaml` is hand-edited on srviac and never committed; the hook's baseline manifest
is committed repo content. **Anything not safe in git is a ref.**

## Leaves outside the hook's namespace

The homelab provider's credentials, which app Terraform needs and which live in shared space. They
are enumerated in the hook's policy, exactly as `openbao_iac_agent_kv_paths:118-124` enumerates
them for `iac`. The working set, from the same provider's entries in
`support/iac-agent/etc/iac/secrets.example.yaml`:

| Leaf | Becomes |
| --- | --- |
| `kv/shared/prd/ceph-csi` | `HOMELAB_CEPH_USER`, `HOMELAB_CEPH_KEY` |
| `kv/shared/prd/ceph-rgw/s3` | `HOMELAB_S3_ADMIN_ACCESS_KEY`, `HOMELAB_S3_ADMIN_SECRET_KEY` |
| `kv/eso/prd/iac-provisioner/api/token` | `HOMELAB_IAC_PROVISIONER_TOKEN` |

The binding rule, not the list, is what matters: **the policy grants exactly what the baseline
manifest resolves.** A leaf the manifest stops referencing leaves the policy; one it adds outside
`argocd-hooks/` joins the enumeration.

Note the two notations differ. A `!bao` ref names the mount: `kv/shared/prd/ceph-csi#user_id`. A
policy path list entry is relative to the mount: `shared/prd/ceph-csi`, which the policy template
expands to both `kv/data/…` and `kv/metadata/…`
(`ansible/roles/openbao/templates/policy.hcl.j2`).

## What is a literal in the baseline manifest, not a secret at all

`TF_BACKEND_HTTP_ENCRYPTION_PROVIDER=sops`, `GIT_USERNAME=x-access-token`, and any non-secret URL —
the estate's standing "URLs never enter Vault" rule.

**What must *not* be copied across from `iac`'s manifest:** `KUBE_CONFIG_PATH` / `KUBECONFIG`.
They name a kubeconfig file materialised on srviac. In the hook pod the identity is the Job's own
ServiceAccount (design.md, flow step 5), and a pointer to a file that does not exist is a failure
mode that only shows up on the first app whose Terraform touches Kubernetes.

## The GitHub token

What the hook does with it: clones the deploy repo at the synced SHA (read), lets
terraform-backend-git pull and push `pvginkel/TerraformState` (read-write), and lets the app's own
Terraform create that deploy repo's webhook (D39).

So the requirement is: **`pvginkel/TerraformState` read-write, the deploy repos read, and webhook
administration** (`admin:repo_hook` on a classic PAT, "Webhooks: Read and write" on a fine-grained
one).

**A single GitHub token cannot express "read-write here, read-only there."** A classic PAT's
`repo` scope is account-wide; a fine-grained PAT carries one permission set across every repository
it selects. The requirement's read-only half is therefore not enforceable by the token — it is
enforced by the hook never writing to a deploy repo's contents.

The recommendation is one fine-grained PAT selecting `TerraformState` plus the deploy repos, with
Contents read-write and Webhooks read-write, and the write-on-deploy-repos over-grant accepted and
named. The alternative — two tokens, one per role — would add a second key to
`argocd-hook-credentials` and a second env var to the entrypoint, which the ruling on that Secret's
contents forecloses.

## What slice 009 consumes from this

The Secret's name (`argocd-hook-credentials`), its four key names, and the leaf path
`kv/eso/prd/argocd-hooks/credentials` its ExternalSecret reads. Nothing else here is 009's.
