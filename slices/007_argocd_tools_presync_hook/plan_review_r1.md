# Plan review — 007 ArgoCDTools and the PreSync hook image (round 1)

Reviewed: `slice.md`, `plan.md`, `verification.json`, `attachments/credential-map.md`, the
`argo-cd/` document set, and the code every load-bearing ruling cites.

**AC completeness is clean.** `verification.json`'s eighteen criteria cover slice.md's three
numbered requirements 1:1 in the operator's wording — R1 across V01–V09, R2 across V10–V12, R3
across V13–V17, with V18 as a blast-radius guard. Nothing is dropped, softened or substituted, and
no criterion asserts a prose universal.

**Citations largely hold.** I opened every source the rulings and phases lean on. `tf.py:59-68`
and `:139-151`, `helmops.py:117-153`, `iac-impl:108-134`/`:159-179`/`:242-266`/`:309-350`/`:322`/
`:372-383`, `Dockerfile:100-115`/`:129-130`/`:69-83`, `terraform.rc:29`+`:121`,
`_tf-presync-hook.tpl:41-44`/`:45-47`, `render-consumer.sh:62-68`/`:104-106`,
`consumer/values.yaml:37-40`, `openbao.yml:96`/`:106-117`/`:118-124`,
`defaults/main.yml:107-117`, `approle.yml:152-180`/`:184-192`/`:231-296`/`:408-455`,
`.kubecoder/config.yaml:16` — all check out. Two independent derivations confirmed plan claims:
`homelab-shared` 0.1.0 has no consumer (`dist/` holds one tarball, the gate fixture resolves
`>=0.1.0` from a scratch `file://` copy), and the ruled state key's missing cluster axis is safe
because D2 confines Argo to the prd cluster.

Findings below: operator-decidable first, then blocking, then advisory.

---

## F1 — The fourth Job argument contradicts the authoritative `argo-cd/` doc set, and the plan carries no path to propagate it to slice 009

**Problem.** The 2026-08-14 ruling adds `hook.namespace` as a fourth `required`-guarded argument.
The authoritative model states **three**, in four places, and slice.md quotes two of them as *"the
contract this entrypoint must satisfy"*. Nothing in the plan updates those documents, and the doc
phase does not cover them.

**Evidence.**

- `argo-cd/design.md:321` (flow step 1): *"handing it `hook.repo`, `hook.revision` (the exact
  synced SHA), `hook.stage` via chart values."*
- `argo-cd/design.md:361-363` — the Job skeleton's args block, three entries.
- `argo-cd/design.md:372`: *"The **three arguments** are `required`-guarded, so a chart that
  forgets one fails to render rather than passing an empty argument."*
- `argo-cd/design.md:190-199` — the ApplicationSet `parameters:` block supplies exactly
  `hook.repo`, `hook.revision`, `hook.stage`.
- `hook.namespace` appears nowhere in `phases.md`, `design.md` or `decisions.md`. D29 and D33
  describe the reattach's namespace as something the hook *finds*, not something it is handed.
- The most recent `argo-cd/` commit — `a75dda6`, 2026-08-14 09:03, slice 006's close-out — is the
  commit that *introduced* the "three arguments" sentence and rewrote the args block, keeping
  three. The three-arg statement is hours fresher than the ruling that contradicts it.
- `docs/slice-doc-plan.md` enumerates the doc phase's five surfaces: `AnsibleSpecs/decisions.md`,
  `docs/runbooks/`, `AnsibleSpecs/README.md`, role/module docs, `CLAUDE.md`. The `argo-cd/`
  document set is not among them.

**Impact.** Slice 009 (phases.md A.4) builds the ApplicationSet, and its planner reads phases.md
and design.md — not this plan.md. Both say three parameters. `homelab-shared` 0.2.0 ships a Job
template that `required`-guards a namespace the ApplicationSet is never told to supply, so **every
migrated app fails to render** at 009's standup — a render-time failure by design, but one that
surfaces in the wrong slice with no clue pointing back here. The plan's only mitigation is a "Not
in scope" line inside its own file (*"The ApplicationSet that supplies `hook.namespace` — slice
009 (A.4)"*), which is invisible to the session that needs it.

**Operator decision.** Whether folding the ruling into `argo-cd/design.md` — flow step 1, the Job
skeleton, the "three arguments" sentence, the ApplicationSet parameters, and a note on D29/D33
that the reattach's namespace filter is passed rather than derived — belongs in this slice, or
whether the propagation risk is accepted and handled when 009 is planned.

---

## F2 — P1's "five places" enumeration omits the two loops that produce what the cited staging loop consumes

**Problem.** P1's central claim is that *"the role enumerates its consumers by name in five places,
and a new one that joins only some of them half-exists."* The role actually enumerates consumers by
name in **seven tasks**. The two P1 omits are exactly the ones the staging loops it *does* cite
depend on.

**Evidence.** `ansible/roles/openbao/tasks/approle.yml`, read in full:

| Task | Lines | Cited by P1? |
| --- | --- | --- |
| Per-consumer policy renders | 148-182 | yes (`:152-180`) |
| Consolidated policy-text dict | 184-192 | yes (`:184-192`) |
| Read AppRoles loop | 230-256 | yes (within `:231-296`) |
| Write AppRoles loop | 273-299 | yes (within `:231-296`) |
| **Read each AppRole's role_id** | **311-317** | **no** |
| **Mint a fresh secret-id for each AppRole** | **339-345** | **no** |
| Rotation-run staging loops | 428-435, 446-451 | yes (within `:408-455`) |

The staging tasks P1 cites read back from the two loops it omits:

```
content: >-
  {{ (_openbao_role_ids.results
      | selectattr('item', 'equalto', approle)
      | first).json.data.role_id }}
```

(`:423-426`, and the secret_id twin at `:441-444`.) `_openbao_role_ids` is registered at `:310` by
the loop at `:311-317`; `_openbao_secret_ids` at `:338` by the loop at `:339-345`.

**Failure scenario.** An executor works P1's list literally: adds `argocd-hook` to the render, the
dict, the read loop, the write loop and both staging loops, and not to `:311-317`/`:339-345`. The
operator then runs `playbooks/site-openbao.yml -e openbao_rotate_secret_ids=true` — the run
`attachments/credential-map.md:41-44` names as how role_id and secret_id are captured. At "Stage
each operator-facing AppRole role_id", `selectattr(...) | first` runs over an empty sequence and
the play errors out. This is precisely the "half-exists" failure P1 was written to prevent, and it
lands on an operator keystroke against the live OpenBao cluster.

**Related, same phase.** The Write AppRoles loop templates `openbao_<consumer>_token_ttl` and
`openbao_<consumer>_token_max_ttl` (`:266-267`). P1 names only the new `openbao_*_kv_paths`
variable in `defaults/main.yml:107-117`; the sibling TTL defaults at `defaults/main.yml:88-105`
are not mentioned, and an undefined one fails the same play.

---

## F3 — The `kubernetes` Terraform provider is left with no stated credential path, and the ruled proof bar cannot detect it

**Problem.** `attachments/credential-map.md:99-102` rules `KUBE_CONFIG_PATH`/`KUBECONFIG` out of
the baseline manifest, on the grounds that *"In the hook pod the identity is the Job's own
ServiceAccount (design.md, flow step 5)"*. Design.md's flow step 5 and D29 say that about **the PV
reattach**, which this slice implements itself. Nothing establishes that the `kubernetes`
*Terraform provider* picks up in-cluster ServiceAccount credentials from a bare `provider
"kubernetes" {}` block, and this estate's own code documents the opposite behaviour.

**Evidence.**

- `/work/HelmCharts/_providers/providers.tf:98` is `provider "kubernetes" {}` — no attributes. Its
  header comment (`:13-16`) states: *"Credentials are environment variables, full stop: the homelab
  provider reads every config attribute from its `HOMELAB_*` env fallback, and **the kubernetes
  provider follows `KUBE_CONFIG_PATH`**."*
- `/work/HelmCharts/scripts/setup-env.sh:103-107`: *"the kubernetes provider follows
  `KUBE_CONFIG_PATH` and the CLI falls back to `~/.kube/config` — so without this a prd deploy
  silently hits whatever that points at."*
- The pilot's Terraform is kubernetes-provider work from its first line:
  `/work/HelmCharts/configs/prd/kubecoder/_shared/infrastructure.tf` opens with
  `module "namespace"` and follows with `module "zfs"` (a `static-zfs-pv` PV/PVC pair).

**Failure scenario.** The first migrated app's PreSync hook reaches `terraform apply` in-cluster
with no `KUBE_CONFIG_PATH`, no `KUBE_*` env, and no in-cluster block, and the kubernetes provider
fails to configure — a non-zero exit that correctly gates the sync, on every sync, until someone
diagnoses it.

**Why the slice's own proof cannot catch it.** The ruled proof bar runs the entrypoint end to end
*from this pod* against a throwaway deploy repo (plan.md rulings; V04/V06). This pod has
`~/.kube/config` mounted, so the run resolves the provider through the kubeconfig fallback and
passes — proving nothing about the path that matters. P4 makes exactly this distinction for the PV
reattach (*"this must not be written to require a kubeconfig — but the ruled proof for it is a run
from this pod ... It has to work under both"*) and the plan makes it nowhere for Terraform's own
kubernetes provider. The attachment names this failure class for the stale kubeconfig — *"a failure
mode that only shows up on the first app whose Terraform touches Kubernetes"* — and then leaves the
replacement mechanism unstated.

---

## F4 (advisory) — The "leaves outside the hook's namespace" list is derived from srviac's file, not from app Terraform's contract, and drops two leaves the plan's own model grants

`attachments/credential-map.md:72-83` builds the list *"from the same provider's entries in
`support/iac-agent/etc/iac/secrets.example.yaml`"* and arrives at three leaves. That file is
srviac's hand-edited container manifest, not a statement of what app Terraform needs. The
authoritative surface is `_providers/providers.tf` plus `scripts/setup-env.sh`, and
`openbao_iac_agent_kv_paths` — the variable the plan cites as *"the closest working model"* — grants
two leaves the attachment's table omits:

- `eso/prd/postgres-pas/terraform-admin` (`openbao.yml:123`) → `TF_VAR_postgres_admin_password`
  (`setup-env.sh:82-84`), consumed by `provider "postgresql"` at `providers.tf:108-115`.
- `eso/prd/storage/prd/backup-server` (`openbao.yml:124`) → `HOMELAB_BACKUP_SERVER_TOKEN`
  (`setup-env.sh:96-98`), consumed by `homelab_backup_credential`.

Impact is deferred, which is why this is advisory: only `configs/prd/postgres-pas` uses either
provider today, and the pilot (B.1 KubeCoder) needs neither. The attachment's binding rule (*"the
policy grants exactly what the baseline manifest resolves"*) also gives a documented way to extend.
But V08 asserts an *estate-wide* baseline, and as derived it is not one.

---

## F5 (advisory) — V10 has no deploy-owed escape while its sibling V11 does

V10 requires *"a build has actually run and produced an image."* The ordering constraints say the
`IaC/ArgoCDTools` Jenkins job is the operator's to create by hand and that *"the run does not pause
for it."* V11 carries an explicit escape (*"or the correction is recorded as owed"*), and V13/V17
are covered by the "the slice ends deploy-owed" language. V10 is not, so a test phase that reaches
an unwired job has no sanctioned way to record it as owed rather than failed.

---

## F6 (advisory) — P6's pin bullet does not name the gate's hard-coded tag literal

`/work/Charts/tests/render-consumer.sh:68` asserts `image: registry:5000/argocd-hook:1` via
`grep -qF` — a fixed **substring** match. P6 frames its `:62-68` citation as the fourth-argument
assertions, and its pin bullet mentions no gate edit at all. Two consequences: setting the pin to
`"2"` reds the gate for a reason P6 does not predict, and setting it to any tag whose first
character is `1` (`"12"`, `"10"`) leaves the assertion passing against the wrong pin — a silent
false green in the one phase whose job is confirming that number.
