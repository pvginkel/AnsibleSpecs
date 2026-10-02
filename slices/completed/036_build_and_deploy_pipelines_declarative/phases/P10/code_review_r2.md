# P10 code review — round 2

Range: KubeCoderConfig `4cdca35..890da41` (`phase/036-P10`), one commit.

**Readiness.** Round 1's one blocking finding is resolved, and the fix commit introduces nothing
new. The phase may merge.

**F1 (round 1) — resolved.** The skill's SEC-1 brief
(`kubecoder/skills/jenkins-pipelines/SKILL.md:112-115`) now reads "never around `pipeline {}`, the
agent, the checkout, a lint or a test, except the one step that runs a test which itself needs the
secret (SEC-1)". I checked this against three sources:

- **The guide.** It matches the exception in JenkinsPipelineUtils `docs/pages/guide/secrets.md:11-14`
  (in `02989a1`, unchanged on local `main` `521fac6`): "`withVault` MAY wrap the step that runs that
  test, and nothing else".
- **Ruling P3.** It matches the ruling's scope (`plan.md:123`): around only the step that runs that
  test.
- **IoTSupport's file.** That file, `IoTSupport/Jenkinsfile:41-55` (`9748ca1`), now conforms to the
  brief. Its `withVault` sits inside the Test stage's `steps`/`script` and wraps only the
  `modernApp.test(...)` call.

No other line in `kubecoder/` projects SEC-1 or `withVault`, so the brief is the only copy that had
to change.

**The fix commit itself.**

- It touches only that bullet and `plugin.json`.
- The version goes from 0.10.1 to 0.10.2. That is a patch bump in the same commit as the skill
  edit, as KubeCoderConfig's `CLAUDE.md` requires. At the branch's merge base the version is
  0.10.0.
- I ran `kc project lint` (Prettier `format:check`) on `890da41`, and it is green.
- `kc project test` defines no tests, so the test gate is unverified. This bears on nothing here:
  the change is prose, and the lint gate covers what can be checked mechanically.

No findings.
