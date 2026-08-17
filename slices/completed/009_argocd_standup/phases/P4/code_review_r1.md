# P4 code review — round 1

Commit under review: `008126db17d7` on `phase/009-P4`, diff
`20a32660d48f..HEAD` in `/work/ArgoCDDeploy` (4 files, +446/-19).
Gate: `kc project test` green on this commit (`phases/P4/gate_r1.log`) — taken as an input.

## Readiness

**Ready to merge.** The phase delivers what its section asks for and the parts that could only fail
in production check out against the live estate: every one of the nine leaf paths and properties is
corroborated outside the diff (`shared/prd/ceph-csi`, `shared/prd/ceph-rgw/s3`,
`eso/prd/iac-provisioner/api/token`, `eso/prd/storage/prd/backup-server`,
`eso/prd/postgres-pas/terraform-admin` all appear as live or committed consumers; `iac/tf-backend`
is inside the `eso` AppRole grant at `ansible/inventories/prd/group_vars/openbao.yml:107`), the
`openbao-prd` ClusterSecretStore carries no `conditions` block so an ExternalSecret in a brand-new
namespace resolves (`kubectl get clustersecretstore openbao-prd -o yaml`, 2026-08-17), the age
recipient committed at `config/prd/values.yaml:263` is **byte-identical to the recipient every
tfstate in `pvginkel/TerraformState` is already encrypted to**
(`helm-charts/dev/_ci/prd/infra.tfstate:148`), so D32's invariant holds rather than being asserted,
and the 13 non-secret literals are verbatim `_providers/clusters.yaml`'s `prd` block. The three
names the library chart hard-codes agree with `_tf-presync-hook.tpl:27,39,51`. The ClusterRole's
three kinds are exactly what the estate's Terraform manages through the kubernetes provider
(`grep -o 'kubernetes_[a-z_0-9]*' --include=*.tf /work/HelmCharts` → `persistent_volume_v1` ×6,
`secret_v1` ×5, `namespace_v1` ×2 and nothing else), and the hook's own API surface needs nothing
more than the PV collection list plus a merge-patch (`presync/reattach.py:45,48`,
`presync/kube.py:40-53`); the run's env reads are closed too — `cli.py:31-32` plus
`backend.py:37-41` and nothing else calls `require()`. Both findings below are **advisory**: one is
a drift detector that only half-detects, the other a latent rotation hazard in a design the plan
deliberately settled. Neither is a reason to hold the phase.

## Findings

### F1 — the gate binds the hook's per-cluster literals to `clusters.yaml` by value but not by key set · Major · advisory · anchor: none · confidence: high

`tests/render-chart.py:883-897` reads `_providers/clusters.yaml`'s `prd` block and compares values,
but it iterates the **hard-coded tuples** `HOOK_ENV_LITERALS` (`:75-80`) and `HOOK_TF_VARS`
(`:81-88`), never `prd["env"]` / `prd["tf_vars"]`. A value that changes in `clusters.yaml` is
caught; a key **added** to it is not.

Witnessed, not reasoned. Adding `HOMELAB_DRIFT_PROBE: probe-value` to `clusters.yaml`'s `prd.env`
and running `cexec iac tests/render-chart.py` printed
`ok: 66 objects render into argocd-prd and argocd-hooks`, exit 0. Changing
`HOMELAB_CEPH_POOL: k8s` to `k8s-drift` in the same block went red
(`FAIL: HOMELAB_CEPH_POOL is 'k8s', not clusters.yaml's 'k8s-drift'`). `clusters.yaml` was restored
and `git status` in `/work/HelmCharts` is clean.

This is the exact direction that matters. A per-cluster provider setting is added to that file
routinely — the `prd` block carries `HOMELAB_BACKUP_SERVER_URL` and the `dev` block does not — and
the hook path has no CLI to inject it. The consequence the diff's own comment names lands
unannounced: "`envFrom` is all-or-nothing and a missing key surfaces at `terraform apply`, deep
inside a sync" (`chart/templates/hook-namespace.yaml:48-51`).

The claim the check does not carry: `tests/render-chart.py:66-69` — "the two are bound here rather
than restated … a change to that file is a change this chart's object has to follow" — and the
phase's done-record, `plan.md:589-590`, "the non-secret half as literals bound by the gate to
`_providers/clusters.yaml`'s `prd` block". A key addition *is* a change this chart's object has to
follow, and the binding does not see it.

Advisory, not blocking: nothing is missing today (all 13 keys present and byte-equal), no
acceptance criterion names drift detection, and V08 is satisfied as written. The exposure is on the
next change to a file in another repo.

### F2 — the age recipient is committed as a literal while its private half is fetched, and the same leaf already carries the public half · Major · advisory · anchor: none · confidence: high

`config/prd/values.yaml:234-236` fetches `SOPS_AGE_KEY` from `iac/tf-backend#age_secret_key`;
`:259-263` commits `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` as a literal, on the premise — 007's
`credential-inventory.md` §"Non-secret", `docs/runbooks/iac-agent.md:201-207` — that the public
half lives only in srviac's `/etc/iac/secrets.yaml` and "every new consumer takes it as a plaintext
literal".

That premise is contradicted inside this estate. `kv/iac/tf-backend` carries the public half as a
field of the very leaf this ExternalSecret already fetches, and the estate's other consumer of the
same daemon resolves it from there rather than pasting it:
`/work/Ansible/scripts/tf-backend.sh:10-12` documents
`age_public_key — age public key (encrypts state) -> TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS`, and
`:46` reads exactly that field. The `eso` AppRole's grant on that leaf
(`group_vars/openbao.yml:107`) is already what carries `SOPS_AGE_KEY`, so no policy or leaf work
stands between the two forms.

The consequence is a rotation one, and the runbook flags rotation as unexercised
(`docs/runbooks/iac-agent.md:219`, "Rotation is not a paste … this path has not been exercised
either"). Rotating the keypair updates one leaf and every `!bao` consumer of it at once, while this
recipient stays whatever was committed: the hook then encrypts state to the *old* recipient while
holding the *new* identity, which is D32's stated failure mode — and the gate cannot see it,
because `tests/render-chart.py:106,908-911` can only check that the string is shaped like an age
public key, never that it pairs with the private half beside it. The runbook's own answer to that
gap is a manual match-check (`:209-215`), i.e. a procedure rather than a property.

Advisory: the value committed is verified correct today (identical to the recipient in the live
state repo), the literal form is what the plan settled and N2 records, and no criterion is unmet.
This is the operator's call on a design already ruled, not fix work.

## Checked and clear

Recorded so a later round does not re-derive them:

- **AppProject wiring both ways.** `argocd-hooks` is a permitted destination
  (`PERMITTED_NAMESPACES`, `tests/render-chart.py:140`) and the new cluster-scoped `ClusterRole`/
  `ClusterRoleBinding` are covered by the render-driven `clusterResourceWhitelist` assertion
  (`:405-421`), which iterates every namespace-less doc — so P4's objects needed no P3 change and
  did not silently skip one.
- **The exact-key assertion is not vacuous.** `secret["keys"] == HOOK_ENVIRONMENT` (`:868-872`)
  compares the 22-key set; `external_secrets()` (`:221`) correctly takes the template's keys rather
  than the fetch's, which is what ESO does with a `data` template.
- **`check_release_name`'s new derivation is equivalent, not weaker.** `argocd-cmd-params-cm`'s
  namespace is `.Release.Namespace`, the same value `chart/templates/namespace.yaml:11` names, and
  `check_namespace_manifest` still pins the chart's own Namespace to `argocd-prd` independently.
- **The `Prune=false` / `sync-wave: "-1"` pair on `argocd-hooks`** matches Argo's own namespace and
  is asserted (`:836-845`).
- **RBAC completeness.** No `persistentvolumeclaims` grant is owed — the reattach filters PVs by
  `spec.claimRef.namespace` and never reads a claim (`reattach.py:34-39`).
- **Cluster-wide `secrets`/`namespaces` blast radius** is already recorded by the executor as
  close-out **S6**, with the per-app-namespace RoleBinding narrowing named; not re-litigated here.
- **Comment density** is the repo's established style (each block carries a decision id or a cited
  `file:line`), and none of it narrates change history. No prose finding.
