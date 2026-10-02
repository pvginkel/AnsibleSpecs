# P3 code review, round 2: the secrets handoff fix

Range: JenkinsPipelineUtils `02989a1..521fac6` (`phase/036-P3`, one commit). The rest of the branch
was reviewed in round 1 and is context only.

**Readiness: r1 F1 is resolved, and nothing blocking is left. Ready to merge.** `secretsScript`
(`vars/modernApp.groovy:156-171`) no longer pipes `NAME=value` lines into `kubectl set env -e -`.
It passes each secret to kubectl as an argument (`:167-169`), and kubectl takes everything after the
first `=` as the value. I extracted the script from the commit and ran it in the production shell,
busybox ash (`sh -xe`, as the sh step runs it), against real kubectl v1.35.9. One value held `#`, a
backslash-newline, `line2=oops`, backticks, `$HOME` and two trailing newlines. It reached the
`validation` container's env byte for byte. A leading `-` in the client id reached it too. The
service container gained no env. stderr held only `+ set +x`. An unset variable failed with exit 1,
named the variable, and applied nothing. An empty value applied as an empty variable. The
`$(printenv … && echo .)` / `${value%?.}` pair keeps trailing newlines, as `:153-154` says.

The two new tests are not vacuous. I ran `ModernAppTest` against two mutations in a scratch clone.
Without `set +x`, `eachSecretReachesTheJobWholeAndStaysOutOfTheTrace` fails at `:308`: the trace
leaks the value. With plain `$(printenv "$name")`, the same test fails at `:302`: the trailing
newlines are lost. Those tests run under the java container's dash, while production uses busybox
ash; the run above covers that difference. Calling the step is unchanged: `withEnv` sets the
names, and `sh secretsScript()` holds no value, so SEC-4 holds and the step page's claim at
`vars/modernApp.md:114-117` is still true. The value is now in kubectl's argv for the moment
`set env --local` runs. SEC-4 does not cover argv, and the same process environment already holds
the value. That is not a finding.

## F1 — Minor · advisory · anchor: none · confidence: high

**The step page's Internals list leaves out the new helper.** `vars/modernApp.md:141-143` names
the var's helpers that are "not part of what `modernApp` offers a Jenkinsfile". It lists
`testArguments`, `service`, `environment`, `envList`, `jobManifest`, `suiteScript` and `summary`.
`secretsScript` (`vars/modernApp.groovy:157`), added in this round, is missing. Every other var
page with an Internals section lists all its helpers (`vars/espFirmware.md`,
`vars/architectureProducer.md`). Close-out P2 is the mirror case on `podYaml.md`. No product
consequence: no Jenkinsfile calls the helper.
