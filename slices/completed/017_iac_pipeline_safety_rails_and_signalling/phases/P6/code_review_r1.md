# P6 code review — round 1

Range `b681222e..1352e68c` on `phase/017-P6` (`Jenkinsfile.iac-scheduled-certs`,
`Jenkinsfile.iac-scheduled-drift`).

**Readiness: ready to merge, no findings.** The phase meets its outcome. Every prd stage in both jobs
now goes through a helper: certs `prdStage` (:67-79), drift `prdCheck` (:163-171). The helper runs
`sh(returnStatus: true)` outside `catchError`. Only on a non-zero exit does it append that stage's
entry (certs uses `\n`; drift's `recordDrift` appends and now returns the entry, :142-152), then
calls `error()` inside `catchError(buildResult: 'FAILURE', stageResult: 'FAILURE')`. So a failed prd
stage turns the stage and the build red, and the later stages still run. An abort still propagates
from the `sh`, and no Jenkins `timeout()` was added. Stage-level `post { failure }` is gone, so a
passing stage adds nothing to a build that is already FAILURE. The misleading "TLS leaf renewal did
not run" is gone too. A dev stage that genuinely fails calls `notify.warning` right there, then
`unstable()`: certs :142-146 and :206-210, drift :294-298 and :352-356. A powered-off srvk8sdev still
only calls `unstable()` (certs :128-131, :192-195; drift :278-281, :336-339). `DEV_STAGE_FAILED` and
both job-level `post { unstable }` blocks are deleted, and no fallback description was added (R4
ruling).

What I verified rather than took on trust, given that the gate is vacuous for these files (close-out
N1):

- **The files load as Groovy.** I downloaded Temurin 11 and `groovy-all-2.4.21` (Jenkins' Groovy
  line). Both new Jenkinsfiles and both base versions pass `CompilationUnit.compile(Phases.CONVERSION)`.
  As a control, a copy of each with one delimiter broken fails to parse (certs: a `'''` closer cut to
  `''`; drift: a `}` removed). This rules out a syntax-level load failure. CPS, sandbox and
  declarative-model validation are still proven only by a build.
- **The shell bodies are unchanged apart from indentation.** Ignoring whitespace, the diff leaves
  only the removed `sh '''`/`sh """` openers and closers. Neither file has trailing whitespace, so
  the CA-root `\` line join (drift :386) still joins inside the `'''` literal as before.
- **The warning survives a later red build.** `jenkins-telegram-bot` calls `_raise_alerts` for every
  final build whatever its status (`app/bot.py:136-137`). It matches markers anywhere in a line
  (`app/alerts.py:19-20`, `.search`), so the `timestamps()` prefix does not hide them. It is loud only
  for FAILURE (`app/bot.py:25`), which bears out the new comments' "UNSTABLE the bot stays quiet
  about".

V12–V16 stay owed to the next scheduled runs, as the plan states.

## Findings

None.
