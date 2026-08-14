# The hook run's environment — the inventory slice 009's ExternalSecret materialises

What this settles: the **key names** the container reads, **where each value comes from**, the
GitHub PAT's **required permissions**, and the **`bao` commands** the operator runs. It is the
contract's authoritative half — slice 009 authors the ExternalSecret that fills
`argocd-hook-credentials` from it (phases.md A.4), and no single phase of either slice verifies
both halves end to end before A.5, so the names have to be settled once, here.

The container is credential-provider-agnostic (the 2026-08-14 credential-delivery ruling): it reads
plain environment variables and knows nothing about OpenBao, AppRoles or ESO. Three carriers,
and the split between them is the whole design:

| Carrier | What rides it |
| --- | --- |
| The `argocd-hook-credentials` Secret, via the Job's `envFrom` | every value that is a secret |
| Configuration committed in `ArgoCDTools` | the prd cluster's non-secret provider configuration |
| Synthesised inside the pod at run time | the kubeconfig, from the pod's own ServiceAccount |

## Secret-borne — the enumerated OpenBao leaves

The `eso` AppRole's existing grant (`ansible/inventories/prd/group_vars/openbao.yml:91-96`) already
covers every row below except the last two; those are this slice's OpenBao-side work.

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

## Non-secret, committed in `ArgoCDTools`

The homelab provider's schema makes every attribute optional with an `HOMELAB_*` env fallback,
required only for the resources that use it (`/work/HomelabTerraformProvider/internal/provider/provider.go:126-198`),
so this half is ordinary configuration, not credentials. Today the deploy CLI injects it from
`/work/HelmCharts/_providers/clusters.yaml:12-42`; in the hook path there is no CLI, and these are
the values that must still arrive:

- Provider config, verbatim from `clusters.yaml`'s `prd.env`: `HOMELAB_CEPH_MON_HOST`,
  `HOMELAB_CEPH_POOL`, `HOMELAB_S3_ENDPOINT`, `HOMELAB_BACKUP_SERVER_URL`.
- Terraform inputs, from `clusters.yaml`'s `prd.tf_vars`, exported `TF_VAR_*` as the CLI does:
  `ceph_cluster_id`, `ceph_pool`, `csi_rbd_secret_namespace`, `csi_cephfs_secret_namespace`,
  `zfs_pools` (JSON-encoded — it is a map), `postgres_admin_host`.
- Release identity the Job's arguments already carry: `cluster` (always `prd` — the ApplicationSet
  globs `configs/prd/` only, design.md:220-221), `stage` and `namespace`.
- The backend's non-secret settings: `GIT_USERNAME` (any non-empty string GitHub accepts beside a
  PAT; `x-access-token` is what `iac` uses) and `TF_BACKEND_HTTP_ENCRYPTION_PROVIDER=sops`.
- `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` — the age **public** key. Public halves are not secrets, so
  either carrier works; the invariant is that it is the public half of the same keypair
  `SOPS_AGE_KEY` holds, or state the hook writes is undecryptable by `iac` and vice versa (D32).

## The GitHub PAT

Stated as effective permissions, because the mint is the operator's:

- `pvginkel/TerraformState` — **read-write** on contents. terraform-backend-git pushes state commits
  and per-state lock branches through it.
- Every deploy repo — **read-only** on contents. The run's only clone (D14/D41).
- Every deploy repo — **`admin:repo_hook`**, i.e. read-write on webhooks. D39 makes each deploy
  repo's webhook a Terraform resource created on the first PreSync apply.

Only a fine-grained PAT expresses this — a classic `repo` scope is read-write on everything it
touches, which would give a deploy-repo branch write access to every deploy repo. Operational
consequence to expect: the deploy repos do not all exist yet (Phase B creates them one at a time),
so the token's repository selection is revisited as each is added.

## The operator's keystrokes

The git token — a new leaf under `eso/prd/`, which the `eso` grant's `eso/prd/*` glob already
covers, so it needs no policy change:

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

If the recipient (public half) is to reach the Secret through ESO rather than through committed
configuration, the leaf needs to carry it — `kv patch`, so the private half is left alone:

```
cd /work/Ansible && cexec iac bao kv patch -mount=kv iac/tf-backend age_public_key=<age1…>
```

Nothing else is minted. **No AppRole is created for the hook** (the credential-delivery ruling) —
the hook never authenticates to OpenBao.
