# P3 — code review, round 1

Branch `phase/011-P3`, `f67f790..HEAD` (AnsibleSpecs `9de4486` + the done-record commit `cf594f1`).

## Readiness

The phase lands its stated outcome. All three `design.md` sites that stated where CI writes the
tags now describe D47 (`:64-66`, `:501-504`, `:511-512`), and a grep of every `image`/`pin`
mention in that file confirms there is no fourth site the phase missed. `decisions.md`'s D45
records P2's settled signature in D40's voice (`:469-476`), and the D37 amendment now names the
chart's `required` guards rather than the absent default. Slice 012 carries R2 quoted exactly as
`phases.md:242-244` states it, beside the R4 entry, with G5/G6/G8/G10/G12 in a "Carried in from
slice 011" section placed and named the way `011/slice.md:166` does it, and its **Depends on**
line now states what this slice actually delivers. The plan's one ordering constraint holds:
KubeCoderDeploy `main` is at `49f0629`, so R8's correction follows the gate inversion rather than
preceding it. No deterministic gate is recorded green and AnsibleSpecs has none to run (no
`.kubecoder/`), so the branch's state is unverified by construction; in its place I re-ran the
phase's own two checks — every markdown link in the three edited files resolves, and the only
added lines past 100 columns are two in `plan.md`'s own done-record, not in the edited docs. What
I found is all in the handoff, not in the register: two caller-facing constraints P2 handed P3
never reached either document (F1), and item 14's new lede states a staging the same document's
G5 bullet contradicts (F2). None of it harms the product on merge — all three findings are
advisory.

## Findings

### F1 — Major, advisory (anchor: contradiction) — the two constraints P2 handed P3 for slice 012 reached neither document

`plan.md:350-355` is P2's handoff, both bullets addressed to this phase: "*P3: … Values are
written verbatim, so P1's leading colon is the caller's to supply*" and "*P3 → slice 012:
`Build-Main` declares no `disableConcurrentBuilds()`, and two builds pushing pins race on the
second push; the call also needs `git` in whichever container it runs in.*" Neither appears in the
diff. D45 as rewritten (`decisions.md:469-476`) gives the map's shape and no value semantics;
slice 012's call description (`slice.md:126-134`) says only "with `<n>` for `config/dev/values.yaml`
and `prd-<n>` for `config/prd/values.yaml`"; the "Carried in from slice 011" section
(`slice.md:360-401`) carries the five grounding bullets Ruling 5 named and neither of these. P3's
own done-record "Later phases" list (`plan.md:428-432`) repeats three inherited facts and drops
both.

Failure: slice 012's author writes the call from `slice.md:128-129` as
`pins: ['config/dev/values.yaml': ['images.controller': '524', …]]`. The five `images.*` pins are
tag *suffixes* — `config/dev/values.yaml:29` holds `controller: ":523"` and
`chart/templates/controller-deployment.yaml:46` renders
`registry:5000/kubecoder-controller{{ required "…" .Values.images.controller }}` — so the commit
renders `image: registry:5000/kubecoder-controller524`. The `required` guard passes, because the
value is non-empty; KubeCoderDeploy carries no Jenkinsfile, so nothing re-runs the render gate
between the CI-written commit and Argo's sync; the dev cutover fails on an invalid reference. The
second half is live too: `/work/KubeCoder/Jenkinsfile` declares no `properties([…])` block at all,
so `Build-Main` has no `disableConcurrentBuilds()` today.

Advisory because `cicd.groovy:29-33` carries both rules in the method's own docstring — the
`':524'` example and the concurrency sentence — and that docstring is what the author of the call
reads; and the render failure is loud and local when it comes. Confidence high on the omission,
medium on the consequence.

### F2 — Major, advisory (anchor: contradiction) — item 14's new lede stages the promotion job against the grounding the same document carries

The added lede (`slice.md:116-117`) reads "*each applied at the moment its stage flips,
`Build-Main`'s rewrite at dev's cutover, `Deploy-PRD`'s replacement at prd's*". The carried G5
bullet 250 lines later (`slice.md:369-375`, from `plan.md:160-163`) states the opposite
requirement: "*even at the dev cutover the prefix cannot simply vanish, because prd flips later
and promotion must keep working from the bare `<n>` in between.*"

Failure: a planner who takes the lede plans no promotion work at dev's cutover. At that flip
`Build-Main` stops pushing `dev-<n>` (it pushes `:<n>`/`:latest`), while the surviving
`Deploy-PRD` retags `registry:5000/kubecoder-<name>:dev-${sourceDevBuild}`
(`/work/KubeCoder/Jenkinsfile.deploy-prd:33-38`) — a tag no new build produces. prd becomes
unpromotable for every build made between the two cutovers, and the document names nothing that
performs promotion in that window. The lede is the phase's own gloss: Ruling 1 (`plan.md:43-44`)
says only "applied at the moment each stage flips, staged per stage", and B.3's own R4 text
constrains the *deletion*, not the replacement's authoring.

Advisory because the contradicting grounding is in the same document, under a heading a planner
of slice 012 will read, and because Ruling 3 records that KubeCoder is not under active
development, so the window is unlikely to need a promotion. Confidence medium-high.

### F3 — Minor, advisory (anchor: none) — two of the register's new absolutes are contradicted by the chart they describe

`decisions.md:397` now says "*the chart `required`-guards every tag it renders*". It does not:
`chart/templates/controller-deployment.yaml:225` renders
`registry:5000/kube-coder-tunnel-reclaim{{ .Values.images.tunnelReclaim }}` with no guard, and
`controller-config.yaml:13` ranges over `list "worker" "vsix"` only, while
`controllerConfig.images.localHome` rides the same unguarded `toYaml` dump. The plan asked for the
narrower true statement — "*the chart `required`-guards all seven; say that*" (`plan.md:397-398`).
`design.md:511-512` similarly generalises the old "*the chart's committed default tag*" into
"*Every committed tag is a real `<n>` or `prd-<n>`, never `latest`*", while `chart/values.yaml:17`
commits `tunnelReclaim: :latest` and `:665` commits `localHome: …:latest` — and the gate P1
shipped positively *requires* `tunnelReclaim` to stay floating (`plan.md:299-301`: "`tunnelReclaim`
pinned" is one of the twelve mutations that turn it red). Both images are out of this slice's scope
by G3, and D47's own `:498` already phrases the claim absolutely, so the phase widened an existing
imprecision rather than inventing one. No consumer codes against either sentence. Confidence high
on the facts.
