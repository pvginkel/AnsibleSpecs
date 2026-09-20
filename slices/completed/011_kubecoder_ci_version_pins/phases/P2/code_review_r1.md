# P2 code review — round 1

`git diff f8103ac..482706a` on `phase/011-P2` in `/work/JenkinsPipelineUtils`: one commit,
one file, +295 lines, `vars/cicd.groovy`.

## Readiness

The phase's outcome is there and the shape is right: `cicd.writeVersionPins(repo:, pins:,
message:)` sits beside `helmDeploy()`, `pins` carries the whole set of values files one call
must move (V01), the rewrite is surgical and idempotent, an unknown or duplicated YAML path
throws before anything is committed, an unchanged run commits and pushes nothing and says so
(V02), and the credential follows `HomelabTerraformProvider/Jenkinsfile:82-95` exactly — shared
username/password, shell-expanded under `set +x`, a repo-local git identity, and a push that
reuses the clone's remote (V03). I transcribed `applyPins`/`replacePin` to Python and ran it
against P1's real `config/{dev,prd}/values.yaml`: exactly the seven lines change per file, the
rest of both documents is byte-identical, a re-run changes nothing, a pin-shaped decoy inside a
`|` block scalar is not touched, and missing/duplicate paths raise. Two things bear on the
verdict. First, **the branch's test and lint state is unverified** — this repo has no gate and
this environment has no JVM (`which java groovy` is empty, G2 holds), so nothing has compiled
this file and review is the only net, as Ruling 2 says. Second, and the reason this is not a
signoff: the executor's stand-in verification was a *Python* transcription, and Python cannot
reproduce the one Groovy semantic this method turns on — that a `GString` key and a `String`
key are different map keys. The method defends the inner map against exactly that (`:148-152`)
and then reintroduces it on the outer map at `:98` (F1).

## Findings

### F1 — `pins[file]` at `:98` looks the values-file map up with a coerced `String`, after `:52` looked it up with the caller's raw key

- **Severity** Major · **Impact** blocking · **Anchor** repro-trace · **Confidence** high

`vars/cicd.groovy:49` keeps the caller's own key objects: `pins.keySet() as List` erases the
`List<String>` hint and coerces nothing. `:52` therefore probes `pins[files[i]]` with the raw
key and hits. `:88` then declares `String file = files[i]`, which *does* coerce — assigning a
`GString` to a `String`-typed local converts it — and `:98` looks up `pins[file]` with the
converted `String`.

`groovy.lang.GString.hashCode()` is `37 + toString().hashCode()` and its `equals` returns false
for anything that is not a `GString`; this is the gotcha the file itself documents twelve lines
further down, at `:148-150` ("A GString key hashes unlike the String path built from the file"),
where the *inner* map is defended with `path.toString()`. The outer map gets no such defense,
and nothing in the docstring (`:27-31`) constrains the key type.

Failure: a caller that builds the dict with an interpolated path —
`['dev','prd'].each { s -> pins["config/${s}/values.yaml"] = [...] }`, which is the natural way
to write a two-stage dict whose stages differ only by prefix — passes the `:51-55` emptiness
check, clones, passes `fileExists` at `:91`, and then reaches `applyPins(file, before, null)`.
The pins for that file are never applied. `applyPins` immediately calls `pins.each` on the null
at `:152`, so the build dies inside a `@NonCPS` method on a null map instead of being told its
key is wrong; and if Groovy's null dispatch treats that as an empty iteration instead, the
method falls through to `:106-107` and reports "already carries these pins: nothing committed,
nothing pushed" on a build that wrote nothing — the pin that lands nowhere, which `:17-18`
states this method exists to make impossible. Both outcomes are the defect; the traced part is
that the `:98` lookup returns null.

The symmetric reading does not rescue it: if `as List` at `:49` *did* coerce its elements, then
`:52` would miss instead and the same caller would be told "`config/dev/values.yaml` names no
pins" about a file it plainly named. One of the two lookups is wrong whichever way the coercion
falls; they cannot both be right, because they are spelled differently.

Bears on the unverified state: no compiler and no JVM here, and the Python transcription the
executor ran in their place has no GString/String distinction to reproduce, so this class of
defect was outside what that verification could see.

### F2 — the round-trip guarantee at `:233-235` does not hold for a value the line's plain style renders as a non-string

- **Severity** Minor · **Impact** advisory · **Anchor** repro-trace · **Confidence** high

`:233-235` promises "what comes back always parses back to the value that went in", and
`plainSafe` (`:285-293`) rejects only values whose *first* character or embedded `: ` / ` #`
would break plain style. It admits values whose plain rendering YAML resolves to another type.
Traced through the transcription: `replacePin('  tag: abc', '524')` returns `  tag: 524`, which
a YAML parser reads back as the integer `524`, not `"524"`; `replacePin('  tag: abc', 'no')`
returns `  tag: no`, read back as boolean `false` under the YAML 1.1 rules go-yaml (and so
Helm) applies.

No product consequence in this slice: all seven of KubeCoder's values either begin with `:`
(double-quoted by `plainSafe`'s first-character rule, and their lines are double-quoted already)
or are whole `registry:5000/...` references, and every one round-trips — I checked all fourteen
against the real stage files. It matters only because the claim is stated as a general property
of a library method other apps are invited to call, and the ordinary Helm pinning shape
(`image.tag: 524`) is the case it does not cover.
