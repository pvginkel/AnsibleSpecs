# Code review — slice 033, phase P1, round 1

Range: JenkinsPipelineUtils `276beff..9cbbad9` (`phase/033-P1`).

**Readiness: ready to merge.** The pin is right. `tests/pom.xml:18` is `4383.v04fa_a_3d67b_d9`, and a
live read of the controller's `/pluginManager/api/json` today returns the same `workflow-cps`
version. The cached 4383 groovy-cps pom declares the same `groovy` 2.4.21 (provided),
`groovy-sandbox` 1.34.1 (optional) and `guava` 33.4.8-jre as 4376's, so the pom's other versions
and its comment still hold. `VersionPinsTest` and `AlertEscapeTest` check behaviour, not smoke
calls. `applyPins` is checked against a full byte-for-byte expected file: comments, a
mapping-with-comment parent, `|`/`>` bodies that look like YAML, a same-named key under another
parent, the no-op re-pin and the missing final newline. Every refusal is checked by its exact
message. `replacePin` is checked across all three quoting styles, escapes included, and
`plainSafe` across each class of value its comment names. `escape` is checked for the backslash
ordering. I ran two mutations of my own that the executor did not claim: removing the
path-on-two-lines refusal, and dropping single-quote doubling in `replacePin`. Each turned
`VersionPinsTest` red (`aPathOnTwoLinesIsRefused`, `replacesOnlyTheScalar[22]`). The tree was
restored afterwards. `LibraryCompileTest` and `TrackingTagTest` are untouched (V12), and no
dependency was added.

The executor saw that `applyPins` writes into a sequence entry's second key. That is a problem in
the existing code, not in this diff, and it is already close-out B1. The `env` fixture
(`VersionPinsTest.java:47-48`) keeps to the first-key case, which is refused correctly, and no
test pins the defective behaviour in place. The missing `normalizePins` tests are already
close-out T1.

## Findings

### F1 — The gate's comments say every `@NonCPS` function has behaviour tests; two have none · Minor · advisory · anchor: none · confidence: high

Both `tests/pom.xml:5-6` ("asserts the behaviour of its @NonCPS functions") and
`.kubecoder/project.yaml:13` ("asserts the behaviour of the @NonCPS functions") claim tests for
every `@NonCPS` function. `cicd.normalizePins` (`vars/cicd.groovy:155`) and
`helmCharts.rebuildAtIso` (`vars/helmCharts.groovy:202`) are `@NonCPS` and no test calls either
one (`grep` over `tests/src` finds neither name). A maintainer who trusts the comment could change
`normalizePins`, see the gate stay green, and take that as covered, which is the case T1
describes. Nothing breaks today; the text is wrong, and that is all.
