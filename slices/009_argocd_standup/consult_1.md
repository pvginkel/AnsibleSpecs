# Consult 1 — slice 009 argocd_standup

**Outcome: `complete`.** No phase appended. Two comment-only residues fixed in session
(ArgoCDDeploy `415a0c4`), and the close-out reconciled.

## What I checked, and against what

The bar is narrow: append a phase only for *build work the plan owes and no phase delivered* — a
requirement or ruling nothing carried out, an acceptance criterion with no implementing work to
point at. Everything else is a close-out entry. Priced honestly, a phase costs an executor round, a
review round and the consult this generation forces; a close-out line costs the operator one word.

### Requirements R1–R7

| | Owed | Delivered by |
| --- | --- | --- |
| R1 | wrapper chart pinning `argo-cd`, AppProject, both ApplicationSets, notifications, SSO, webhook secret ref, the three register values | P1 (`chart/Chart.yaml` pins **10.3.3** exactly, `config/prd/values.yaml` carries `application.resourceTrackingMethod: annotation`, `controller.operation.processors: 2`, `timeout.reconciliation: 0s`), P2, P3 |
| R2 | the Keycloak client | Ruled out of the repo 2026-08-16 — hand-created, no `terraform/`, no Keycloak provider credential. The client secret arrives as the `argocd-oidc` ExternalSecret (P2). The ruling's *second* half — "record it so #68 can import" — is now an explicit keystroke in close-out **A2**. |
| R3 | `argocd-hooks`, the composed credential object, `tf-presync` + RBAC, AppProject destination | P4. All **22** keys checked key-by-key against slice 007's `credential-inventory.md`: 9 leaves, 13 literals, none missing, none invented. |
| R4 | repository credentials via ESO | P2 — one `repo-creds` Secret on `https://github.com/pvginkel/`. R4's "check whether anonymous read suffices" was answered at planning time: nowhere. |
| R5 | exposure + **O3** | P1 (`is-public: "no"` **and** `enable-ssl: "yes"` on argocd-server) and P5 (the relay is the one public Service). O3 settled in the plan's rulings. |
| R6, R7 | bootstrap, the registry webhook | Operator, by the plan's design. P6 committed the registry entry as the last code phase, per the r1 F4 ruling. |

### The sixteen rulings

Each is carried out by a phase, or by a deliberate omission a phase records. The only two not
discharged inside a phase are assigned elsewhere *by the plan itself*:

- **The `namespace: argocd` correction across the `argo-cd/` document set** — the 2026-08-16
  namespace ruling ends "*and the doc phase corrects them*". The doc phase is the driver's, and it
  runs after this consult. Appending a phase for it would duplicate it.
- **Recording the Keycloak client for Trello #68** — an operator keystroke, now written into **A2**.

### Acceptance criteria

V01–V10, V19 (build half), V28, V29 and V30 all have implementing work I could point at and read.
V11–V18 and V20–V27 are the A.5 proof items, which the plan states are "outcome-level acceptance,
**not extra build work**" and which run against a cluster after the operator's bootstrap — the one
that *was* build work in disguise, the throwaway deploy repo, already became P5a on the r1 F1 ruling.

I read the artefacts rather than the done-records: the wrapper chart's values, all four templates,
both ApplicationSet bodies (four hook parameters including `hook.namespace`, `requeueAfterSeconds: 0`,
`missingkey=error`, the finalizer, the shared `templatePatch`), the AppProject's destinations and
whitelist, the hook ClusterRole, and ProofDeploy's chart, `terraform/` and stage config.

### Nothing downstream depends on an unproduced thing

P5's `registry:5000/webhook-relay:2485` exists (slice 015 published it, P5 verified it in the
registry). P5a's `homelab-shared` 0.2.0 resolves from `https://charts.home`. P6's entry depends on
P3's ApplicationSets, which exist.

## What I fixed rather than reported

Mechanical residue — comment text, no behaviour change, in files this slice authored. Committed to
`main` in `/work/ArgoCDDeploy` as `415a0c4`; `tests/render-chart.py` still prints `ok: 68 objects
render into argocd-prd and argocd-hooks` and `helm lint` still exits 0.

- **B13** — `webhook-relay.yaml` and `tests/render-chart.py` justified the `:80` leg with "a leg
  pointed at 443 fails on the TLS handshake". With `server.insecure: true` both Service ports front
  the same plain listener, so 443 would answer; the handshake failure belongs to an `https://`
  *scheme*. Port 80 is still right, now for the reason actually written.
- **B8** — the ExternalSecret header said the shared ESO helper "lives in HelmCharts' charts". It is
  defined once, in `Charts`' library chart at `_helpers.tpl:204`.

## Close-out reconciliation

- **B4** struck — *resolved by P2 (`f747a9f`) and P4 (`008126d`)*, verified against the merged tree.
  P2 retired dex and rewrote the params loop, which now reads `("repo.server", "redis.server")` and
  asserts dex is absent; P4 replaced the bare `next()` with the namespace read off
  `argocd-cmd-params-cm`. The phase predicted to inherit a red gate is the one that fixed it.
- **B8**, **B13** struck — fixed in place, above.
- **S10** struck — *folded into A1 and A4*. Re-checked both remotes: `git ls-remote origin` is empty
  in `/work/ProofDeploy` **and** in `/work/ArgoCDDeploy`. The prerequisite now sits in the two
  entries an operator actually reaches for, not in a suggestion beside them.
- **A2** extended with the #68 record, discharging the R2 ruling's second half.
- **S13** added — `/work/Ansible/.tmp-argocd-values.yaml`, a 178 KB untracked scratch dump from the
  run, neither committed nor gitignored. Not deleted: it is untracked in a working tree the operator
  shares.

**B5** deliberately left standing. It is adjacent to B4 in the same function and *not* resolved: the
`repo.server`/`redis.server` block still cannot fail, because both sides come from one render.
Removing dead assertions is a code change, not comment residue, and it is sub-bar for a phase.

## What is genuinely left, and why none of it is a phase

Everything outstanding is live verification against a cluster that does not exist yet, or an
operator keystroke, or a gate-coverage hole in work that is itself correct. The four **A** entries
are the runbook for the bootstrap; **B5–B7, B9, B11, B12, B15, B16** are test-coverage gaps where
the shipped artefact is right and the mutation that would break it is caught nowhere; **B1**, **B14**
and most of the **S** entries belong to other repos or other slices. None of it is a requirement the
plan owes and no phase delivered.
