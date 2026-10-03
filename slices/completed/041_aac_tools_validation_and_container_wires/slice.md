---
issue: ANS-192
---

# 041 — aac-tools: validation errors, YAML quoting, per-container wires

Two asks against ArgoCDTools' `aac-tools`: an `arch-validate` type error that hides its cause and
a YAML writer that emits strings YAML 1.2 reads as numbers (ANS-184), and an `upstream:` wire that
cannot be scoped to one container of an image that runs as several (ANS-151).

Source: triage 2026-10-02 of the ANS intake queue. Cards: ANS-184, ANS-151. The phase count
triage guessed (~5) is a guess from the cards alone.

## Requirements

1. **ANS-184.1 — type errors show the source.** "In a type error, have `arch-validate` print the
   source scalar and its line next to the parsed value, e.g. `line 42: firmware: 9e10234 (parsed
   as float Infinity)`, rather than only `/devices/3/stats/firmware: value Infinity is not of
   expected type string`."
2. **ANS-184.2 — generated YAML quotes number-like strings.** "Have the generators' YAML writer
   quote any string that YAML 1.2 would read as a number (`1e5`, `1.5e3`, `0o17`, `089`,
   `9e10234`). PyYAML dumps by YAML 1.1 rules and leaves these unquoted. This is the real defect,
   and it comes back whenever live data holds such a string. Which code owns this dump was not
   checked."
3. **ANS-184.3 — archive on a failed validate.** "If the pipeline change is small, archive the
   generated architecture file when an AaC validate stage fails."
4. **ANS-151 — a wire per container role.** "Wanted: a wire that names its container, or one
   drawn only on the containers that set the var, so one image with several roles carries a wire
   per role. The same scoping would keep a recipe's `boundByDefaultValue` off containers that
   never make the call; FieldnotesDeploy's chart now sets `SSE_GATEWAY_URL` on `app` to get that."

## Operator rulings and Q&A

- ANS-184: operator's ruling on the card, "yes" (on the ask as written, no note). Item 3 is
  conditional in its own words ("If the pipeline change is small").
- ANS-151: the two shapes ("a wire that names its container, or one drawn only on the containers
  that set the var") are not ruled; the nightly card pass noted "it extends the architecture.yaml
  wire schema every producer shares, and the card leaves two shapes [...] to pick between."
- **ANS-151, operator's comment (2026-09-30):** "Please note that there's a link to a different
  card that's on Later. I want moved to New once this card is resolved." The linked card is FN-14
  (ANS-151 relates to it). When this slice delivers ANS-151, FN-14 moves from Later to New.
- No standing-decision collision found at triage for either card.

## Source material

The cards as read at triage on 2026-10-02, verbatim (headings demoted one level). A card's
diagnosis, cause or line reference is the card's claim, not verified at triage.

### ANS-184 — aac-tools: arch-validate type errors show the source text and line; generated YAML quotes strings that YAML 1.2 reads as numbers

- Reporter: jeeves · Created: 2026-10-02 · State: New · Type: Task · Updated: 2026-10-02
- Links: none

#### Description

Asked, in aac-tools:

1. In a type error, have `arch-validate` print the source scalar and its line next to the parsed value, e.g. `line 42: firmware: 9e10234 (parsed as float Infinity)`, rather than only `/devices/3/stats/firmware: value Infinity is not of expected type string`.
2. Have the generators' YAML writer quote any string that YAML 1.2 would read as a number (`1e5`, `1.5e3`, `0o17`, `089`, `9e10234`). PyYAML dumps by YAML 1.1 rules and leaves these unquoted. This is the real defect, and it comes back whenever live data holds such a string. Which code owns this dump was not checked.
3. If the pipeline change is small, archive the generated architecture file when an AaC validate stage fails.

Operator's ruling: "yes" (on the ask as written, no note).

Evidence: 1 report from IoTSupport, 2026-10-01. AaC/IoTSupport #43 and #44 failed on a generated deployed-architecture.yaml that was not archived, so the cause had to be inferred. #45 is green.

Fieldnotes observation: 01M3WCK7KG6X5XFG1CJYMYNK7F

#### Comments

none

### ANS-151 — aac-tools gen-architecture: an upstream wire cannot be scoped to one container of a shared image

- Reporter: jeeves · Created: 2026-09-27 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-30
- Links: Relates: FN-14

#### Description

An `upstream:` wire on an `images:` entry applies to every non-init container of that image, and a var a container does not set is a hard fail (`resolve_upstreams`). FieldnotesDeploy's `fieldnotes` image runs as two containers, `app` and `mcp`, and only `app` sets `FIELDNOTES_KUBECODER_URL`, `FIELDNOTES_YOUTRACK_URL` and `FIELDNOTES_MODELS_URL`. So the deployer cannot draw the Serving edges to the KubeCoder controller, YouTrack and the models pod, and producer `fieldnotes-app` publishes the three as plain Associations only.

A `boundBy` recipe is no way around it: on a `svc:` target, `resolve_svc_target` looks only at this render's instances, so a provider another deploy repo runs fails the build. Only `cap:` targets resolve through published interfaces.

Wanted: a wire that names its container, or one drawn only on the containers that set the var, so one image with several roles carries a wire per role. The same scoping would keep a recipe's `boundByDefaultValue` off containers that never make the call; FieldnotesDeploy's chart now sets `SSE_GATEWAY_URL` on `app` to get that.

15 images in the fleet run as several containers. Found while seeding `fieldnotes-app`, 2026-09-27.

#### Comments

##### Comment 1/2 · 7-5189 · jeeves · 2026-09-28 01:03Z

Card pass 2026-09-28: outside the lane — no boundary crossed: it extends the architecture.yaml wire schema every producer shares, and the card leaves two shapes (a wire naming its container, or one drawn only where the var is set) to pick between.

##### Comment 2/2 · 7-5272 · pvginkel · 2026-09-30 17:17Z

Please note that there's a link to a different card that's on Later. I want moved to New once this card is resolved.
