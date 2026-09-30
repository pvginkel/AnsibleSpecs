# P5 code review — round 1

Branch `phase/034-P5` in JenkinsPipelineUtils, `751d837..b37b8ba`. Gate: green on `b37b8ba` (`gate_r1.log`).

**Readiness.** The phase does what it set out to do, with one gap. The twelve guide pages carry every
R4 ruling and all 14 rulings-page slots: §2's `and` in LABEL-4, §3 A in GRAN, §5 (a) in POD-5,
§8 (c) with §9's exemptions in PROP-3/POST-3, §11 C in LIB-1–4, §12 (a), §13's rules, and §14 as
NEW-1–3. The four examples apply the rules I checked them against. Stage labels have their own page
next to stage granularity (R3), and the library decision test comes with the estate's cases (R5).
I ran `kc project lint` myself: all four examples answer "Jenkinsfile successfully validated." A
mutant example (`notify.warning` bare in `steps`) makes it exit 1, so the lint is not vacuous. Whole-file
and nested-section includes render with their markers stripped. That matches `lint_examples.py`'s
`published()`, so what the site shows is what the linter checked, and the Markdown copies and
`llms-full.txt` carry the example code. The gap is the plan's instruction to bring P3's reference
snippets into line: two of them still show a complete `stages {}` block that breaks CHK-1/GRAN-1
(F1). F2 and F3 are advisory.

## F1 — Two reference-page examples show a `stages {}` block whose first stage is not `Checkout` · Major · blocking · anchor: contradiction · confidence: high

- The plan requires it: `plan.md:576-578` ("Any P3 snippet that breaks a rule is brought into line
  there").
- The rule: CHK-1 (`docs/pages/guide/checkout.md:7-9`, "Its first stage MUST be `Checkout`") and
  GRAN-1 (`stage-granularity.md:12`).
- `vars/podYaml.md:7-31`: the opening example shows the agent and a complete `stages { … }`. Its
  stages are `Test` and `Validate manifests`, and there is no `Checkout`, so `npm ci && npm test`
  runs on an empty workspace.
- `vars/cicd.md:46-65`: the example shows the full standard `options {}`, which P5 added and which
  includes `skipDefaultCheckout()`. It is followed by a complete `stages {}` holding only
  `Write image pins`.

In both examples P5 treated the snippet as the file's whole block for other rules. It added
`Validate manifests` so that `k8s` has a step (POD-6), and it wrote out cicd's whole standard
`options {}` (PROP-2). Yet the first stage still breaks CHK-1. The done-record says "Reference pages
brought into line" (`plan.md:623-625`). A session that takes the `podYaml` or `cicd` page as its
model writes a file with no `Checkout` stage, in a guide the operator wants followed strictly. The
linter cannot catch this: it passes both.

## F2 — `check_site.py` catches a typed Groovy example only in a plain `` ```groovy `` fence · Minor · advisory · anchor: none · confidence: high

`docs/check_site.py:32-34`: `GROOVY_BLOCK` requires the fence line to be exactly
`` ```groovy `` plus trailing blanks. I ran the regex over five fence forms. `` ```groovy `` is caught.
`` ```groovy title="Jenkinsfile" ``, `` ``` groovy ``, `~~~groovy` and `` ```Groovy `` are not.
SuperFences highlights each of those as Groovy on the site. So Groovy typed into a guide page under
any of those fences is published without a check_site error and without the linter ever seeing it.
The done-record's "check_site.py fails on any other groovy block" (`plan.md:588-589`) and the
module docstring (`check_site.py:13-15`) state more than the check does. Today every guide block is
a plain `` ```groovy `` include, so nothing is wrong yet: it becomes a problem only when a later page
edit uses one of those fences.

## F3 — The guide's overview says every rule can be verified from the Jenkinsfile alone, but eight rules are not about a Jenkinsfile · Minor · advisory · anchor: none · confidence: high

`docs/pages/guide/index.md:8-10`: "Each is stated as a fact about a Jenkinsfile, which a reader or
a checker can verify from the file alone." NEW-1–3 (`new-repo.md:15-36`) rule how and where a job is
created. LIB-1–5 (`library.md:8-52`) rule what goes into the library. None of them is a fact about a
Jenkinsfile. Whoever writes the later conformance checker from this sentence will find those rules
untestable from a file.
