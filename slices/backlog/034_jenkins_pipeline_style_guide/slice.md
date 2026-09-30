---
issue: ANS-170
---

# 034 — Jenkins pipeline style guide, its docs site and skill

**Improvement.** This slice writes one strict, example-driven style guide for every kind of
Jenkins pipeline in the estate. It covers stage labels, stage granularity, checkout, pods,
secrets, timeouts, notifications, file layout, and when code belongs in the shared library
(JenkinsPipelineUtils). The guide is published on a docs site at `pipelines.home`, next to the
library's reference pages, and a skill carries its rules into every session that writes a
Jenkinsfile. The declarative migration of all pipelines is the next slice, and it is built from
this guide.

## What is being requested and why

The review is AnsibleSpecs `reviews/2026-09-jenkinsfile-review/report.md`, with its work plan
`plan.md`. The triage record is `handovers/triage_2026-09-30.md`: this slice is the rest of its
group A, which slice 033 (ANS-166) left open. Slice 033 is complete. Its declarative trial on
`KubeCoder/Jenkinsfile` passed, and the operator's verdict is **migrate all**.

The operator's ask, 2026-09-30, in the session that filed this slice:

> "I'd like to progress with the next step. I would like the style guide to be delivered. This
> will also impact the pipeline we just migrated.
>
> What I'm looking for is a style guide that basically touches every aspect of building
> pipelines. How do we label stages, what's the granularity we pick for stages, how do we clone
> repos, etc. I want it to use examples (so cookbook), and I want it to be followed strictly.
> Ideally it covers every (type of) pipeline we have. And when do we put something into the
> utility library.
>
> Then I want this used for the actual pipeline migration."

After Claude proposed the approach below, the operator said:

> "Yes, that sounds fine. Please have a dedicated section for labeling stages. I find these
> very messy and all over the place.
>
> Hostname: pipelines.home/docs, with an index page at /.
> We could host the performance checker there also? I'm not sure man. I mean that's a whole new
> thing. I'm honestly not too worried. Maybe not start with it.
>
> Go"

"Performance checker" refers to the conformance checker Claude proposed (see requirement 8).

Routing, from earlier sessions: 2026-09-21, "I think I'd prefer doing all this work in its own
slices. A triage session should really be deciding that." And 2026-09-30, on the first cut: "I
would think the style guide stands alone, because as you said it depends on the trial."

## The approach the operator agreed to (2026-09-30)

Claude proposed the following, and the operator answered "Yes, that sounds fine":

1. **Inventory.** List every pipeline type in the estate, from the clones and the report:
   roughly ten, among them app build with pin write, ESP-IDF firmware, monorepo validation Job,
   `Jenkinsfile.architecture` producers, the `iac-*` controller jobs, and the odd ones
   (DockerImages, Intercom, Architecture, HA Fleet). For each topic, also record how the files
   handle it today.
2. **A rulings page for the operator.** For each topic, one proposed rule with a short example,
   and the operator rules on it. The topics are stage naming, stage granularity, checkout, pod
   definition, secrets and `withVault` scope, timeouts, `post`/`notify`, file naming and
   headers, and when code goes into the library. Stage granularity and the library rule are
   judgment calls, so Claude doesn't settle them alone.
3. **The cookbook.** Rules written as MUSTs, with the reason for each. One complete reference
   Jenkinsfile per pipeline type, a short recipe per topic, and a decision test for when
   something goes into the library. Every example passes the declarative linter.
4. **Where it lives.** A Zensical docs site in `JenkinsPipelineUtils/docs/`, which also takes
   J22's library reference pages, plus a short skill that carries the hard rules and links to
   the site.
5. **Webhook test (§6a)** stays in this slice, because its result becomes the guide's recipe
   for setting up a new repo. It needs a throwaway repo and job, and the operator's OK first.

## Requirements

1. **Inventory of pipeline types** (Improvement): every kind of pipeline the estate runs, and
   for each topic the variants in use today. Source: the 125 jobs of `report.md` Appendix A
   and the clones (plan.md, "State does not survive an environment", says how to rebuild them).
2. **Rulings page** (Improvement): one proposed rule plus an example per topic. The operator
   rules before the guide is written. It goes in the slice folder or the review folder, as
   planning decides.
3. **A dedicated section on stage labels** (Improvement). Operator: "Please have a dedicated
   section for labeling stages. I find these very messy and all over the place." It sits next
   to the section on stage granularity, not inside it.
4. **The cookbook** (Improvement): the style guide itself, strict ("I want it to be followed
   strictly"), with examples, covering every pipeline type. Plan §4 lists the rulings it has to
   carry: "J24 (`checkout scm` for the job's own repo), J23 (the one load line), J01 (the
   job-properties block and its placement; ~~J13~~ retention is the global build discarder, so
   files declare none), J08 (the declarative rule after §3), J11/J12 (timeouts), J17
   (`withVault` scope), J19 (the iac dev-stage duplication is deliberate: those files stay
   self-contained), the §6a result (what a new repo needs for its push hook), non-secret
   settings inline rather than as global env vars (Q6; `HA_URL` is the ruled exception, and
   endpoints never go into OpenBao), `notify` use, `Jenkinsfile.*` naming, and header
   comments." J08 is now "migrate all", so the guide describes declarative only. J23:
   "See, this is something we need in the style guide."
5. **When code goes into the library** (Improvement). Operator: "And when do we put something
   into the utility library." The guide gives a decision test, with examples from the estate:
   J14/J15/J16 are accepted helpers, and J19 was ruled against ("Keep the duplication; the
   style guide says it is deliberate").
6. **Docs site at `pipelines.home`** (Improvement). Operator: "Hostname: pipelines.home/docs,
   with an index page at /." Source in `JenkinsPipelineUtils/docs/`, built with Zensical (plan
   §4: "Starlight is the fallback if Zensical isn't stable by then"). The library has no
   `Jenkinsfile` and no Jenkins job today, so building and publishing the site is new.
   Serving it is new too: a host, DNS for `pipelines.home`, and whatever deploy path the
   estate uses for a static site. Planning grounds this.
7. **J22's docs half** (Improvement; accepted): library reference pages on the site, "replacing
   `vars/*.txt`" (plan §4), generated from `vars/` or kept next to it. That includes
   `containerTemplates.podYaml`, which slice 033 added.
8. **The skill** (Improvement). Operator, 2026-09-23: "Instead I want a skill. Likely
   KubeCoderConfig is good enough for this, but we can review that once we get to it." And:
   "Btw the skill is itself still a reference to the online docs. The kubecoder env skill is
   like that also." The skill's home is reviewed in planning. KubeCoderConfig has no YouTrack
   project and is worked from KubeCoder's environment (the youtrack-usage skill says so).
9. **§6a — the webhook test** (Improvement). This is the operator's note on Appendix A R1: "I
   want to test this." Plan §6a has the steps, which start with the operator's OK to create a
   throwaway private repo and job. The result goes into the guide.

## Out of scope

- **A conformance checker.** Operator: "Maybe not start with it." It isn't built here. The
  guide's rules are written so that one could check them later.
- **Converting any pipeline**, including bringing `KubeCoder/Jenkinsfile` into line with the
  guide. The operator: "This will also impact the pipeline we just migrated", and "Then I want
  this used for the actual pipeline migration." The migration slice comes next and absorbs
  that. Its carry-list is `handovers/triage_2026-09-30.md` § After 033 (I1, B4, B3, stage
  generators) plus groups C and D.
- The library helpers themselves (J14–J17, J21) and ANS-84's job-configuration move.

## Source material

- **Pipeline types that generate stages or triggers** (triage § After 033): "`DockerImages/Jenkinsfile`
  (a stage per image variant) and `Intercom/Jenkinsfile` (a stage pair per hardware version:
  `matrix` or `script {}`) generate stages; `Architecture/Jenkinsfile` computes its triggers
  from YAML, which `triggers {}` cannot express." The guide needs a recipe for each of them.
- **B3** (033 close-out): `podYaml` derives a string `images:` entry's container name without
  checking RFC 1123. One of its fixes is to "state the map form's `name:` in the guide".
- **The reference conversion**: `KubeCoder/Jenkinsfile` at KubeCoder `4a6be3de`, which is
  declarative and green (Build-Main #559/#560). It predates the guide.
- **Verification of converted files** (ruled 2026-09-30): "Pushing a new version, and checking
  the result is fine." Standing rules in plan.md: each push, Replay and Jenkins API write
  needs the operator's OK; every edited Jenkinsfile goes through
  `/pipeline-model-converter/validate`.
- **The review's J-items in full**: `report.md` Themes A–E; the style guide's form is under J23
  (the 2026-09-23 response).

## Cards

This slice subsumes no card. It is the second part of ANS-84's work, and ANS-84 stays open until
the slice that moves the job configuration absorbs it.
