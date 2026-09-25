# Slice 027 — plan review r1

Verdict: **questions**. There is one operator-decidable finding and one advisory. Everything else
checked holds; the list is at the end.

## Operator-decidable

### Q1 — P1 steers the Groovy gate to a 2019 transform, not the one the controller loads the library with

**Problem.** The settled ruling says the gate compiles "through the Jenkins pipeline engine's own
transform with the Groovy version Jenkins runs (2.4.21)". P1 sends the executor to slice 011's
setup: "ANS-89's card text in slice.md describes it: the classpath …". That classpath is
`groovy-cps-1.31`, `groovy-sandbox-1.19` and `guava-11.0.1`. The grounding (plan.md:77-78) says
the controller "vendors groovy-cps in-tree, and the last standalone `com.cloudbees:groovy-cps` on
Maven Central is 1.31". It reads as if 1.31 were the only transform on offer. Neither P1 nor V01
says which transform version the gate compiles against. The plan's one hedge, "Unverified: that
the same classpath runs on the toolchain's JDK 21", is about the 1.31 classpath.

**Evidence.**
- The controller reports `workflow-cps 4376.v30c8c00684a_3` (Jenkins `pluginManager/api`,
  2026-09-25; `X-Jenkins: 2.568.3`).
- `com.cloudbees:groovy-cps:4376.v30c8c00684a_3`, the transform at the controller's own version,
  is published on `https://repo.jenkins-ci.org/public/`, which answers HTTP 200 from this pod. Its
  pom declares:
  - groovy 2.4.21 (provided);
  - groovy-sandbox 1.34.1;
  - guava 33.4.8-jre;
  - groovy-cps-dgm-builder at the same version;
  - jenkins-core 2.528.3 (provided).
- `groovy-cps-1.31.jar` on Maven Central is dated 2019-09-09.
- The controller runs 4376 with Groovy 2.4.21 on JDK 21 (JenkinsDeploy `chart/values.yaml:24`,
  `lts-jdk21`). The JDK-21 risk the plan flags belongs to the 1.31 classpath. The
  controller-matched combination already runs on JDK 21 in production.

**Impact.** As written, the likely gate compiles `vars/*.groovy` through a transform and sandbox
six years older than the ones the controller loads the library with. What it refuses at load
time may differ from what the controller refuses. V01 ("through the pipeline engine's CPS
transform on Groovy 2.4.21") and V02 would still pass on 1.31, so nobody would see the
difference. The refinement is ambiguous about what the operator agreed to:
- "the Jenkins pipeline engine's own transform" suggests the controller's version;
- "a superset an earlier slice ran successfully" suggests slice 011's 1.31 setup.

Two design costs follow, and they are the operator's to weigh:
- a gate that tracks the controller has to be bumped when workflow-cps is upgraded, as promtool
  is pinned to prd's server;
- it resolves from a second Maven repository besides Central.

## Advisory

### A1 — The rulings section hands the D61 correction to the doc phase, and P5 also makes it

**Problem.** The D2 ruling bullet ends "The doc phase owes that record the correction"
(plan.md:40-42). P5 makes that correction as a phase of its own, and says why: the doc plan
requires a doc task named by a requirement to be a phase (plan.md:224-227; Ansible
`docs/slice-doc-plan.md:71-74`). The plan template counts a plan that hands such work to the doc
phase as a defect. The rulings section, which is the doc phase's only steering, still does
exactly that.

**Evidence.** The sentence is not in refinement D2's recommendation or the operator's "Agree".
The seeding session added it. P5's Target is `../AnsibleSpecs`, and it lands the edit to
`argo-cd/decisions.md` (D61, :759-773).

**Impact.** Low. Every executor digest carries the rulings section verbatim, so every session
sees two owners for one edit. The doc-writer is told it owes an edit P5 already landed. The most
likely cost is a second pass over D61.

## Checked and holding

- **ACs against slice.md.** R1→V01-V04, R2→V05-V08, R3→V09-V12, D2's D61 consequence→V13,
  R4→V14. R4 is split to slice 030 under the D1 ruling, and that slice exists in the backlog. The
  wording is the operator's and the consequences are quoted. Every criterion has a phase that
  earns it: V07 is earned by the test phase's push of P3's work, and V13 by P5. No doc-truth
  universals.
- **Task shape.** `cross-cutting` holds. slice.md spans three sibling repos and adds a shared
  `containerTemplates` entry that slice 030 is ruled to reuse. slice.md itself settles no design.
- **Targets.** `../JenkinsPipelineUtils`, `../ArgoCDTools`, `../PrometheusDeploy` and
  `../AnsibleSpecs` all exist as git checkouts under `/work`, and each is where its phase's work
  lands.
- **Order.** P1's gate precedes P2's edit under `vars/`. P2 precedes P3, and the push-order
  constraint reaches the test agent through the plan path in its dispatch. P4 precedes P5.
- **Citations.** The following were read and are correct:
  - `vars/containerTemplates.groovy:12-76` (`modern_app_dev` at :74-76) and `vars/utils.groovy:1`;
  - ArgoCDTools `Jenkinsfile:16-56` (scripted; a clone and two kaniko stages) and
    `.kubecoder/project.yaml:24,36`;
  - PrometheusDeploy `.kubecoder/project.yaml:15-23`, the rules at `config/prd/values.yaml:58-298`
    (five groups, eight alerts), and `tests/` holding only the two scripts;
  - DockerImages `1c1945a` `kube-coder-iac-toolchain/Dockerfile:11-12,19,116-122`;
  - the `java` catalog entry (KubeCoderDeploy `chart/values.yaml`, `jdk-21`, `.m2` overlay, 1Gi);
  - Ansible `9edef16`;
  - the card's Maven Central artifacts (groovy-all 2.4.21, groovy-sandbox 1.19, groovy-cps 1.31),
    all HTTP 200.
- **Independent derivation.** Rendering prd's chart and extracting `alerting_rules.yml` from the
  `prometheus-prd-server` ConfigMap gives `promtool check rules` 3.14.0 "SUCCESS: 8 rules
  found", as P4 states.
- **Attachments and doc content.** There are no attachments and none are needed. There is no
  auto-doc content. P5's bullets are a doc-task phase's outcome statement.

A cross-slice observation, the 028/027 overlap on PrometheusDeploy's rule proofs, went to
close-out as S1.
