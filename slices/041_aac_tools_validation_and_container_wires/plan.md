# Slice 041 — arch-validate errors show the source line and text; generators quote YAML-1.2 number-like strings; Fieldnotes drops its pasted SSE gateway default

## Requirements / rulings

- R1 (ANS-184.1). "In a type error, have `arch-validate` print the source scalar and its line next
  to the parsed value, e.g. `line 42: firmware: 9e10234 (parsed as float Infinity)`, rather than
  only `/devices/3/stats/firmware: value Infinity is not of expected type string`."
- R2 (ANS-184.2). "Have the generators' YAML writer quote any string that YAML 1.2 would read as a
  number (`1e5`, `1.5e3`, `0o17`, `089`, `9e10234`). PyYAML dumps by YAML 1.1 rules and leaves
  these unquoted. This is the real defect, and it comes back whenever live data holds such a
  string. Which code owns this dump was not checked."
- R3 (ANS-184.3). "If the pipeline change is small, archive the generated architecture file when
  an AaC validate stage fails."
- R4 (ANS-151). "Wanted: a wire that names its container, or one drawn only on the containers that
  set the var, so one image with several roles carries a wire per role. The same scoping would
  keep a recipe's `boundByDefaultValue` off containers that never make the call; FieldnotesDeploy's
  chart now sets `SSE_GATEWAY_URL` on `app` to get that."
- Ruling (ANS-184, on the card): "yes" — on the ask as written.
- Ruling (ANS-151, operator's card comment 2026-09-30): "Please note that there's a link to a
  different card that's on Later. I want moved to New once this card is resolved." (FN-14.)
  Done at planning, 2026-10-03: FN-14 moved Later → New (its blocker shipped 2026-09-29, see R4
  grounding) with a comment carrying the working wire shape; this slice does not edit FN-14's
  work.
- Ruling (2026-10-03, on the boundByDefaultValue half of R4): "I see two options. This "fix"
  isn't a fix because it depends on changing a global default. An example of "Solves my
  problem". The two options I see are: Draw both edges. This is my lean. Add the parameter a ""
  or null to the MCP app. Why do I lean to drawing both edges? Nothing inherently prevents the
  MCP instance from calling the SSE server. It could do so at any time. And then the architecture
  would break silently. The capability is there, even if it's not exercised. Setting the value to
  "" or null for the MCP app, would fix that. But, I don't find this important enough. Don't try
  to get this right. Just remove the SSE_GATEWAY_URL config from the app and the comment. If you
  want, you can add one to the MCP that the edge is drawn but not used by the app. It's known and
  not identified as a problem."
  → No generator work for boundBy scoping. FieldnotesDeploy's chart drops the `SSE_GATEWAY_URL`
  env entry and its comment from the `app` container (`chart/templates/app-deployment.yaml`,
  ~lines 57-61); the recipe's `boundByDefaultValue` then applies to both `app` and `mcp`, and the
  model carries the gateway Serving edge onto both — accepted as known. A short comment on the
  `mcp` container saying the edge is drawn onto it though it does not use the gateway is
  optional (operator: "If you want"). This rolls the Fieldnotes pod on sync; that is expected.

#### Grounding (verified at planning, 2026-10-03)

- **R1 lands in the Architecture service, not in `arch-validate`.** `arch-validate`
  (`ArgoCDTools/aac-tools/image/arch-validate.py`) only POSTs the file to
  `https://architecture.webathome.org/api/validate` and prints each error's `path`, `message`,
  `schema`, `hint` (`print_human`, ~lines 78-107). Parsing is `js-yaml` 4 (YAML 1.2 core
  schema — why `9e10234` becomes Infinity) in `Architecture/service/src/validate.ts`; validation
  is ajv; the quoted message is built in `service/src/error-translate.ts` (`value … is not of
  expected type …`). No source positions are kept today. Settled by the session: on errors, the
  service re-reads the uploaded text with a position-keeping YAML parser (e.g. the `yaml` npm
  package, `parseDocument` + `LineCounter`) to map each error's JSON pointer to its node; every
  error that maps gets a `line` field; a type error's message also carries the raw source scalar
  next to the parsed value, in the card's form. `arch-validate` prints the line. Both copies of
  `arch-validate` change identically — `ArgoCDTools/aac-tools/image/arch-validate.py` and
  `Architecture/.claude/architecture/arch-validate.py` (byte-identical today). A push of the
  Architecture repo makes AaC/Architecture build the `architecture_viewer` image and pin it in
  WebathomeOrgDeploy prd — the normal path, no promotion step.
- **R2: the dump that actually failed is already fixed.** The AaC/IoTSupport #43/#44 failure was
  IoTSupport's own `backend/tools/gen-architecture.py`, fixed 2026-10-01 (IoTSupport `d6ec6e8`,
  `_Yaml12SafeDumper`, ~line 609 — the reference pattern). Two generators still dump with plain
  `yaml.safe_dump` and no representer: ArgoCDTools `aac-tools/image/gen_architecture.py`
  (single write site, ~line 1245) and Architecture `tools/ha-fleet/gen-ha-fleet.py` (~line 394,
  writes live Home Assistant device data — the more exposed). Both get the same quoting. Quoting
  is safe for the readers: PyYAML loads (collector) and js-yaml (service) both read a quoted
  scalar as a string. The quoting target is what the service's reader takes for a number, a
  superset of the YAML 1.2 core grammar: js-yaml 4 also reads `_` digit separators (`1_0e5` →
  1000000, `0o1_7` → 15; witnessed in plan review r1), which IoTSupport's resolvers do not
  cover — so the two generators extend the reference pattern to those forms. Over-quoting a
  string is harmless; under-quoting is the defect.
- **R3 is already satisfied; no pipeline change.** Every generated architecture file is archived
  in its Generate stage before Validate runs: IoTSupport's `Jenkinsfile.architecture` (since its
  2026-10-01 restructure, slice 035) and every deploy repo via JenkinsPipelineUtils'
  `architectureProducer` template (`docs/examples/deploy-architecture.groovy`). Hand-authored
  files validate before archiving but live in git. R3 is checked off by evidence, not by work.
- **R4's wire half already shipped.** gen_architecture's `containers:` map on an image entry
  (ArgoCDTools `14d85ae`, 2026-09-29, slice 026 / ANS-90; `SCOPED_KEYS = {"realizes",
  "upstream"}`) scopes `upstream` per container — the "wire that names its container" shape.
  Verified by a local run against FieldnotesDeploy: `containers: {app: {upstream: [{env:
  FIELDNOTES_KUBECODER_URL, providers: [kubecoder-controller]}, {env: FIELDNOTES_YOUTRACK_URL,
  providers: [youtrack]}]}}` drew exactly two new Serving edges onto `fieldnotes/app`, none onto
  `mcp`. The models wire still needs `models.url` set in prd values (FN-14 already says so). No
  generator work is owed for R4; the boundBy half is resolved by the 2026-10-03 ruling.

## Task shape

pre-settled — the rulings and grounding above fix every mechanism (R1: the service maps error
pointers to source positions and `arch-validate` prints the line; R2: the two named generators get
IoTSupport's YAML-1.2 quoting pattern; R3: satisfied by evidence; R4: the FieldnotesDeploy chart
drops its `SSE_GATEWAY_URL` entry); planning is transcription into per-repo phases.

## Ordering constraints

- The Architecture service phase (R1's line/source fields) lands before the phase that makes
  `arch-validate` print the line, or `arch-validate` must tolerate a response without `line`.
- P1 changes the service and the canonical `arch-validate` together. P3 ships P1's script byte for
  byte, so it runs after P1.

### P1 — The validate service locates each error in the source; arch-validate prints the line

Target: service

When an artifact fails validation, every error in the `POST /api/validate` response that can be
traced to a node of the submitted text carries that node's line. A type error's message also
shows the source scalar as written beside the value it was parsed as. The canonical
`arch-validate`, Architecture's `.claude/architecture/arch-validate.py`, prints the line. For the
card's case the output then reads in the card's form: `line 42: firmware: 9e10234 (parsed as
float Infinity)`. Today the service parses with js-yaml and keeps no positions
(`src/validate.ts:154`). The type message is built from the parsed value alone
(`src/error-translate.ts:188-195`), and the script prints only path, message, schema and hint
(`arch-validate.py:100-105`).

- **Validation itself does not change.** js-yaml still produces what ajv and the relation-triple
  check see. The session settled the mechanism: a second, position-keeping parse of the same text
  (e.g. the `yaml` package's `parseDocument` + `LineCounter`) only maps each error's JSON pointer
  to its node.
- **`line` is an additional field on the error object** (shape at `src/error-translate.ts:3-16`).
  An error that does not map keeps today's shape. The relation-triple errors
  (`src/validate.ts:194-202`) map too.
- **The script prints an error without `line` exactly as today.** Every error lacks it until the
  new service image is live, and the script is the one estate-wide copy pinned by hash. It stays
  standard-library only (`arch-validate.py:18`), and `--json` still passes the raw response
  through.
- **`test/arch-validate.test.ts` is where the card's case gets pinned end to end.** It already
  runs the canonical script against an in-process service.

**Done (P1).** Architecture `2dcf07b` on `phase/041-P1`. `POST /api/validate` errors carry `line`
wherever the pointer maps; a type error on a one-line scalar reads `firmware: 9e10234 (parsed as
float Infinity) is not of expected type string`; `arch-validate` prints `line N: <message>`.

Later phases:
- P3: the canonical `.claude/architecture/arch-validate.py` at `2dcf07b` has md5
  `766f6ec529466c321bf79cef1507e0db` — the value for `CANONICAL_ARCH_VALIDATE_MD5`.

Record:
- New `service/src/source-locator.ts`: `sourceLocator(text)` parses lazily (first lookup only, so a
  valid artifact is never re-parsed) with `yaml` `^2.9.1` (`parseDocument` + `LineCounter`) and
  returns `{line, key?, scalar?}` per JSON pointer. Line is the key's line for a mapping value,
  else the node's first line; aliases resolve to their anchor; JSON bodies map too. A key that only
  exists through a js-yaml `<<` merge does not map — that error keeps today's shape (pinned).
- `translateErrors(raw, artifact, locate)` — `locate` is a required third argument;
  `checkRelationsTriples` takes it too. `line` sits right after `path` in the error object.
- Type message: `<key>: <scalar as written> (parsed as <t> <value>)`, or `value <scalar> (…)` for a
  sequence item / root; `<t>` is `str|bool|int|float`, from the parsed JS value (so `1e5` reads
  `int 100000`, as ajv sees it); null reads `(parsed as null)`. Multi-line scalars and non-scalars
  keep the old `value X is not of expected type Y`. Scalars clip at 60 chars like `quoteShort`.
- On the wire `value` stays `null` for Infinity (JSON) — unchanged; the message now carries it.
- Script: one line changed in `print_human`; `--json` untouched; stdlib only.
- Tests: `test/source-locator.test.ts` (new), card case + triple line + JSON + merge-key shape in
  `validate.test.ts`, exact stderr for the card case and for a line-less (old-service) response in
  `arch-validate.test.ts`. Gate: `kc project test --project service` green; build green.

### P2 — The Home Assistant fleet generator quotes strings YAML 1.2 reads as numbers

Target: tooling

`tools/ha-fleet/gen-ha-fleet.py` writes every string that a YAML 1.2 reader would take for a
number in quotes (`1e5`, `1.5e3`, `0o17`, `089`, `9e10234`). Live Home Assistant data then reaches
the service as the strings it is. Today it dumps with plain `yaml.safe_dump` inline in `main`
(`gen-ha-fleet.py:394`).

- **Reference pattern:** IoTSupport's `_Yaml12SafeDumper` (commit `d6ec6e8`,
  `backend/tools/gen-architecture.py:609`, used at `:635`; a checkout is at
  `/work/scratch/IoTSupport`). Strings that are not number-like are written as before.
- **The generator cannot run against Home Assistant here** (`.kubecoder/config.yaml:39-41`). Its
  tests are `tooling/tests/test_ha_fleet.py`, which loads the script by path.
- **No new dependency.** Its Jenkins job installs only `websocket-client` and `pyyaml`
  (`Jenkinsfile.ha-fleet:46`).

### P3 — aac-tools ships the new arch-validate and quotes strings YAML 1.2 reads as numbers

Target: aac-tools

- **The image ships P1's canonical `arch-validate`.** `image/arch-validate.py` is a copy of
  Architecture's `.claude/architecture/arch-validate.py` as P1 left it, byte for byte. The pinned
  `CANONICAL_ARCH_VALIDATE_MD5` (`tests/test_image.py:20`, checked at `:74-78`) is that file's
  hash. The copy is never edited or reformatted here (`tests/test_image.py:16-19`).
- **`gen-architecture` writes every string that a YAML 1.2 reader would take for a number in
  quotes.** It has a single write site (`image/gen_architecture.py:1242-1245`). The reference
  pattern and the unchanged-otherwise rule are P2's. The image installs only `python3-yaml` beside
  the standard library (`tests/test_image.py:22-25`).

### P4 — FieldnotesDeploy stops pasting the SSE gateway default onto `app`

Target: github:pvginkel/FieldnotesDeploy

FieldnotesDeploy is not checked out under `/work`. The driver clones it for this slice, or adopts
the clean clone at `/work/scratch/FieldnotesDeploy`.

`chart/templates/app-deployment.yaml` no longer sets `SSE_GATEWAY_URL` on the `app` container, and
no longer carries the comment that justified it (`:57-61`). When no container sets the variable,
gen-architecture applies the recipe's `boundByDefaultValue` to every instance of the product
(`ArgoCDTools/aac-tools/image/gen_architecture.py:1597-1606`). The prd model therefore carries the
SSE gateway Serving edge onto both `app` and `mcp`, which the 2026-10-03 ruling accepts as known.
The operator allows one short comment on `mcp` saying the edge is drawn onto it though it does not
call the gateway ("If you want"). Nothing beyond that comment goes in.

The repo's gate already runs `gen-architecture --stage prd` and `arch-validate`
(`.kubecoder/project.yaml`), and both stay green with the edge drawn onto both containers. The pod
rolls when Argo CD syncs; that is expected.

## Not in scope

- FN-14's wires in FieldnotesDeploy's `architecture.yaml` and the prd `models.url` value — FN-14's
  own work, moved to New by this planning session.
- Any per-container scoping of `boundBy` / `boundByDefaultValue` in the generator (ruled out).
- JenkinsPipelineUtils and any Jenkinsfile change (R3 already holds).
- IoTSupport's generator (already fixed).
- Any YAML writer other than the two generators R2's grounding names.
- The offline validator in Architecture's `tooling/` and its error output. R1 is `arch-validate`
  and the service it calls.
