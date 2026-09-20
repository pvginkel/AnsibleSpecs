# P2 code review — round 2

`git diff 482706a..c5bf246` on `phase/011-P2` in `/work/JenkinsPipelineUtils`: one commit, one
file, +43/−12 in `vars/cicd.groovy`. Nothing else on the branch changed.

## Readiness

Round 1's one blocking finding is resolved, and this round I ran the code rather than reading it.
The executor left a usable JVM behind (`/tmp/jvm`: Temurin 17 JRE and `groovy-all-2.4.21`, the
version workflow-cps compiles — close-out S4), so I parsed `vars/cicd.groovy` **unmodified** with
`com.cloudbees.groovy.cps.NonCPS` as a default import and a base script class stubbing `error`,
`echo`, `sh`, `pwd`, `fileExists`, `readFile`, `writeFile`, `usernamePassword`, `withCredentials`
and `withEnv`; `sh` really runs bash, and the clone and push reach a local bare repo seeded from
P1's real `config/{dev,prd}/values.yaml` through a `url.<path>.insteadOf` rewrite of the exact
credentialed GitHub URL. Same harness, two commits:

- **F1 is fixed, witnessed both ways.** Against `482706a` the round-1 caller — a map literal whose
  values-file keys are interpolated — fails with `cicd.writeVersionPins: config/dev/values.yaml
  names no pins` about a file it plainly named, and writes nothing. That is F1's symmetric branch,
  reproduced exactly. Against `c5bf246` the same caller writes all fourteen pins and pushes one
  commit. The premise the new comment states (`:140-144`) is also true as written: a `GString` key
  stored by a map *literal* is reachable by no subscript at all — `m[theStoredKeyObject]` returns
  null, only `.get()` hits — while subscript *assignment* coerces, which is why the two spellings
  diverge.
- **The `wanted` → `pins` rename in `applyPins` broke none of its guards.** An unknown path throws
  before anything is committed (and the remote's commit count is unchanged after it); a path the
  file holds twice throws naming both lines; a pin-shaped decoy inside a `|` block scalar is left
  alone while the real pin is written; an empty dict, an empty inner dict and a values file the
  repo lacks all error.
- **V02 end-to-end on P1's real stage files:** exactly 7 insertions and 7 deletions in each of the
  two files and no third file, `README.md` in the deploy repo untouched, one commit on the remote,
  all fourteen values round-tripping through a YAML parser as strings, and a re-run echoing
  `already carries these pins: nothing committed, nothing pushed` with a null return.
- **V03** is untouched by this commit and still holds: no echo carries the token.

On the gate: this repo has no gate (Ruling 2), so the branch's lint and test state is formally
unverified and nothing below rests on a suite. As a stand-in for the estate-wide failure mode
`vars/*` compiling together, all seven `vars/*.groovy` parse under `groovy-all-2.4.21`
(`utils.groovy` needs `jenkins.model.Jenkins` on the classpath; with it stubbed, it parses). That
is a parse check, not the library load Ruling 2's canary owes — V04 stays the test phase's.

One new finding, Minor and advisory: the guard this commit added has no counterpart one level down.

## Findings

### F1 — the new duplicate-key guard covers the values-file map and not the pins map, so two keys naming one YAML path silently drop a pin

- **Severity** Minor · **Impact** advisory · **Anchor** repro-trace · **Confidence** high

`normalizePins` throws when two keys render the same values-file name (`vars/cicd.groovy:154-157`,
`pins names ${name} twice`) — the new check this commit adds, and the right one: without it two
spellings of one file collapse and a whole file's pins vanish. One line further down the same
structure gets no such check: `:161` writes `normalised[path.toString()] = value.toString()` in a
loop, so two distinct keys in one file's dict that render the same dotted path collapse, last one
wins, nothing is said.

Traced and run: with `String c = 'controller'`, the map literal
`['images.controller': ':800', ("images.${c}"): ':801']` keeps **two** keys — one `String`, one
`GStringImpl`, both rendering `images.controller` (literals do not coerce; only subscript
assignment does, which is the same asymmetry `:140-144` documents). `:161` folds them to one. The
build committed `  controller: ":801"` and echoed
`pvginkel/Decoy de50642 pins config/dev/values.yaml.` — `:800` was discarded with no error, no
warning and a success return.

Why it is a defect rather than taste: `:16-18` states that a pin landing nowhere "deploys the
previous image and says nothing", and that this is the failure the method exists to make
impossible; `:154-157` now enforces exactly that property one level up, and the docstring at
`:27-31` places no constraint on key types.

Why it is advisory: no caller in this slice writes that shape, and neither does the call shape
P3 records for slice 012 (`plan.md`, P2 "Later phases": one literal per path, no interpolated
path keys); the result is a valid pin in a well-formed file rather than corruption; and the
silently-lost pin is the caller's own contradiction — it named two values for one path.
