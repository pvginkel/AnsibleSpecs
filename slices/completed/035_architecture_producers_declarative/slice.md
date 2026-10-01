---
issue: ANS-175
---

# 035 — Architecture producers to declarative

**Improvement.** This is the first half of the declarative migration of the estate's Jenkins pipelines.
The operator's verdict after slice 033's trial was "migrate all". Slice 034 then wrote the style
guide (`pipelines.home/docs`, source in JenkinsPipelineUtils `docs/`) that the migration follows.
This slice moves every architecture producer, the `Jenkinsfile.architecture` files behind the
`AaC/*` jobs, onto the guide's declarative form. It adds the library helper the guide accepts
for that type (J16 `architectureProducer(…)`) and moves the job configuration Jenkins holds in
its UI into each file (ANS-84's ask, for these jobs). The build and deploy pipelines are the
second half. That slice is not filed yet; see § Not in this slice.

Source: the review `reviews/2026-09-jenkinsfile-review/` (`report.md` holds the operator's
rulings per item, `plan.md` how the review is worked, `inventory.md` the pipeline types), the
triage record `handovers/triage_2026-09-30.md` (§ After 033 is the migration's carry list), and
this triage's chat of 2026-10-01.

## Requirements

1. **Every architecture producer becomes declarative per the style guide.** The operator after
   the 033 trial: "I have no problem all pipelines being rewritten. [...] I do think it's worth
   the migration. [...] And yes, the pipelines that can become a few lines, of course, migrate
   those so that they are a few lines. It doeesn't exclude this rewrite." The scope is the
   inventory's T1 (app producers, 23) and T2 (deploy-repo producers, 49), plus the five
   ModernAppTemplate-rendered apps' producers (requirement 2): 77 files.
2. **The five ModernAppTemplate apps are migrated; ModernAppTemplate itself is not.** Operator,
   2026-10-01, overruling the skip of slice 034's plan review ("Please completely skip the
   moderapptemplate repos. I'll get them fixed when we do the next sync."): "It's fine if MAT is
   broken. The next sync it'll look at all pipelines in the other repos, and fix its template.
   An agent does this. The downstream repos of MAT, so IoTSupport and ElectronicsInventory must
   be migrated themselves. Aligning that with MAT is a reconciliation step that's done later."
   And, confirming: "Yeah that really was a misinterpretation. MAT itself must be skipped, the
   downstream repos not." The apps are DHCPApp, ElectronicsInventory, FieldnotesApp, IoTSupport
   and ZigbeeControl. Their producer jobs are `AaC/DHCPApp`, `AaC/ElectronicsInventory`,
   `AaC/FieldnotesApp`, `AaC/IoTSupport` and `AaC/ZigbeeControl`. This restores Q11's original
   ruling: "Do 'the right thing' for those pipelines, and we'll handle merging later." The
   guide (034) and `inventory.md` were written under the skip and list these apps as untyped.
3. **J16: an `architectureProducer(…)` helper for the producers.** report.md J16, "accept". The
   guide's library page lists it as "accepted, not yet in the library", and until it lands
   "the type's reference file is the full declarative file." The 2026-09-30 refresh of J16: "77
   copies now: 28 app producers (with `AaC/FieldnotesApp`) and 49 deploy producers (with
   `KeycloakDeploy/Jenkinsfile.architecture-dev`). Slice 026 (ANS-116) moved every app producer
   onto `aac-tools`; it closed 2026-09-30 and none still run a copied `arch-validate.py`. Once
   026 closes, the helper only removes boilerplate, and it is written against the post-026
   bodies." The report's J16 also notes "Depends on — [...] J17 for the IoTSupport variant"
   (IoTSupport's producer generates with Vault; J17 is in the second slice).
4. **J01: the job configuration moves into the files.** report.md J01, "accept". ANS-84, the
   operator's original ask: "There's a lot of manual configuration in Jenkins. Things linke
   disallow concurrent builds. I'd like a cleanup to move as much of possible of this into the
   Jenkinsfiles." In declarative form the concurrency guard and the trigger go into
   `options{}`/`triggers{}`, by the guide's PROP rules (the operator accepted PROP-3's list as
   decision D1 of 034's close-out). The report's Appendix A has the per-job rows. Report
   Theme A (2026-09-30): "All 49 `AaC/*Deploy` jobs are UI-only", and `AaC/Ansible` and
   `AaC/YouTrackMCPServer` have no guard at all.
5. **Q9:** "`AaC/UnderfloorHeatingController` is the only AaC job with `abortPrevious=false`.
   Reason, or accident?" Operator: "Accident."
6. **J24, J25, J23 ride along in the same edit.** report.md, each "accept". J24: "Replace `git
   branch: 'main', credentialsId: '5f6fbd66-…', url: 'https://github.com/pvginkel/<Repo>.git'`
   with `checkout scm`". Its 2026-09-30 refresh: "There is no `KubeCoderDeploy` exception:
   `AaC/KubeCoderDeploy` builds `*/prd`, the branch its clone takes [...] 49 deploy producers
   clone themselves (`:16-18`; `ArgoCDDeploy` and `KubeCoderDeploy` at `:26-28`)." J25: dead
   imports, whitespace, stale comments, "only while a file is being touched". J23: one library
   load line ("accept. See, this is something we need in the style guide.").
7. **034 close-out B2, the producer part.** "`Ansible/Jenkinsfile.architecture` (AaC/Ansible)
   inherits 'jenkins-agent kaniko' but builds no image." Folded into the migration on
   2026-10-01.
8. **How the change is pushed and checked.** Operator, 2026-09-30: "I would very much suggest
   that we don't track all repos. We're basically going to push everything, right? I would
   suggest you just change everything and push it all out in one go, and then stop. Let the
   system churn through the whole thing, and when everything's quiet (i.e. the Jenkins build
   queue goes empty), check the results. That's one pull, instead of 124 track_build.py calls."
   The plan records how the planning reads this: "'quiet' is an empty queue **and** no running
   builds, with any item waiting past a bound on 'nodes offline' treated as the Kubernetes-cloud
   slot leak (reset from the Script Console), not as churn; the check is one Jenkins API pull of
   every job's `lastBuild` against the push time." The churn includes the deploy-repo pushes'
   `AaC/*` jobs and the Architecture rebuilds. On verification: "it's not necessary to do the
   replay like this. Pushing a new version, and checking the result is fine." Each push still
   needs the operator's OK.

## Rulings and Q&A (triage, 2026-10-01)

- **The cut.** The migration is two slices, and this one, the producers, goes first. Operator:
  "Q1: Agreed." The recommendation they agreed to: the producers are 72 near-identical files
  (77 with the five apps) with no pin writes, so they roll no app in prd. They prove the helper
  pattern and the quiet-queue check before the build pipelines, whose pin writers roll every
  app.
- **The containerTemplates describables.** Retiring them (033 close-out I1) breaks the
  ModernAppTemplate template. Operator: "It's fine if MAT is broken." The retirement itself
  belongs to the second slice, once no migrated file calls them.
- **Q13's second-build check is superseded by the push-once check.** Operator: "Q3: Yes." What
  Q13 established still holds, quoted from report.md Q13 (C, 2026-09-30, after reading the
  source): "`JobPropertyStep.run()` (workflow-multibranch) works in two modes: [...] First run,
  with no tracker and no earlier `properties` step: it removes nothing and appends the declared
  properties. A UI-set property of the same kind stays beside them. [...] Every later run: it
  removes *every* property whose descriptor the tracker lists, UI copies included, then adds the
  declared ones. The duplicates are gone after one more build. [...] For §9 this means each job
  carries duplicates between its first and second build after the edit. In that window
  `getProperty` returns the first match, the UI copy, so the old `abortPrevious` applies once
  more." That passage is about scripted `properties([...])`. Declarative records its own
  tracker (`DeclarativeJobPropertyTrackerAction`, report.md Theme A).
- **J15 is not built; J19 is ruled against.** The guide's library page records both.

## Not in this slice (the second half, unfiled)

The build and deploy pipelines (inventory T3–T13 and the five apps' `Jenkinsfile`), with J14
`espFirmware`, J17, J21, J11, J12, J02, J26, Q2, the stage generators, podYaml's 033 B3/B4 and
python template, 034 B2's other three files, 034 I2, 033 I1's retirement of the describables,
Q6's `KEYCLOAK_*` inlining (back in scope with IoTSupport), §2 and §9, and closing ANS-84. They
are recorded in `handovers/triage_2026-09-30.md` § Cut: slice 035. That slice is cut after this
one closes.

## Cards

- ANS-84 stays open. The second slice absorbs it, because that slice finishes the move.
