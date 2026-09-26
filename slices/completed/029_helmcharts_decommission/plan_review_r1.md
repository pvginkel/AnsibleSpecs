# Slice 029 — plan review, round 1

Verdict: **issues**, with two blocking findings and two advisory ones. The plan is sound in
structure. Every requirement R1–R7 maps to criteria that quote the operator's wording. All nine
`Target:` lines resolve (`run_loop.py --dry-run`), the phases run producers-first, and the
attachment is written at the altitude the executor needs.

The code citations I opened all hold:

- `argo_migrate.py` :88-99, :444-450, :495-502, :935-937, :970, :1521-1533 and :1746.
- `applicationsets.yaml:64-204` and `render-chart.py:504-652`.
- `pipeline-producers.yaml:26-28` and `views/infrastructure.yaml:12`.
- `cicd.groovy:1-2` and `helmCharts.groovy:177-196`.
- `release.py:16-31`, `origin/main` `test_prd_tree.py:94-147`, and `recommend_resources.py` :73-121 and :161-222.
- `argocd.md` :585 and :612-614.

I re-derived these facts myself, without relying on the plan:

- **Architecture dataset.** The published dataset holds 40 `helm-charts` elements. 91 relations touch them and 37 of them are referenced. The unreferenced three are opensearch, phpmyadmin and rabbitmq. `ss:dnsmasq` belongs to `dnsmasq-deploy`.
- **Live Applications.** There are 50 in `argocd-prd`: 41 owned by `releases-local` and 9 by `releases-upstream`. `argocd-prd` carries the resources finalizer. No Application has labels or a tracking annotation.
- **Webhooks.** ArgoCDDeploy has one webhook, to Jenkins. HelmCharts has two, to Jenkins and to the relay.
- **Namespace module.** 49 files call it: 46 under `configs/dev` and 3 under `configs/prd`.
- **R1 re-check.** V01's state holds.

## Blocking

### B1 — At the end of the run, the docs and argo-migrate move to ArgoCDDeploy's registry, but Argo reads HelmCharts' registry until the operator's switch. No phase owns the docs across that boundary.

**Problem.** P9 says the docs will "describe the Argo CD deploy path instead: deploy repos, and ArgoCDDeploy's registry". V18 asserts the same. That registry location only becomes true at the operator's switch, and V15 is `owed_after` that switch.

The run ends in S1. The ApplicationSets still generate every Application from HelmCharts `configs/prd/*/*/release.yaml` (ArgoCDDeploy `config/prd/values.yaml:171-179`). The plan does not say:

- what the docs should state for the interval between the end of the run and the switch;
- which doc statements change at the switch. Neither P6's runbook nor the attachment's "After the switch" list names them.

**Evidence.**

- `docs/runbooks/argocd.md` has procedures that depend on which registry is live:
  - the Registry row of the components table (:45);
  - the entry format and its HelmCharts path (:220);
  - the handover flip (:412);
  - "Bootstrapping Argo from nothing" (:681-685), which relies on Argo's own entry in HelmCharts and on HelmCharts' registry webhook.
- `docs/slice-doc-plan.md` bans aspirational claims: "If the slice left something owed to the operator, write that it is owed rather than that it is done". V18, as worded, asks for exactly such a claim.
- For the tool, the plan already acknowledges the same interval. The attachment says the second equivalence run catches "a flip or autosync made in the new registry, which is not live yet".

**Impact.** Whichever way P9 writes these procedures, one of the two periods is wrong:

- **Written for ArgoCDDeploy's registry:** the bootstrap and registration procedures are wrong until the switch. A cold boot or a registration in that window follows a registry Argo does not read.
- **Written for today:** they are wrong after the switch, and nothing owns the edit. The loop's doc phase also runs before the switch.

Either way, the test agent checks V18 against a claim the live system contradicts on one side of the switch. Which period the docs describe may need the operator's call.

### B2 — The rulings section carries three facts that the phases contradict. The corrections sit in phase text instead of the rulings being edited in place.

**Problem and evidence.**

- **(a) The webhook.** The D2 sketch's "Stays" bullet reads: "push-only refresh (D6: a registry commit refreshes `releases` through the webhook ArgoCDDeploy already receives…)". P5 answers: "the rulings' 'the webhook ArgoCDDeploy already receives' does not hold". The code agrees with P5: `gh api repos/pvginkel/ArgoCDDeploy/hooks` returns one hook, to `https://jenkins.webathome.org/github-webhook/`.
- **(b) The element count.** The session-settled bullet reads: "The helm-charts producer publishes 41 elements, not 40 (premise correction)". P2 answers: "the session's count of 41 no longer holds". The published dataset agrees with P2: 40 elements, with `ss:dnsmasq` belonging to `dnsmasq-deploy`.
- **(c) `register`.** The session-settled bullet reads: "`argo_migrate.py`'s register, flip and autosync edit HelmCharts' `release.yaml` … They move to editing the registry values file". P7 and V16 say `register` is unchanged. The code agrees with P7:
  - `cmd_register` (`argo_migrate.py:1521-1533`) writes only Architecture's `pipeline-producers.yaml`;
  - `registry_entry`, `cmd_flip` and `cmd_autosync` (:1536-1570) are the only writers of `release.yaml`.

  So V16 departs from R6's literal "move … `argo_migrate.py`'s register" step. The code is on its side, but no ruling records it.

**Impact.** The rulings are "authoritative on intent". They are the doc phase's only steering, and P7's reviewer judges against them. A session that trusts the rulings over the phase text could:

- write a webhook that does not exist into the D6/D39 records or the docs;
- restate 41 elements;
- flag V16 as dropping part of R6.

The template's rule is that rulings are living text, edited in place. Leaving them wrong, with corrections chained in phase text, is the pattern that rule exists to prevent.

## Advisory

### A1 — The way back depends on behaviour the rehearsal does not prove

Two claims in the attachment rely on a recreated ApplicationSet taking ownership of an existing, unowned Application of the same name:

- S2: "If `argocd-prd` is synced now, it recreates them, they take the Applications back".
- "The way back" from S3 or S4. From S4 it also relies on `releases` being gone before the ApplicationSets return, or invariant 2 does not hold.

The rehearsal's list of what it must show covers only the forward path:

- orphan-delete keeps the child;
- the app-of-apps' first diff is tracking metadata only;
- the child is unchanged after the sync;
- deleting the app-of-apps leaves the child;
- teardown leaves nothing behind.

So the rollback from every state past the orphan-delete is untested before the real switch of 50 Applications. That is the path the operator would take under pressure.

### A2 — P6's step order and V14 leave out the second equivalence run

The attachment says the runbook runs the equivalence check "first, and again right before the flip". That second run is the one that catches drift after P4: a HelmCharts entry edited after the move, or a flip or autosync made in the new registry by P7's tool.

P6's numbered order has the check only once (step 3), and so does V14. The test agent checks V14 against its own list, so a runbook without the second run would pass V14.
