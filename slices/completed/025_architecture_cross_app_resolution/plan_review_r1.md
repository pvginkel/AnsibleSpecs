# Slice 025 — plan review, round 1

**Verdict: questions.** The plan is sound on the things this review exists to catch. V01–V04
carry R1–R4 1:1 in the operator's words. Every ruling (D1, D2, no partial-run flag, the
acceptance proof, the prefix quirk) has a criterion, and every criterion is earned by a phase or
by the test phase. All five `Target:` lines are right: `aac-tools/` and `checks/` live in
ArgoCDTools, the generator in HelmCharts, `support/argo-migrate/` under Ansible's `root`, and the
register in AnsibleSpecs. The task shape, `cross-cutting`, is correct. There is no auto-doc
content, and P5 is a legitimate decision-record phase. One load-bearing claim is wrong, though, and
it decides who pushes HelmCharts. That is the operator's call.

What I checked against the code (repo heads unchanged since the writer: ArgoCDTools `08c9974`,
HelmCharts `399b281`, Ansible `84b5beb`):

- Every line citation in P1–P4 and V01–V14 holds.
- My own AST comparison of the two generators confirms what P2 says about which functions match.
- `split_relations` claims all of a relation's endpoints, and `"differs"` is never printed.
- Keycloak's bare-UUID relations are `ss:keycloak-prd-keycloak-keycloak → <IoT device>` edges,
  and those devices belong to `iotsupport-app`. The ids come from IoTSupport's `_relation`,
  keyed on (type, source, target), so they survive the move.
- The jenkins `install-homelab-ca → cap:continuous-integration` Realization is published.
- The published set holds no `.svc` host.
- The relation schema allows what P1 says it allows into `ApplicationInterface`.
- I derived the edge id independently. A Serving edge's id is
  `rel:{kebab(hint_of(pid))}-serves-{consumer hint}-{kebab(hint_of(target))}` (aac-tools
  `:1404`, `:1481`, `:1583`). Every input to it is available from a provider's published composite
  id. Resolving through the published set can therefore reproduce today's ids exactly, as
  V01/V07 require. Checked on postgres-pas → iot: the pooler interface's link, the pooler's
  published `cap:relational-database` Realization, and the consumer's own hint.

---

## Q1 — Operator-decidable: the plan's "pushing HelmCharts redeploys nothing" is wrong, and no push hold exists

**Problem.** The plan says a HelmCharts push deploys nothing. It says so in the grounding at
plan.md:99-101 ("the HelmCharts `Jenkinsfile`'s `changed()` acts only on chart sources, config
trees and the shared Terraform surface, not `tools/`") and in P2's last constraint at :209.
`changed()` is only half of what triggers a deploy. So there is no `## Push holds` for
`../HelmCharts`, and the test phase will push it.

**Evidence.**

- HelmCharts `Jenkinsfile:35`: `pipelineTriggers([githubPush()])`, so IaC/HelmCharts runs on
  every push to `main`.
- `Jenkinsfile:192-193`: a release deploys when
  `!entry['disabled'] && (changed(entry) || entry['args'] != '')`.
- `tools/chart_tools/resolve_helm_args.py:152,157`: `args` is non-empty whenever any image's
  registry digest differs from the value deployed in prd.
- `resolve_helm_args.py:179-180`: an upstream-chart release gets `--version <latest>` whenever
  its deployed chart is behind the chart repository's latest.
- Upstream releases in `configs/prd/` include cloudnative-pg, external-secrets, prometheus,
  grafana, step-ca, headlamp, ceph-csi-rbd, ceph-csi-cephfs and csi-driver-smb.
- The Ansible slice-testing-strategy §4 says "Push what the slice committed". The run loop's
  test phase pushes siblings, and "prd stays operator-gated" (run-loop.md). The same doc records
  a run in which a HelmCharts push crash-looped prd.

**Impact.**

- The test agent's HelmCharts push will be an unattended prd rollout of everything that has
  drifted since the last push: upstream chart upgrades and in-house images whose digests moved.
  None of that is this slice's change.
- V02 (the collect is green after HelmCharts publishes) and V13 (the proof "after HelmCharts'
  patched producer has published") both depend on that push.
- The operator's answer therefore also decides where those two criteria land. Either the test
  phase settles them, or they are owed to the operator after the operator pushes HelmCharts.
- The plan cannot make that decision on a premise that does not hold.

## Q2 — Operator-decidable (low stakes): the instance → interface relation type is left to P1's executor

**Problem.** D1 rules that every interface is "linked directly" to its serving instances, and D2
rules which instances. Neither ruling says which relation type the link is. P1 leaves the choice
to the executor ("the done-record states what got settled: … the linking relation type").

**Evidence.**

- The published set has no instance → interface relation of any kind to follow. Today every
  `applicationInterfaces` relation is an `Assignment` to an application service, across all
  producers. The one component → interface precedent is Architecture's `Composition` into
  `technologyInterfaces`.
- The schema allows five types from both SystemSoftware and ApplicationComponent:
  `Realization`, `Association`, `Serving`, `Flow` and `Triggering`. `Composition` and
  `Aggregation` are allowed only from ApplicationComponent. `Assignment` is allowed from neither.
  So none of the natural ArchiMate readings is available uniformly.
- The refinement gave the model's shape to the operator: D1 "Why yours: … you treat the model as
  first-class". D2 also went to the operator because "it changes what the viewer shows on an
  interface".

**Impact.**

- The executor's pick becomes the semantics of about 60–80 new links plus 52 on today's
  exposed-host interfaces. It also becomes what the viewer draws for them.
- A `Serving` link would sit in the model beside the cross-app `Serving` dependency edges this
  slice is about, and read the same way.
- Changing the type later is a lockstep change to both generators. Until the pending handovers
  finish, it also shows up as a differing field on every kept link id.

## A1 — Advisory: P3's and P4's gate logic has no test surface

**Problem.** P1 and P2 name their test files. P3 and P4 name none, and nothing deterministic
gates either of them.

**Evidence.**

- `handover_equality.py` is "Not part of `kc project test`, and not meant to be" (its docstring).
- No test in `aac-tools/tests/` references it.
- P4's `Target: root` has no test verb: Ansible's `kc project info` lists tests only for
  ansible, terraform and architecture.
- The gate has already failed silently once. The `"differs"` grep P4 fixes (argo_migrate.py:742
  against handover_equality.py:201-204) meant that no field difference has ever stopped an app.

**Impact.** Three things decide whether a handover may drop an id from prd's published model:
P3's exact scoping, P3's relation-ownership classification, and P4's HelmCharts-side comparison.
They will run 16 times in the bulk migration. Reviewers will judge them by reading only, and the
code-reviewer will be told the state is unverified.
