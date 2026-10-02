# P10 code review — round 1

Range: KubeCoderConfig `e04701c..4cdca35` (`phase/036-P10`).

**Readiness.** The phase delivers its named outcome. The paragraph "Two files predate the guide, on
purpose" (`kubecoder/skills/jenkins-pipelines/SKILL.md:31-48`) checks out against the repos:

- ModernAppTemplate's `root/template/Jenkinsfile.jinja` is a scripted `podTemplate`/`node` file
  that calls `containerTemplates.k8s` (`:6`) and the positional `helmCharts.kaniko` (`:195`,
  `:206`).
- The five apps' `Jenkinsfile` are declarative and call `modernApp.test`.
- The `types/modern-app` page exists in JenkinsPipelineUtils (`mkdocs.yml:114`).
- KitchenDisplay's `Jenkinsfile` calls exactly `containerTemplates.dockbuild`/`rsync`,
  `gitUtils.getTreeHashFile` and `helmCharts.ssh`/`rsync`. Its `Jenkinsfile.architecture` is
  declarative, and `Firmware/KitchenDisplay` is disabled in the job dump.

The onboard skill names `kaniko2` at all four places. `:1676` uses the named-argument form, which
matches `kaniko2`'s `dockerfile:`/`context:` arguments (`vars/helmCharts.groovy`). The plugin bump
is a patch (0.10.1) and the `youtrack-usage` rewrap changes no words.

`kc project test` defines no tests, so the test gate is unverified. I ran the plan's gate,
`kc project lint` (Prettier `format:check`), on `4cdca35`, and it is green.

One blocking finding remains. The plan's P10 section checks that the skill's rule lines stay true
after the slice: it records that the LIB-6 line "stays true" (plan `:979-980`). The SEC-1 line does
not stay true, and the phase left it as it was.

## F1 — Major · blocking · anchor: contradiction · confidence: high

**The skill's SEC-1 brief still bans `withVault` around a test. Ruling P3 gave SEC-1 an exception
for a test that needs a secret, and this slice relies on it in IoTSupport's file.**

Evidence:

- `kubecoder/skills/jenkins-pipelines/SKILL.md:112-114`: "`withVault` … never around `pipeline {}`,
  the agent, the checkout, a lint or a test (SEC-1)."
- Plan Ruling P3 (`plan.md:123`, with P3's section at `:507-510`): "SEC-1 gains one narrow
  exception … a test that itself needs a secret may run with `withVault` around only the step that
  runs that test". JenkinsPipelineUtils `docs/pages/guide/secrets.md:11-14` (local `main`,
  `02989a1`) now states this exception.
- The slice's own IoTSupport file uses the exception: `IoTSupport/Jenkinsfile:41-51` (`9748ca1`)
  wraps `modernApp.test` in `withVault` inside `stage('Test')`.
- The skill's opening, `SKILL.md:11-13`, says a file that breaks one of the guide's rules "is wrong,
  whatever else it gets right".

Failure (repro trace):

1. After the one-go push, a session loads `jenkins-pipelines` to review or edit
   `IoTSupport/Jenkinsfile`.
2. It holds the Test stage to the skill's SEC-1 brief. The brief says SEC-1 forbids `withVault`
   around a test, and the skill exists to tell the session "what to hold a file to"
   (`SKILL.md:14-15`).
3. The session reports a SEC-1 violation in a file this slice migrated to the guide. If it acts on
   the report, it moves the secret out of the Test stage, and IoTSupport's suite loses the Keycloak
   admin client it needs (Ruling P3's premise).

The skill is the slice's one projection of the guide's rules into agent context. This phase is the
slice's only edit of the skill. The slice pushes once (R18), so a fix found after the test phase's
push needs a new push.
