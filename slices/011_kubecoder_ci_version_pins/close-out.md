# Close-out — slice 011 kubecoder_ci_version_pins

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 011 shipped the producer side of D47 and only that. KubeCoderDeploy now carries Build-Main's
seven image pins in `config/dev/values.yaml` (build 523) and `config/prd/values.yaml` (`prd-523`);
`chart/values.yaml` names no tag for those seven and every template `required`-guards its key, so a
stage file that omits one fails to render rather than deploying something untagged. The render gate
enforces the shape — exactly the seven per stage file, one build across both, none in the chart.
JenkinsPipelineUtils gained `cicd.writeVersionPins(repo:, pins:, message:)`: one call clones a
deploy repo, rewrites the named YAML lines in every values file it is handed, and commits and
pushes them together, so no stage is left behind on the previous build. The argo-cd register,
KubeCoderDeploy's README and slice 012's slice.md were brought onto that shape.

Ruling 1 moved the Jenkins-side half — `Build-Main`'s rewrite and `Deploy-PRD`'s replacement — to
slice 012, so neither half is exercised yet: the method has no caller and the pins have no reader.
Verification was static by design. What stays owed is the operator's one canary build (A1) and, at
the cutover, the tags themselves — the registry holds neither `523` nor `prd-523` today.

## Outstanding actions

Focus: A1 first — one Jenkins build. The library is already on `main` and live for every job
that loads it, so until that build is green the push is proven only off-Jenkins. A2 is the
push of two repos the driver's branch sweep does not reach.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Re-run the Jenkins job AaC/Ansible once and hand back its console — Ruling 2's canary for the library push (verification V04)

**Do:** after JenkinsPipelineUtils `main` is at `2c43b0694cd94e66942644b9504d4690bed44f38` (the test phase pushed it), press *Build Now* on https://jenkins.webathome.org/job/AaC/job/Ansible/ and hand back the console output. The job is `Jenkinsfile.architecture` from github.com/pvginkel/Ansible: it loads the library, validates one YAML and archives it, and changes nothing. Its last build, #139, was SUCCESS in 20 s.

**Settled by:** the console reading `Loading library JenkinsPipelineUtils@main` → `Resolved main as branch main at revision 2c43b0694cd94e66942644b9504d4690bed44f38` (build #139 resolved `f8103acb0e4862b313eb6881708cd7c59ff93514`, the pre-slice head), then `Finished: SUCCESS`.

**Why it is yours:** Ruling 2 keeps the keystroke with the operator, and this pass was pre-authorized to push, not to start Jenkins builds.

**What was done first:** at that commit all seven `vars/*.groovy` compile under Groovy 2.4.21 and through groovy-cps 1.31's `CpsTransformer` (S4's note has the detail), so a syntax error or a CPS-transform rejection is ruled out. What only this build shows is that Jenkins itself loads the library.

**What stays open until it is done:** verification item V04 only; every other item is settled. If it is red, revert the offending library commits (`482706a`, `c5bf246`, `2c43b06` are the only ones this slice put there) and push — every job loads the library unpinned, so a revert is live on the next run.

**Consequence:** Until that build is green the library push is proven only off-Jenkins; a load failure that slipped past the compile checks would fail every job that loads JenkinsPipelineUtils on its next run.

**Provenance:** witnessed; test-agent, test phase r1; verification.json V04, evidence from the Jenkins API and /tmp/t011/cps_parse.groovy
**Disposition:**

### A2 — The doc phase's commits land on `main` in AnsibleSpecs and KubeCoderDeploy, outside the driver's branch sweep · minor

Only /work/Ansible carries a phase/011-docs branch; AnsibleSpecs and KubeCoderDeploy were on main, as slice 024's doc phase also found (its A5). The doc-phase edits are therefore committed on main in both: AnsibleSpecs — argo-cd/phases.md (B.2's pin location, B.3's method signature and what slice 011 committed), history.md (the D47 turn in the promotion arc, the D45 label) and decisions.md (D37's amendment narrowed to the images CI pins); KubeCoderDeploy — both stage values files' pin comment. Gates run in place: kc project lint and kc project test green in KubeCoderDeploy, and AnsibleSpecs' substitute checks (every relative link in the three changed files resolves, no changed line over 100 columns). Nothing pushed, in any repo.

**Consequence:** The driver's sweep rebase-merges and pushes only the Ansible branch, which this phase left empty — if nobody pushes AnsibleSpecs and KubeCoderDeploy, the register and the deploy repo keep the corrected text locally and the estate keeps reading the pre-011 shape.

**Provenance:** witnessed; doc phase; doc_phase_result.json
**Disposition:**

## Notable events

Focus: Nothing filed — no bail-out, no appended phase, no tool or harness trouble. What moved
this slice moved before it ran: Ruling 1 sent the Jenkins-side half to slice 012, and the three
phases then ran as planned.

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: B1 first: registry-cleanup's per-prefix cap has already deleted the build the committed
pins named, and the same cap can reach a deployed tag once Argo syncs a stage file. B2 and B3
are latent in `writeVersionPins` — no caller in 011 or 012 passes the shapes that trigger them.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — DockerImages/registry-cleanup: the per-prefix cap has already deleted the dev-511 build that KubeCoderDeploy's committed pins name · major

All seven `Build-Main` images in `KubeCoderDeploy/chart/values.yaml` pin `dev-511`. The registry
no longer holds that tag for any of them: the `dev` family runs `dev-428, dev-441, dev-443,
dev-457, dev-470, dev-479, dev-482, dev-495, dev-509` then jumps to `dev-514 … dev-523`. The nine
survivors below 514 share digests with `prd-26 … prd-36` and are held by the shared-digest guard;
`dev-511` was not promoted, so the newest-10 per-prefix cap evicted it while KubeCoderDeploy's
chart referenced it in git.

`plan.md`'s G11 frames this exposure as prd-only, un-promoted and TTL-based. The realised case is
a *dev* pin, deleted by the *cap*, with a git reference standing. Under D47 the dev stage's
deployed reference becomes exactly such a pin, and the protection D47 designs — `prd-<n>` created
at promotion, sharing a digest with `prd-latest` — covers prd only.

Two adjacent observations from the same registry read, recorded for whoever picks this up:

- Six of the seven images already carry a bare-numbered family, `175`/`176`-`185`, from a
  pre-`dev-` scheme; `kubecoder-vsix` and `kubecoder-claude-shim` carry none. D47's bare `<n>`
  family is therefore not empty for most of the set, and its cap is already full at 10.
- `prd-26 … prd-36` are the promote job's own build numbers, not image build numbers — the
  mismatch S1 records, confirmed live.

consult 1, 2026-09-20 — The realised case this entry names was P1's input, not its output: P1 re-pinned to build 523 under Ruling 4 precisely because dev-511 can never be reproduced, and the chart now pins nothing at all. The bug is unchanged and still lands on DockerImages/registry-cleanup — a git-committed pin is outside its protection set — but the exposed tags are now 523 and prd-523, which do not exist yet and which slice 012's cutover creates.

doc-writer, 2026-09-21 — Read against what shipped: the pins are 523 and prd-523, not dev-511 — Ruling 4 chose the build at phase time. The realised instance this entry names is therefore gone from the repo, and the exposure is not: the chart no longer names a tag at all, and nothing in registry-cleanup's protection set knows that a stage values file in git is a deployment reference.

**Consequence:** A git-committed deployment reference is not in registry-cleanup's protection set, so once Argo deploys KubeCoder from a stage file the pinned tag can be deleted under the cap while git still names it — the Application then fails to pull. It has already happened to the pins in the repo today.

**Provenance:** witnessed — plan-reviewer, plan review r1; http://registry:5000/v2/kubecoder-*/tags/list queried 2026-09-20, KubeCoderDeploy/chart/values.yaml:11-18,668,671, DockerImages/registry-cleanup/app/main.py:285-299
**Disposition:**

### B2 — JenkinsPipelineUtils/cicd.writeVersionPins: the round-trip guarantee in its docstring does not hold for a value YAML reads back as a number or a boolean · minor

vars/cicd.groovy:233-235 promises that a rewritten line "always parses back to the value that went in", and plainSafe (:285-293) only rejects values whose first character, or an embedded ': ' / ' #', would break plain style. A value that is legal plain YAML but resolves to another type passes: replacePin('  tag: abc', '524') returns '  tag: 524', which parses back as the integer 524, and replacePin('  tag: abc', 'no') returns '  tag: no', which go-yaml — and so Helm — reads as boolean false. None of KubeCoder's seven pins is affected: they either begin with ':' (quoted by plainSafe's first-character rule) or are whole registry:5000/... references, and all fourteen round-trip against P1's real stage files. It is the ordinary Helm pinning shape, image.tag: 524, that the claim does not cover, in a library method other apps are invited to call.

test-agent, test phase r1, 2026-09-21 — Reproduced, and the false promise itself is corrected: a rehearsal against a seeded probe file (values `524`, `true`, `null` written onto plain-style lines) read back as int, bool and None, as the entry says, while `:524`, `it's 524`, `say "hi" \ back`, `a #b` and `x: y` all round-tripped as strings. `replacePin`'s docstring no longer says a rewritten line "always parses back to the value that went in": it now says a value plain style cannot carry is quoted and parses back as the string handed in, and that a plain `524`/`true`/`null` on a plain-style line reads back as a number, boolean or null (JenkinsPipelineUtils `2c43b06`, comment only, all seven `vars/*.groovy` still CPS-compile). The behaviour question the entry raises is untouched and stays open: whether the method should quote a value YAML would re-type. Nothing in slices 011 or 012 reaches it — the five tag suffixes sit on already double-quoted lines and the two whole references are non-numeric.

**Consequence:** A future app that pins a bare numeric tag through this method gets an int where it asked for a string; a chart that renders the tag through printf "%s" emits %!s(int=524) instead of the tag. Nothing in slice 011 or 012 passes such a value.

**Provenance:** witnessed — code-reviewer, P2 review r1; phases/P2/code_review_r1.md F2, traced through a Python transcription of replacePin/plainSafe
**Disposition:**

### B3 — JenkinsPipelineUtils/cicd.writeVersionPins: the duplicate-key guard covers the values-file map but not the pins map · minor

normalizePins throws when two keys render the same values-file name (vars/cicd.groovy:154-157). One line down, :161 writes normalised[path.toString()] = value.toString() in a loop, so two distinct keys in one file's dict rendering the same dotted path collapse silently, last one wins. Witnessed under a JVM with Jenkins steps stubbed: with String c = 'controller', the literal ['images.controller': ':800', ("images.${c}"): ':801'] keeps two keys (String and GStringImpl, both rendering images.controller — map literals do not coerce, only subscript assignment does), the method commits controller: ":801" and discards :800 with no error and a success return. The docstring at :16-18 names a pin that lands nowhere as the failure this method exists to make impossible, which is precisely what :154-157 enforces one level up.

**Consequence:** A caller that names two values for one YAML path in a single file's dict has one of them silently dropped and the build reports success. No caller in slice 011 writes that shape, and neither does the call shape slice 012 inherits, so nothing in flight is affected.

**Provenance:** witnessed | code reviewer, P2, review round 2, phases/P2/code_review_r2.md F1
**Disposition:**

### ~~B4 — AnsibleSpecs/argo-cd: two of the register's new absolutes are contradicted by the chart they describe · minor~~ — resolved by consult 1 (AnsibleSpecs a4fd09c): both clauses narrowed to CI-written tags — decisions.md's D37 amendment now reads 'required-guards every tag CI writes' and design.md:511 'Every tag CI commits'; tunnelReclaim and localHome, the chart's two floating DockerImages tags, are no longer contradicted. Prose only, in files this slice's diff already touched; AnsibleSpecs has no gate, and the re-check in its place was the one P3 used — every relative link in both files resolves, no changed line over 100 columns; struck by consult 1

<details><summary>struck — body kept for the record</summary>

decisions.md:397 now says 'the chart required-guards every tag it renders'. It does not: chart/templates/controller-deployment.yaml:225 renders registry:5000/kube-coder-tunnel-reclaim{{ .Values.images.tunnelReclaim }} unguarded, and controller-config.yaml:13 ranges over list "worker" "vsix" only while controllerConfig.images.localHome rides the same toYaml dump. The plan asked for the narrower true statement (plan.md:397-398, 'the chart required-guards all seven; say that'). design.md:511-512 generalises to 'Every committed tag is a real <n> or prd-<n>, never latest', while chart/values.yaml:17 commits tunnelReclaim: :latest and :665 commits localHome: ...:latest — and P1's render gate positively requires tunnelReclaim to stay floating. Both images are out of the slice's scope by G3, and D47's own :498 already phrases the claim absolutely.

doc-writer, 2026-09-21 — The narrowing went one clause further at the doc phase: decisions.md's D37 amendment still opened 'chart/values.yaml carries no image tag', which tunnelReclaim and localHome contradict as flatly as the two clauses consult 1 fixed. It now reads 'carries no tag for the images CI pins, and the chart required-guards every one of them' — same scope as design.md:511's 'Every tag CI commits'.

**Consequence:** A reader takes 'no image tag in the chart' and 'every rendered tag is guarded' as invariants of KubeCoderDeploy's chart, when two DockerImages images in it are committed at :latest by design and the gate requires one of them to stay that way.

**Provenance:** read; code review, P3 round 1; phases/P3/code_review_r1.md (F3)
**Disposition:**

</details>

## Open questions and rulings

Focus: Nothing open. The rulings that shaped the slice were all made at plan time, and the one
question a phase raised — how wide the register's new absolutes should be — was settled by
consult 1 and is struck as B4.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: S5 first — slice 012 would otherwise learn it the hard way: values are written verbatim,
so the five dev pins need their leading colon, and the caller needs `disableConcurrentBuilds()`
and `git` in its container. S1, S2 and S6 are slice 012's too; S3, S4 and S7 outlive it.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — Deploy-PRD numbers its prd-<n> tags with the promote job's build number; D47 numbers them with the image build's · minor

`Jenkinsfile.deploy-prd:33-38` retags `dev-${sourceDevBuild}` to `prd-${currentBuild.number}` — the promote job's own build number, in a numbering space unrelated to Build-Main's. D47 pre-writes `prd-<n>` into the prd stage values file at build time, where `<n>` is the image build's number, and has the promote job create exactly that tag. Slice 012's replacement therefore changes numbering space, not just mechanism, and the `prd-*` tags already in the registry belong to the old space. This slice writes `prd-511` into the prd stage file as its first forward reference.

doc-writer, 2026-09-21 — The prd stage file shipped with prd-523, not prd-511 (Ruling 4). The numbering-space point is unchanged — the forward reference names Build-Main's build number, and Deploy-PRD's own.

**Consequence:** If slice 012's promote job keeps the old numbering, it creates a tag nothing references while the stage file's prd-<n> stays unpullable — and the sync fails on an image that does not exist, which is exactly the loud-and-local failure D47 designed for, landing for the wrong reason.

**Provenance:** read — plan-writer, plan pass r1; /work/KubeCoder/Jenkinsfile.deploy-prd:33-38, argo-cd/decisions.md:493-498
**Disposition:**

### S2 — The pins this slice writes are forward references: slice 012 must build before it points Argo at KubeCoderDeploy · minor

P1 leaves `config/dev/values.yaml` naming build 511's bare tag and `config/prd/values.yaml` naming `prd-511`; the registry holds `dev-511` and neither of the two. Nothing creates them until a Build-Main run under the new scheme (slice 012, Ruling 1). Nothing consumes the repo today (G7), so the gap is inert — but it is an ordering constraint on the cutover, not a defect to fix here.

consult 1, 2026-09-20 — Numbers superseded by Ruling 4 and P1: the stage files name build 523, not 511 — dev '523', prd 'prd-523' — and the registry holds dev-523 but neither 523 nor prd-523 (dev-511 is gone entirely, see B1). The substance is unchanged and is what slice 012 inherits: both written tags are forward references, so the cutover must create them before the first dev sync. Slice 012's slice.md carries this as its own bullet under 'Carried in from slice 011'.

**Consequence:** A dev Application created before the first cutover build syncs to an image tag that does not exist and fails to pull; sequencing the build ahead of the Application avoids it entirely.

**Provenance:** read — plan-writer, plan pass r1; KubeCoderDeploy/chart/values.yaml:11-18,668,671, plan.md G7 and Ruling 1
**Disposition:**

### S3 — HelmCharts: the gitToken PAT rides the helm command line for all 45 releases, and only version-poller consumes it · minor

`argo-cd/design.md` records it, and slice 011's `slice.md` carried it into planning "so it isn't
lost", asking the planner to decide deliberately because `version-poller` is one of requirement
3's tag-prefix readers:

> **`gitToken` travels as a helm CLI argument for all 45 releases**; only `version-poller`
> consumes it. It must become an ESO leaf when version-poller migrates — Argo has no such
> argument to inject — and a PAT on a command line lands in process tables and echoed commands
> regardless.

**The decision (Ruling 7, operator, 2026-09-20): out of scope for slice 011.** `design.md`
assigns the fix to the version-poller migration, and nothing in slice 011 touches the helm
invocation that carries the argument — the slice moves image tags between values files in
KubeCoderDeploy and adds a library method. Recorded here so the item survives the slice rather
than closing with it.

**Consequence:** A GitHub PAT is visible in process tables and echoed commands on every one of 45 release deploys, to serve the one release that needs it; nothing changes until version-poller migrates and the token becomes an ESO leaf.

**Provenance:** read, plan-writer r2 (review fix pass) — Ruling 7 in plan.md; carried in slice.md's source material from argo-cd/design.md
**Disposition:**

### S4 — JenkinsPipelineUtils could have a real Groovy parse gate: a JVM is obtainable in this environment after all · minor

G2 and Ruling 2 both rest on "nothing in this environment can check Groovy". That is true of the
containers as they stand — `java` and `groovy` are absent here and in the `iac`, `go` and
`aac-tools` sidecars — but not of the environment: `https://api.adoptium.net` and
`repo1.maven.org` are both reachable, and a portable Temurin 17 JRE plus `groovy-all-2.4.21.jar`
(the Groovy version workflow-cps compiles) is a ~54 MB unprivileged download into `/tmp` that needs
no root. This round used exactly that to witness F1 and to verify the fix — `CompilationUnit` at
`Phases.CONVERSION` parses all seven `vars/*.groovy`, and the method body runs off-Jenkins against
real values files with the Jenkins steps stubbed in ~40 lines of Groovy.

Two things that would follow, neither this slice's work: a `.kubecoder/project.yaml` for
JenkinsPipelineUtils whose test entry point parses every `vars/*.groovy`, which turns the
estate-wide failure mode into a pre-push gate; and, further out, the real CPS transform
(`com.cloudbees:groovy-cps`) to catch the serialization hazards a parse cannot see. The parse gate
is the cheap half and catches the one failure that reaches other jobs.

test-agent, test phase r1, 2026-09-21 — The "further out" half was run before the push, and it works in this environment. Adding `com.cloudbees:groovy-cps:1.31` (the latest on repo1.maven.org), `guava-11.0.1` and `groovy-sandbox-1.19` (about 1.9 MB more, the same unprivileged download into `/tmp`; `jenkins.model.Jenkins` stubbed so `utils.groovy` resolves) to the JRE 17 + `groovy-all-2.4.21` classpath, all seven `vars/*.groovy` compile through `CpsTransformer` set up the way workflow-cps sets it (a star-import of `com.cloudbees.groovy.cps`, then the transformer as a compilation customizer). Two controls show the check can fail: a transformed method throws `CpsCallableInvocation` when called outside the engine, and a `synchronized` block is rejected with `synchronized is unsupported for CPS transformation`.

One correction to what the entry expects of it: the transform compile catches constructs the transformer refuses, at load time. It does not catch the serialization hazards a resumed build trips on (`NotSerializableException` shows up only when a build resumes), which still need reading. The scratch scripts (`/tmp/t011/cps_parse.groovy`, `harness.groovy`) are ephemeral; the compile check is about 25 lines and would be the body of the test entry point the entry proposes.

**Consequence:** Every change to the shared library ships on reading alone, and a syntax error in any vars/*.groovy breaks every job in the estate on its next run — the failure mode Ruling 2's canary exists to catch after the fact rather than before.

**Provenance:** witnessed | code-writer, P2, review round 2 — /work/AnsibleSpecs/slices/011_kubecoder_ci_version_pins/phases/P2/code_review_r1.md F1
**Disposition:**

### S5 — Slice 012 is not told that writeVersionPins writes values verbatim, nor that Build-Main needs disableConcurrentBuilds() and git in its container · major

P2 handed both constraints to P3 (plan.md:350-355) and neither reached the register or slice 012's slice.md. D45 as rewritten (argo-cd/decisions.md:469-476) gives the map's shape and no value semantics; slice 012's call description (slices/backlog/012_kubecoder_argo_cutover/slice.md:126-134) says only 'with <n> for config/dev/values.yaml and prd-<n> for config/prd/values.yaml'; the 'Carried in from slice 011' section (:360-401) carries the five grounding bullets Ruling 5 named and neither of these. The five images.* pins are tag suffixes — config/dev/values.yaml:29 holds controller: ":523" and chart/templates/controller-deployment.yaml:46 concatenates onto registry:5000/kubecoder-controller — so a caller handing '524' instead of ':524' renders registry:5000/kubecoder-controller524, which the required guard accepts. KubeCoderDeploy carries no Jenkinsfile, so nothing re-runs the render gate between a CI-written pin commit and Argo's sync. /work/KubeCoder/Jenkinsfile declares no properties([...]) block, so Build-Main has no disableConcurrentBuilds() today. cicd.groovy:29-33 does carry both rules in the method's docstring, which is what the author of the call will be reading.

consult 1, 2026-09-20 — Judged against the generation bar and left here rather than appended. It is real and it is plan-described — P2's later-phase note (plan.md, under P2) addressed both constraints to P3, and P3 carried six grounding bullets into slice 012's 'Carried in from slice 011' section and neither of these. It does not clear the bar because Ruling 5, which is what the plan actually owes slice 012, enumerates what to carry (R2 verbatim, G5/G6/G8/G10/G12, the corrected Depends on line) and all of it landed; and because the constraints are not lost: vars/cicd.groovy:22-31 states all three in the method's docstring — git on PATH, 'a caller declares disableConcurrentBuilds()', and 'Values are written verbatim' with ':524' as the worked example — which is what the author of the call reads. A phase for three sentences of prose costs an executor round, a review round and another consult; this costs one word. The remediation, if the operator folds it into 012: one bullet in that section saying the five images.* pins are tag suffixes, so the caller supplies the leading colon (':524', not '524'), and one saying Build-Main needs disableConcurrentBuilds() and git in its container.

**Consequence:** If slice 012 writes the Build-Main call from its own slice.md, the five image pins land without their leading colon and the dev cutover fails on an invalid image reference; and two concurrent builds lose the race on the second pin push.

**Provenance:** read; code review, P3 round 1; phases/P3/code_review_r1.md (F1)
**Disposition:**

### S6 — Slice 012's requirement 14 stages Deploy-PRD's replacement at prd's cutover, which leaves prd unpromotable between the two flips · minor

The lede added at slices/backlog/012_kubecoder_argo_cutover/slice.md:116-117 reads 'each applied at the moment its stage flips, Build-Main's rewrite at dev's cutover, Deploy-PRD's replacement at prd's'. The G5 bullet carried into the same document at :369-375 states the opposite requirement: 'even at the dev cutover the prefix cannot simply vanish, because prd flips later and promotion must keep working from the bare <n> in between'. At dev's flip Build-Main stops pushing dev-<n>, while the surviving Deploy-PRD retags registry:5000/kubecoder-<name>:dev- (/work/KubeCoder/Jenkinsfile.deploy-prd:33-38) — a tag no new build produces. Nothing in the document names what promotes to prd in that window. Ruling 1 says only 'applied at the moment each stage flips, staged per stage'; the per-job assignment is the phase's gloss.

consult 1, 2026-09-20 — The tension is in Ruling 1, not in P3's gloss of it: the operator's ruling stages the two Jenkins artefacts 'at the moment each stage flips', and G5 — verified in the same session — says the dev- prefix cannot simply vanish at dev's cutover because promotion must keep working from the bare <n> until prd flips. Both texts now sit in slice 012's own slice.md (requirement 14's lede and the carried-in G5 bullet), so its planner meets the question rather than inheriting a silent gap. Settling what promotes to prd in the window between the flips is slice 012's planning decision, not work slice 011 owes.

**Consequence:** A slice-012 plan written from requirement 14's lede schedules no promotion work at the dev cutover, and prd cannot be promoted for any build made between the dev and prd flips.

**Provenance:** read; code review, P3 round 1; phases/P3/code_review_r1.md (F2)
**Disposition:**

### S7 — slices/DAG.md still files the /work/KubeCoder gate constraint, and a KubeCoder + HelmCharts repo set, under 011 · minor

DAG.md:31 lists 011's subprojects as JenkinsPipelineUtils, KubeCoder, KubeCoderDeploy, HelmCharts — Ruling 1 moved the Build-Main edit to 012 and G4 took HelmCharts out of the slice entirely. DAG.md:74-77 heads the constraint 'Not a gate, but a constraint on 011' and mentions 012 only in its closing sentence, about the pull-policy removal rather than Build-Main. The doc phase does not hand-edit DAG.md: its own header says to re-run /dev:slice-dag after slices land, and the inventory section says re-runs reuse cached rows for slices already listed, so the stale 011 row survives a regeneration unless it is invalidated.

**Consequence:** Slice 012's planner reads the '/work/KubeCoder cannot gate here' constraint as slice 011's, with its own Build-Main rewrite named only in passing, and can schedule a run-loop phase against a repo whose gate this environment cannot run.

**Provenance:** read; doc phase; /work/AnsibleSpecs/slices/DAG.md:31,74-77
**Disposition:**
