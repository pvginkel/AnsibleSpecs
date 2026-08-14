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

The credentials the deploy providers read, which live in shared space and so are enumerated in the
hook's policy leaf by leaf. **The authority for what app Terraform needs is the provider set it
runs against** — `/work/HelmCharts/_providers/providers.tf` and the script that credentials it,
`/work/HelmCharts/scripts/setup-env.sh` — not `iac`'s hand-edited `secrets.example.yaml`, which
states what one container happens to carry. Derived from those two, the set is the same five
`openbao_iac_agent_kv_paths` grants (`ansible/inventories/prd/group_vars/openbao.yml:118-124`),
which is unsurprising: the hook runs the same providers against the same estate.

| Leaf | Becomes | Read by | In the image baseline |
| --- | --- | --- | --- |
| `kv/shared/prd/ceph-csi` | `HOMELAB_CEPH_USER`, `HOMELAB_CEPH_KEY` (`setup-env.sh:54-55`) | `provider "homelab"` | yes |
| `kv/shared/prd/ceph-rgw/s3` | `HOMELAB_S3_ADMIN_ACCESS_KEY`, `HOMELAB_S3_ADMIN_SECRET_KEY` (`:56-57`) | `provider "homelab"` | yes |
| `kv/eso/prd/iac-provisioner/api/token` | `HOMELAB_IAC_PROVISIONER_TOKEN` (`:58`) | `provider "homelab"` | yes |
| `kv/eso/prd/postgres-pas/terraform-admin` | `TF_VAR_postgres_admin_password` (`:81-85`) | `provider "postgresql"` (`providers.tf:108-115`) | no — per-app overlay |
| `kv/eso/prd/storage/prd/backup-server` | `HOMELAB_BACKUP_SERVER_TOKEN` (`:91-99`) | `homelab_backup_credential` | no — per-app overlay |

**The binding rule, not the list, is what matters (ruled): the policy grants a superset of what the
baseline manifest resolves, and a deploy repo's overlay closes the gap.** The last two leaves are
granted but not baseline-resolved — an app that provisions a database or a backup credential
declares them in its own `config/<stage>/secrets.yaml`, and needs no live-OpenBao keystroke to do
it. That split is deliberate: D41's blast radius says no hook run carries a credential it does not
need, while the policy's shape says no `site-openbao.yml` re-run when the first postgres-using app
migrates. A leaf outside `argocd-hooks/` that no overlay and no baseline can reference has no
business in the policy either; one that any of them adds joins the enumeration.

Impact today is nil either way — only `configs/prd/postgres-pas` uses either provider, and the
pilot (B.1 KubeCoder) uses neither.

Note the two notations differ. A `!bao` ref names the mount: `kv/shared/prd/ceph-csi#user_id`. A
policy path list entry is relative to the mount: `shared/prd/ceph-csi`, which the policy template
expands to both `kv/data/…` and `kv/metadata/…`
(`ansible/roles/openbao/templates/policy.hcl.j2`).

## What is a literal in the baseline manifest, not a secret at all

`TF_BACKEND_HTTP_ENCRYPTION_PROVIDER=sops`, `GIT_USERNAME=x-access-token`, and any non-secret URL —
the estate's standing "URLs never enter Vault" rule.

## The one pair that is neither — `KUBE_CONFIG_PATH` / `KUBECONFIG`

`iac` declares both in its manifest as literals (`support/iac-agent/etc/iac/secrets.example.yaml:122-125`),
pointing at a kubeconfig materialised on srviac. **Neither the literal nor the file survives the
move**, but the two variable names do: the entrypoint synthesises a kubeconfig from the pod's own
ServiceAccount at run time and exports both at it before `terraform init` (ruled). So they are not
manifest entries at all — nothing in OpenBao backs them, and nothing declares them.

Getting this wrong is invisible until it is expensive. The `kubernetes` provider takes no
credentials in code — `/work/HelmCharts/_providers/providers.tf:98` is a bare
`provider "kubernetes" {}`, and its header (`:13-16`) states that it follows `KUBE_CONFIG_PATH`.
Unset, the first migrated app's hook fails to configure the provider on every sync; set to a path
this image never materialises, the same. And a proof run from this pod resolves it through the
ambient `~/.kube/config` and shows nothing either way.

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
