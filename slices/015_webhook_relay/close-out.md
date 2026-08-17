# Close-out — slice 015 webhook_relay

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Every entry, in every section, has exactly this shape. The id is the section's letter
     (A · N · B · Q · S) and the next number — count the section's `###` headings, struck ones
     included. Severity (major | minor | nit | cosmetic) sits in the heading of Bugs only.
     `Disposition:` is the operator's line: leave it blank.

     ### B2 — <headline: one line, the claim itself> · minor · <repo or component>

     <What: the thing itself, quoted where it is text or output — the sentence, the command and
     what it printed, the file and lines. Why it matters: the consequence, or "none" said plainly.
     How it was found. As many paragraphs as it takes.>

     Provenance: <role, phase, round; the artifact that holds the full record>
     Disposition:

     An entry is never deleted. Struck, it keeps its heading, with the reason appended:

     ### ~~S3 — <headline>~~ — absorbed by P11 (97b5313), struck by consult 1
-->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — first push of `webhook-relay`; live `DockerImages` build confirms the pipeline discovery claim · DockerImages

The test phase pushed this slice's three `DockerImages` commits (`51f6653`, `6f4c884`, `6e01ede`)
to `origin/main` — their first push; the branch had only existed locally since the phase and
consult rounds. `track_build.py` could not track the result (`$JENKINS_TOKEN` is not set in this
pod), so the Jenkins MCP tools were polled by hand instead: job `DockerImages` build #2485 started
automatically off exactly these three commits with no registration step, and finished `SUCCESS` in
120s, publishing `registry:5000/webhook-relay:2485` and `:latest`. This is live evidence for V06's
"creating the directory is the whole of wiring it into the pipeline" claim, beyond the phase's own
`kaniko --context webhook-relay --no-push` dry run (also re-run green this session).

Provenance: test-agent, test round 1; Jenkins `DockerImages` #2485.
Disposition:

## Bugs

Focus: <!-- doc-writer: the worst one first; which are in this slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — nothing in `webhook-relay`'s suite pins the constant-time signature comparison · minor · DockerImages

`verification.json` V14 names five properties of GitHub's webhook wire format that R6's suite must
pin. Four are pinned by real tests — the `sha256=` prefix and lowercase-hex digest, the digest over
the exact raw bytes off the wire, a missing `X-Hub-Signature-256` refused exactly like an invalid
one, and SHA-1 forwarded but never trusted. The fifth, *"the comparison is **constant-time**
(`hmac.Equal`), never `==`"*, has no test behind it. Mutation run during review: in a scratch copy
of the module, replacing `webhook-relay/src/internal/signature/signature.go:36`'s
`return hmac.Equal([]byte(got), []byte(want))` with `return got == want` leaves
`cexec go go test -count=1 ./...` green across all three packages.

Consequence: none today — the shipped code is constant-time, and the doc comment above it says why.
The exposure is to a future edit: the one security property among the five is the one the suite
would not notice being removed, on the service whose whole design rationale is what an
unauthenticated internet caller can reach. It is filed rather than fixed because constant-timeness
is not behaviourally testable in Go without a timing harness whose flakiness would cost more than it
buys; a source-level guard (a lint rule, or a comment the next reader is expected to honour) is the
realistic shape of any fix.

Provenance: code-reviewer, P1 round 1 (F2, Major severity / advisory impact); `phases/P1/code_review_r1.md`
Disposition:

### B2 — two request shapes escape the relay's stated refusal matrix · nit · DockerImages

`verification.json` V04, `plan.md`'s health-path ruling and `webhook-relay/README.md:75-76`'s table
all say the same thing: exactly two routes are served, and every other path and every other method
on those two is refused (`405` / `404`). Two shapes are neither, both consequences of Go's
`ServeMux` and confirmed by probing the commit through `ServeHTTP` and over a real socket:
`HEAD /healthz` → `200` (a `GET` pattern also matches `HEAD`), and `POST /api//webhook` or
`POST /api/./webhook` → `307` (the mux redirects a non-canonical path rather than missing).
`webhook-relay/src/internal/relay/relay_test.go:354-381` pins eleven refusal cases and covers
neither shape.

Consequence: none for the product — `HEAD` is `GET` without a body per RFC 9110, and the `307` lands
the client on the canonical path where the signature still has to verify. It is worth recording only
because the two-route ruling exists so that a test agent probing the refusal matrix "does not have to
guess which way to rule", and these are exactly that guess — now also asserted in the image's own
README as a claim the binary does not make.

Provenance: code-reviewer, P1 round 1 (F1, Minor severity / advisory impact); `phases/P1/code_review_r1.md`
Disposition:

### ~~B3 — "the estate's only internet-facing service" is false as written~~ — fixed in session by consult 1 (`6e01ede`), struck by consult 1 · nit · DockerImages

`webhook-relay/architecture.yaml:4`, `README.md:9-10` and `Dockerfile:12-13` each state flatly that
the relay is the estate's only internet-facing service. Twenty-one Services are public today —
`grep -rn isPublic /work/HelmCharts/configs/prd | grep -c yes` → 21, among them
`jenkins/prd/values.yaml:4`, `keycloak/prd/values.yaml:4`, `guacamole/prd/values.yaml:4` and
`webathome-org/prd/values.yaml:4` — and this slice's own estate facts say so: `slice.md`, *"Jenkins
rides it today at `jenkins.webathome.org`"*. The authoritative design states the narrower, true
claim: the consult's §1 calls the relay "the only public thing in `argocd-prd`".

Consequence: nothing breaks, and the claim does not reach the merged federated model (it is a
YAML comment, not a modelled element). It is recorded because one of the three copies is in a
hand-authored `architecture.yaml`, which is source of truth rather than a throwaway comment, and
because the sentence is the stated premise for the Dockerfile's minimal-package argument.

Provenance: code-reviewer, P1 round 1 (F3, Minor severity / advisory impact); `phases/P1/code_review_r1.md`
Resolution: fixed by consult 1 in `6e01ede` — comment and prose only, no behaviour change, in three
files this slice's diff created, which is the mechanical-residue exception rather than a phase or a
report entry. All three now state the true, narrower claim the authoritative design states: the
relay is the only internet-facing service in `argocd-prd` and the only way in from the internet
toward Argo CD. `main.go:27`'s "this process is internet-facing" was already true and is untouched.
Gate re-run green after the edit: `cexec go go test ./...` and `cexec iac ./scripts/arch-validate.py
*/architecture.yaml` over all 23 files.
Disposition: no action needed

## Open questions and rulings

Focus: <!-- doc-writer -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — `DockerImages` has no `.kubecoder/project.yaml`, so phases targeting it get no deterministic gate · DockerImages

P1 is the first phase in the whole slice set to carry `Target: ../DockerImages` (`grep -rn
"Target:.*DockerImages" /work/AnsibleSpecs/slices/` matches only this slice's plan). The run loop
resolves a sibling repo's gate from that repo's own manifest and falls back to none when there is
no `.kubecoder/project.yaml` — `run_loop.py:1509-1515` — so the dry run prints `gate: (no
deterministic gate)` and the code reviewer is told the state is unverified. Of the repos checked
out here, `Ansible`, `HelmCharts`, `Charts`, `ArgoCDTools`, `KubeCoder` and `AIWorkflow` carry a
manifest; `DockerImages`, `ArgoCDDeploy`, `HomelabTerraformProvider`, `JenkinsPipelineUtils` and
`AnsibleSpecs` do not.

The plan works around it by naming the two gate commands in P1 itself (`cexec go go test ./...`,
`cexec iac ./scripts/arch-validate.py */architecture.yaml`), which is correct for this slice but
does not generalise — every future `DockerImages` phase pays the same tax, and each one invents
its own gate. A small `.kubecoder/project.yaml` in `DockerImages` wiring `test` to the Go suites
and `arch-validate.py` would make the loop's gate real there. Note the repo is heterogeneous (Go,
Python and pure-Dockerfile directories), so what "test" means repo-wide is a genuine design
question, not a copy-paste.

Provenance: plan-writer, planning round 1; `plan.md` P1 and the `--dry-run` output
Disposition:

### S2 — `webhook-relay`'s architecture edge toward the two Argo CD receivers is owed to 009 · DockerImages / ArgoCDDeploy

`webhook-relay/architecture.yaml` models the relay's own identity and exposed surface — `app:`,
`svc:`, `if:POST /api/webhook` — but carries **no consumption edge** toward the two receivers it
fans out to, even though those are its only outbound dependencies and the reason it exists. The
producer manual is why: "A cross-producer reference is the UUID — period," and Argo CD is modelled by
no producer today (`find /work/HelmCharts -name architecture.yaml | xargs grep -il argo` matches
nothing, and `ArgoCDDeploy` does not exist until 009's first phase). There is no UUID to point at, so
the honest artifact omits the edge rather than minting a dangling hint-only reference.

Consequence: in the merged model the estate's one internet-facing service looks like a leaf — it
exposes a public endpoint and consumes nothing — which understates both its blast radius and the
`015 → 009` dependency. Nothing breaks; `arch-validate` is green either way, since it does not
resolve cross-producer refs.

The fix belongs to whichever slice first models Argo CD. When 009 authors `ArgoCDDeploy` (and with it
argocd-server's and the applicationset-controller's `svc:` ids), add two `type: Association`
relations to `webhook-relay/architecture.yaml` — relay `app:` → each receiver's `svc:` UUID, with
`boundBy: "env:ARGOCD_WEBHOOK_URL"` and `boundBy: "env:APPLICATIONSET_WEBHOOK_URL"` recording the
wire. That is a two-relation edit to a file this slice already shipped, not new design.

Provenance: code-writer, P1 round 1; `webhook-relay/architecture.yaml` and P1's done-record in `plan.md`
Disposition:

### S3 — V08 cannot be earned in the phase that judges it: the test phase checks off `verification.json` before the doc phase writes R7 · AIWorkflow

The loop runs `phases → sweep → consult → test → docs` (`run_loop.py:2486`, `:2521`, `:2631`). The
test agent is the one role told to "check off the slice's `verification.json` as you verify"
(`agents/test-agent.md:17`); the doc-writer is never told to touch that file. V08 is R7 — the
`argo-cd/` document-set edits — which this plan deliberately assigns to the doc phase rather than a
coding phase ("R7 is in scope and `verification.json` checks it, but its `argo-cd/` document-set
edits are the run loop's own doc phase … not a phase here"). So when the test agent reaches V08 the
work is genuinely not done yet, and no later role revisits the verdict.

Consequence for this slice: probably none — the test agent reads `plan.md`, which says in as many
words that R7 is the doc phase's, so it has the material to rule "owed to the doc phase" rather than
red. It is recorded so that a V08 verdict of red, or a blank one, is read as this ordering and not as
a product defect, and because the general shape — a slice whose acceptance criteria include
doc-owed items — will recur in this repo, where the `argo-cd/` document set is a first-class
deliverable.

Provenance: consult 1; `state.json` (`test_rounds: 0` at consult time), `run_loop.py`, `agents/test-agent.md`
Disposition:
