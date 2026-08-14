# Consult 2 — slice 007, generation 2

Verdict: **complete**.

## What I judged against

Generation 2's bar is blocking-only, so the question was narrow: is there an acceptance criterion
with no implementing work behind it, a done-record admitting a leftover, a ruling no phase
delivered, or a later phase depending on something nothing produced? I walked V01–V22 against the
merged trees, read P9/P10/P11's review results (the three phases generation 1 appended), and
re-derived the two contracts the slice hangs on rather than trusting the done-records.

## Every criterion traces to work

- **V01–V09** — the `ArgoCDTools` tree at `98ce20f`: the four-argument entrypoint, the clone at
  SHA through the credential helper (with P9's chain reset), the state backend and key scheme, the
  in-pod kubeconfig synthesis, the apply with the clone's tfvars, the reattach bound to
  `Released` + `claimRef.namespace ==`, exit-code discipline, and the image whose build assertion
  checks what D31 names. P2's and P3's live proofs are recorded; the test phase re-proves them.
- **V12/V13** — Charts `3600c2f`: `_tf-presync-hook.tpl` renders four `required`-guarded args in
  the entrypoint's positional order, and P10's sequence assertion is what makes a swap fail.
  `dist/homelab-shared-0.2.0.tgz` is committed and untouched by P10.
- **V14** — the repo commits no estate fact: the whole Ansible-side diff is `openbao.yml` plus
  `docs/slice-doc-plan.md`, and `ArgoCDTools` carries no `clusters.yaml` value.
- **V15/V16/V18** — `attachments/credential-inventory.md`. I re-derived its key set two ways: every
  name `presync` requires (`GIT_USERNAME`, `GITHUB_TOKEN`, and `backend.provide()`'s
  `TF_BACKEND_HTTP_ENCRYPTION_PROVIDER` / `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` / `SOPS_AGE_KEY`)
  is in it, and its provider rows match `_providers/providers.tf`'s five declarations — including
  `postgres_admin_host` / `postgres_admin_password`, which the `postgresql` provider block reads as
  TF variables rather than env fallbacks.
- **V17** — P6's single `iac/tf-backend` entry, with the comment stating why the leaf is shared
  rather than copied.
- **V19** — nothing from slice 009 is here and `support/iac-image/` is untouched, confirmed against
  the diff from the slice base.
- **V20–V22** — P7's four-argument and enumerated-leaves amendments across `argo-cd/`, and P8's
  surface 2 in `slice-doc-plan.md`.
- **V10/V11** — the test phase's, gated on the operator prerequisites the run already carded (the
  `IaC/ArgoCDTools` job, the PAT, the `bao kv put`, `site-openbao.yml`).

## The two hinges I re-derived rather than trusted

The credential-delivery ruling only holds if the **Job** actually delivers: the shipped template
carries `envFrom: [{secretRef: {name: argocd-hook-credentials}}]` beside the four args, so slice 009
authors an ExternalSecret against a consumer that already exists — no 0.3.0 bump is owed for it.
And the four-argument contract agrees end to end: `_tf-presync-hook.tpl:45-48`, `presync.cli`'s
positional `parse_args`, and `design.md`'s ApplicationSet `parameters:` block all read repo,
revision, stage, namespace in that order.

## Fixed in this session (mechanical residue)

Both from P11's review, both prose in files this slice's diff already touched — AnsibleSpecs
`c0819e5`:

- `design.md:404`'s identity table still called the Secret *"the whole of a run's environment"*,
  which P9's `TF_VAR_stage`/`TF_VAR_namespace` export contradicts. Flow step 4 was corrected by the
  sentence P11 added right after it; the table row was not. It now says *"everything a run's
  environment carries beyond its own Job arguments"*.
- `verification.json` V20's evidence pointer `design.md:196-203` stopped one line short of the
  `hook.namespace` value the criterion is about; the block runs `196-204`.

## What I carded rather than appended

Two Minor advisories from the appended phases' reviews, neither of which can produce a wrong result
in production: P10's awk latch binds to the render's first `args:` block (a possible false **red**
in Charts' own gate, never a false green), and an empty stage/namespace argument would be exported
verbatim — unreachable from a rendered Job, because Helm's `required` rejects the empty string too.
