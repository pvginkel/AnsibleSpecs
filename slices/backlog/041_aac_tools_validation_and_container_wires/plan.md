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
  The session moves FN-14 Later → New at planning (its blocker shipped 2026-09-29, see R4
  grounding), with a comment carrying the working wire shape; this slice does not edit FN-14's
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
  scalar as a string.
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

## Ordering constraints

- The Architecture service phase (R1's line/source fields) lands before the phase that makes
  `arch-validate` print the line, or `arch-validate` must tolerate a response without `line`.

## Not in scope

- FN-14's wires in FieldnotesDeploy's `architecture.yaml` and the prd `models.url` value — FN-14's
  own work, moved to New by this planning session.
- Any per-container scoping of `boundBy` / `boundByDefaultValue` in the generator (ruled out).
- JenkinsPipelineUtils and any Jenkinsfile change (R3 already holds).
- IoTSupport's generator (already fixed).
