# Slice 041 — plan review r1

Verdict: **go**. The plan can run as written. No finding needs a ruling from the operator and none
blocks the run. Two advisory notes follow, then what was checked.

## Advisory

### A1 — R2: the reference quoting pattern and the service's actual YAML reader disagree on underscore forms

**Problem.** P2 and P3 take IoTSupport's `_Yaml12SafeDumper` (`d6ec6e8`,
`backend/tools/gen-architecture.py:609-625`) as their reference pattern. Its resolvers follow
the YAML 1.2 core number grammar, which has no `_` digit separators. The service reads with
js-yaml 4 (`service/src/validate.ts:154`), and js-yaml also reads underscore-separated digits as
numbers. V05's second sentence goes further than R2's wording: "Each such string reads back as
the same string through the service's YAML reader".

**Evidence** (witnessed this round). In `/work/Architecture/service/node_modules/js-yaml`,
`1_0e5` loads as `1000000` and `0o1_7` as `15`. The reference dumper, run in the aac-tools
image's Python with its PyYAML, writes both plain (`1_0e5: 1_0e5`). Every example in the card
(`1e5`, `1.5e3`, `0o17`, `089`, `9e10234`) comes out quoted, and so do `1_000` and `0b101`,
which YAML 1.1 already covers.

**Impact.** It is narrow. A string with digit separators in a number-like shape is unlikely in
live device or chart data. Still, the plan states two targets, "YAML 1.2 reads as a number"
(R2's words) and "what the service's reader reads as a number" (V05). They diverge on these
forms. The executor and a test author may each pick a different one, and V05's second sentence
can fail against code that follows the reference exactly.

### A2 — No phase, criterion or close-out action carries the FN-14 move

**Problem.** The operator's comment on ANS-151 asks for FN-14 to move from Later to New. The
plan's ruling hands this to the planning session ("The session moves FN-14 Later → New at
planning … with a comment carrying the working wire shape"). Nothing in `verification.json`
or the close-out report records it.

**Evidence.** The close-out report is empty (`close_out.py list`). The spec history
(`787a49d`, `222763d`, `bba8343`) shows no record that the move was made. This reviewer has no
YouTrack access and could not check the card's state.

**Impact.** If the session has already moved FN-14, there is nothing to do. If it has not, no
role in the run or its close-out will, and an instruction the operator wrote explicitly is
dropped without anyone noticing.

## What was checked

- **AC completeness.** V01–V04 cover R1, V05–V06 cover R2, V07 covers R3, and V08–V09 cover R4.
  Each quotes its requirement in the operator's wording. V09 carries the 2026-10-03 ruling,
  which is recorded in the rulings section. V07 and V08 are earned by evidence the test phase
  can read; neither depends on the doc phase. There are no doc-truth universals.
- **Task shape.** `pre-settled` is justified. The session's grounding settles every mechanism,
  and each grounding claim below held when re-checked against the code.
- **Targets.** `run_loop.py run … --dry-run` resolves all four phases: `service` and `tooling`
  to Architecture, `aac-tools` to ArgoCDTools, and `github:pvginkel/FieldnotesDeploy` to the
  clean, up-to-date clone at `/work/scratch/FieldnotesDeploy`, which has a
  `.kubecoder/project.yaml` gate. P2's code sits in `tools/ha-fleet/`, outside `tooling/`, but
  `tooling`'s pytest is the gate that exercises it (`tooling/tests/test_ha_fleet.py` loads the
  script by path), so the Target is right. The `modern-app`, `iac` and `aac-tools` sidecars the
  gates call are present in this environment.
- **Citations.** These match the code: `arch-validate.py:18` and `:100-105`; `validate.ts:154`
  and `:194-202`; `error-translate.ts:3-16` and `:188-195`; `gen_architecture.py:272`, `:1245`
  and `:1597-1606`; `test_image.py:20`; `gen-ha-fleet.py:394`; `Jenkinsfile.ha-fleet:46`;
  `14d85ae`; and IoTSupport `d6ec6e8`. The two `arch-validate.py` copies are byte-identical, at
  md5 `9e7e3f8c…`. Gitblit finds other copies only in DesignAssistant, SomfyRemote and the
  archived HelmCharts. None of those is a registered producer. The type-error message text is
  pinned only by the service's own test.
- **Derived expectation for P4 / V09** (witnessed). I copied FieldnotesDeploy, removed the
  `SSE_GATEWAY_URL` entry and its comment, and ran `gen-architecture --stage prd --producer
  fieldnotes-deploy`. The relation count went from 77 to 78. The one added relation is
  `…-sse-gateway-serves-…-fieldnotes-mcp-ssegateway` (Serving, onto `mcp`), `app`'s edge is
  unchanged, and `arch-validate` passes. The removed value is `http://localhost:3402`, which
  the chart's own comment calls the API's built-in default, so the pod's runtime behaviour
  does not change.
- **R3.** Every generating `Jenkinsfile.architecture` that is checked out archives in its
  Generate stage, before Validate: ArgoCDDeploy, KubeCoderDeploy, FieldnotesDeploy, IoTSupport,
  `Jenkinsfile.ha-fleet`, and the scratch deploy repos. The hand-authored producers validate
  first, but their files are in git.
- **R2 generator inventory.** Gitblit `**/gen*architecture*` and `**/gen-*.py` find only
  ArgoCDTools, IoTSupport (already fixed), `gen-ha-fleet.py` and the archived HelmCharts. The
  pipelines take `registry:5000/aac-tools` at its floating tag (`podYaml.groovy:76`), so P3
  reaches them when it is pushed.
- **Phases.** Each phase is PR-sized and can be reviewed from its own diff. The phases run
  producers-first (P1 before P3), with no end-to-end testing phase and no auto-doc phase. There
  are no attachments and no doc-deliverable content.
