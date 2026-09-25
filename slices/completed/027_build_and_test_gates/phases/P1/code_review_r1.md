# P1 code review — round 1

Range: JenkinsPipelineUtils `062b106..e7f51bc` on `phase/027-P1`.

**Readiness: ready to merge.** The gate delivers the phase outcome and every P1 acceptance
criterion.

- **V01, pin and provenance.** `dependency:tree` resolves groovy-cps `4376.v30c8c00684a_3`,
  guava `33.4.8-jre` (arriving transitively), groovy-all 2.4.21 and groovy-sandbox 1.34.1. Nothing
  else is on the classpath apart from JUnit. Central's 1.31 is not there, and no hand-downloaded
  runtime is used.
- **V01, trusted shell.** The shell matches `CpsGroovyShellFactory` at the tag, which I fetched
  and compared:
  - `new CompilerConfiguration()` with no sandbox;
  - star imports for `com.cloudbees.groovy.cps`, `hudson.model` and `jenkins.model`;
  - a plain `CpsTransformer` with a safepoint;
  - `GroovyShellDecorator.forTrusted()` returns `NULL`.
- **V02 and V03, witnessed independently.** No gate is recorded green for this commit, so I
  probed it myself. I ran `cexec java mvn -B -f tests/pom.xml test` in a scratch worktree of
  `e7f51bc` with two new, unregistered `vars/` files added:
  - 12 cases ran;
  - the seven real `vars/*.groovy` files and the three controls passed;
  - `zzProbeSync.groovy` went red with "synchronized is unsupported for CPS transformation";
  - `zzProbeSyntax.groovy` went red with "unexpected token".

  With the probes left out, the branch's own ten cases are green.
- **V04.** The gate's files are all under `tests/`, `.kubecoder/` and `.gitignore`. After the run,
  `git status --ignored` shows `tests/target/` as ignored.
- **V15.** The pin is one `<properties>` block, and its comment names the controller's
  workflow-cps.
- **Plan edit.** The executor's edit to P3's text only spells out the one-off check that P3
  already named. It does not widen scope.

One advisory gap remains, from the stand-in base class.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high on the mechanism, low on it ever mattering

**The stand-in script base class does not mark `invokeMethod` final. `CpsScript` does, so the gate
passes a `vars/` method that the controller refuses at compile time.**

- **Controller side.** The controller compiles every library script with base class `CpsScript`,
  which declares `public final Object invokeMethod(String name, Object args)` (workflow-cps
  `4376.v30c8c00684a_3`, `plugin/src/main/java/org/jenkinsci/plugins/workflow/cps/CpsScript.java:92`).
- **Gate side.** The gate sets `SerializableScript` as the base class
  (`tests/src/test/java/org/webathome/jenkinspipelineutils/LibraryCompileTest.java:48`). That class
  inherits `groovy.lang.Script`'s non-final `invokeMethod`.
- **Result.** Suppose a `vars/*.groovy` file declares `def invokeMethod(String name, Object args)`.
  The gate is green. On the controller, Groovy's class-completion check rejects the override of a
  final method when the library loads, and every job that calls the library breaks.
- **Why advisory.** No file in `vars/` declares that method, and the plan accepts plugin-class
  stand-ins. The only other difference between `CpsScript` and `SerializableScript` is the
  package-private `$initialize`, which a script cannot override by accident. This entry records
  the one known false-green of the stand-in approach. It is not fix work.
