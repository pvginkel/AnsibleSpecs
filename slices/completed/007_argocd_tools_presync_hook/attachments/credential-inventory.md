# The hook run's environment — the inventory slice 009's ExternalSecret materialises

What this settles: the **key names** the container reads, **where each value comes from**, the
GitHub PAT's **required permissions**, and the **`bao` commands** the operator runs. It is the
contract's authoritative half — slice 009 authors the ExternalSecret that fills
`argocd-hook-credentials` from it (phases.md A.4), and no single phase of either slice verifies
both halves end to end before A.5, so the names have to be settled once, here.

The container is credential- **and configuration-** agnostic (the 2026-08-14 credential-delivery and
configuration rulings): it reads plain environment variables, knows nothing about OpenBao, AppRoles
or ESO, and carries no estate facts of its own. Two carriers, and the split between them is the
whole design:

| Carrier | What rides it |
| --- | --- |
| The `argocd-hook-credentials` Secret, via the Job's `envFrom` | every value the run needs — the secrets ESO fetches from the leaves below, and the non-secret per-cluster facts its ExternalSecret carries as `template` literals |
| Synthesised inside the pod at run time | the kubeconfig, from the pod's own ServiceAccount |

One object in one GitOps-managed repo is therefore the whole of what a hook run receives.
`ArgoCDTools` commits none of it: a copy of `clusters.yaml` inside that repo would be production
cluster fact duplicated with no test able to bind the copies, since `ArgoCDTools`' CI has no
HelmCharts checkout.

## Secret-borne — the enumerated OpenBao leaves

The `eso` AppRole's existing grant (`ansible/inventories/prd/group_vars/openbao.yml:91-96`) already
reaches every row below except the last: `shared/prd/*` and `eso/prd/*` are globs, and a trailing
`*` in an OpenBao ACL matches across `/`. Two rows still need operator work, for two different
reasons — `eso/prd/argocd-hooks/git` is inside the grant but the **leaf does not exist yet**, and
`iac/tf-backend` exists but is **outside** the grant, which is this slice's one policy change.

| Env key | Leaf (`kv` mount) | Property | Why the run needs it |
| --- | --- | --- | --- |
| `GITHUB_TOKEN` | `eso/prd/argocd-hooks/git` | `token` | the deploy-repo clone, terraform-backend-git's pushes to the state repo, and D39's `github_repository_webhook` |
| `HOMELAB_CEPH_USER` | `shared/prd/ceph-csi` | `user_id` | homelab provider — rbd/cephfs resources |
| `HOMELAB_CEPH_KEY` | `shared/prd/ceph-csi` | `user_key` | as above |
| `HOMELAB_S3_ADMIN_ACCESS_KEY` | `shared/prd/ceph-rgw/s3` | `access_key_id` | homelab provider — the s3 resource |
| `HOMELAB_S3_ADMIN_SECRET_KEY` | `shared/prd/ceph-rgw/s3` | `secret_access_key` | as above |
| `HOMELAB_IAC_PROVISIONER_TOKEN` | `eso/prd/iac-provisioner/api/token` | `token` | homelab provider — `homelab_zfs_dataset` |
| `HOMELAB_BACKUP_SERVER_TOKEN` | `eso/prd/storage/prd/backup-server` | `management_token` | homelab provider — `homelab_backup_credential` |
| `TF_VAR_postgres_admin_password` | `eso/prd/postgres-pas/terraform-admin` | `password` | the `postgresql` provider's `terraform_admin` role |
| `SOPS_AGE_KEY` | `iac/tf-backend` | `age_secret_key` | terraform-backend-git decrypts state with it |

The set is derived from the estate's Terraform **capabilities** — the five providers
`/work/HelmCharts/_providers/providers.tf:19-35` declares — cross-checked against the credentials
`/work/HelmCharts/scripts/setup-env.sh:53-101` exports for a manual run. `random` needs none.

**`keycloak` is the one declared capability with no credential here.** `provider "keycloak" {}`
(`providers.tf:100`) is bare, nothing in the estate sets `KEYCLOAK_*` today, and no leaf exists —
the Keycloak Terraform capability itself arrives with A.4's Keycloak client and keycloak-tf
(Trello **#68**). Adding it later is one leaf plus one ExternalSecret line; recorded here so its
absence reads as deliberate rather than as an omission.

## Non-secret — `template` literals in the same Secret

The homelab provider's schema makes every attribute optional with an `HOMELAB_*` env fallback,
required only for the resources that use it (`/work/HomelabTerraformProvider/internal/provider/provider.go:126-198`),
so this half is ordinary configuration, not credentials — but it rides the same Secret, because the
container reads one environment and the ExternalSecret is the one place that composes it. Today the
deploy CLI injects it from `/work/HelmCharts/_providers/clusters.yaml:12-42`; in the hook path there
is no CLI, and these are the values that must still arrive. Each is copied from `clusters.yaml`'s
`prd` block into the ExternalSecret's `template` — that file stays the source of truth, and a change
to it is a change slice 009's object has to follow:

- Provider config, verbatim from `clusters.yaml`'s `prd.env`: `HOMELAB_CEPH_MON_HOST`,
  `HOMELAB_CEPH_POOL`, `HOMELAB_S3_ENDPOINT`, `HOMELAB_BACKUP_SERVER_URL`.
- Terraform inputs, from `clusters.yaml`'s `prd.tf_vars`, exported `TF_VAR_*` as the CLI does:
  `ceph_cluster_id`, `ceph_pool`, `csi_rbd_secret_namespace`, `csi_cephfs_secret_namespace`,
  `zfs_pools` (JSON-encoded — it is a map), `postgres_admin_host`.
- Release identity: `stage` and `namespace` are not Secret keys — they reach the run as Job
  **arguments**, and the entrypoint exports them as `TF_VAR_stage` and `TF_VAR_namespace` before
  `init`, so `var.stage`/`var.namespace` carry what Argo is syncing rather than the empty-string
  defaults `_providers/providers.tf:76-92` declares. A `-var-file` outranks a `TF_VAR_*`, so a
  deploy repo's own tfvars still win. **`TF_VAR_cluster` is deliberately not exported**:
  `var.cluster` is read by nothing under `configs/`, and the cluster is always `prd` — the
  ApplicationSet globs `configs/prd/` only (design.md:227-228), so nothing has to name it.
- The backend's non-secret settings: `GIT_USERNAME` (any non-empty string GitHub accepts beside a
  PAT; `x-access-token` is what `iac` uses) and `TF_BACKEND_HTTP_ENCRYPTION_PROVIDER=sops`.
- `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` — the age **public** key, a literal in the `template` like
  every other row here (the state-encryption-key ruling; public halves are not secrets and the leaf
  is left alone). The invariant is that it is the public half of the same keypair `SOPS_AGE_KEY`
  holds, or state the hook writes is undecryptable by `iac` and vice versa (D32).

## The GitHub PAT

**Minted 2026-08-15 as a classic PAT with `repo` on every private repository the operator owns.**
This section originally specified a fine-grained token, and the mint went the other way for a
reason that is worth keeping: **a fine-grained PAT is scoped to a single resource owner**, and the
estate's repositories do not all sit under one, so the intended scoping is not expressible in one
token. D41 carries the amendment and the blast-radius consequence; **O4** holds the GitHub App
option that would restore it.

What that means for anything reading this file: **the token is read-write on the state repo and
every deploy repo alike**, and it needs no per-repo selection revisited as Phase B adds deploy
repos — `repo` already covers them on creation. Nothing else here changes; the leaf, the key name
and the ExternalSecret are unaffected.

The scoping this section asked for, kept as the statement of intent behind O4:

- `pvginkel/TerraformState` — **read-write** on contents. terraform-backend-git pushes state commits
  and per-state lock branches through it.
- Every deploy repo — **read-only** on contents. The run's only clone (D14/D41).
- Every deploy repo — **`admin:repo_hook`**, i.e. read-write on webhooks. D39 makes each deploy
  repo's webhook a Terraform resource created on the first PreSync apply. Granted separately under
  a fine-grained token; under the classic `repo` scope actually minted it is not, so **D39's
  `github_repository_webhook` is confirmed on the first PreSync apply** rather than assumed.

## The operator's keystrokes

**Status:** both OpenBao writes are done (2026-08-15, Trello #621). The age **public** key handoff
below is still owed — it is an input to slice 009, not to 007.

The git token — a new leaf under `eso/prd/`, which the `eso` grant's `eso/prd/*` glob already
covers, so it needed no policy change. **Written:** `kv/eso/prd/argocd-hooks/git` exists,
version 1, 2026-08-15T13:56Z.

```
cd /work/Ansible && cexec iac bao kv put -mount=kv eso/prd/argocd-hooks/git token=<the PAT>
```

The state encryption key needs no new value — it is `iac`'s existing keypair at
`kv/iac/tf-backend` (the ruling; `support/iac-agent/etc/iac/secrets.example.yaml:164-165` is where
`iac` reads it). What it needs is for the `eso` AppRole to be allowed to read that one leaf, which
is the Ansible change this slice makes, applied by:

```
cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook playbooks/site-openbao.yml
```

**Converged:** the live prd `eso` policy carries `kv/data/iac/tf-backend` and
`kv/metadata/iac/tf-backend` read. A re-run reports no change by design — the role PUTs a policy
only when the rendered text differs from what is live (`roles/openbao/tasks/approle.yml:211`).

The recipient — the public half — needs no OpenBao work at all: it is a `template` literal, exactly
as `iac` carries it in srviac's `/etc/iac/secrets.yaml` rather than in a leaf
(`support/iac-agent/etc/iac/secrets.example.yaml:126-133` shows the shape, with the real `age1…`
string standing where the example's placeholder does). What the operator hands over is that one
non-secret string, for slice 009 to place in the ExternalSecret's `template`; it can equally be
derived from the private half with `age-keygen -y`, which is a read of the secret and therefore also
the operator's. No `kv put` or `kv patch` on `iac/tf-backend` is involved either way — the leaf is
left exactly as it is.

Nothing else is minted. **No AppRole is created for the hook** (the credential-delivery ruling) —
the hook never authenticates to OpenBao.
