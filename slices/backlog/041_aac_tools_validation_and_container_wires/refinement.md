# Slice 041 — refinement

## D1 — A recipe's default edge keeps landing on every container of an image, or the generator gains a way to keep it off a named container

**Context.** An image's own architecture recipe, published by the app's producer, can say "this
app calls X, found in environment variable V; if V is not set, assume default D". Today, if any
container of the image sets V, only those containers get the edge and the others are skipped
silently; only when no container sets V does the default apply — and then to every container of
the image, including ones that never make the call. The per-container map the generator gained
two days after the wire card was filed (see Settled) takes only the two keys that replace an
image's realizes and upstream for one container; it has no way to say "no recipe defaults for
this container".

**The ask.** The card that asked for a wire scoped to one container also wants that scoping to
keep a recipe's default off containers that never make the call. The one known case is
Fieldnotes' SSE gateway: the Fieldnotes image runs as an app container and an MCP container, and
only the app container calls the gateway.

**Background.** The Fieldnotes deploy chart already sets the gateway's URL variable explicitly on
the app container, so the edge lands there only. Verified: the app container really reads that
variable (its own config declares it, with a localhost default) and the MCP container does not
set it — so setting it explicitly is correct configuration, not a hack. Not verified: whether any
of the other roughly fifteen multi-container images in the fleet draws a wrong default edge today
onto a container that does not make the call.

**Why yours.** The card names this as part of what it wants, and building it is a small, real
option — dropping it is a scope cut you could reject.

**Recommendation.** Do not build it. Close that part of the card as covered by the workaround —
set the variable explicitly on the container that uses it — which keeps the generator's
per-container map at the two keys it has. The trade-off: a deployer who meets this again sets the
variable in the chart (rolling the pod) rather than writing one line in the architecture file,
and an edge drawn on the wrong container stays silent rather than being reported.

**The other way.** A third key on the per-container map that switches recipe defaults off for
that container — one more phase in ArgoCDTools with tests and the generator's contract text,
widening the contract every deploy repo shares, for one known case that is already solved.

**If this is wrong.** Nothing breaks; a wrong default edge sits somewhere in the model until it
is fixed by the variable or by building the key then.

**Operator.** (2026-10-03, in chat) "I see two options. This "fix" isn't a fix because it depends on changing a global default. An example of "Solves my problem". The two options I see are: Draw both edges. This is my lean. Add the parameter a "" or null to the MCP app. Why do I lean to drawing both edges? Nothing inherently prevents the MCP instance from calling the SSE server. It could do so at any time. And then the architecture would break silently. The capability is there, even if it's not exercised. Setting the value to "" or null for the MCP app, would fix that. But, I don't find this important enough. Don't try to get this right. Just remove the SSE_GATEWAY_URL config from the app and the comment. If you want, you can add one to the MCP that the edge is drawn but not used by the app. It's known and not identified as a problem."

## Open facts — questions only you can answer

None — nothing in this slice turns on something only you know.

## Settled

- The wire card asked for a wire scoped to one container of an image that runs as several; that
  shape already shipped — the generator gained a per-container map on an image entry on
  2026-09-29 (from the card about Argo CD's controllers), two days after the wire card was filed,
  and a live run in this pod adding the KubeCoder and YouTrack wires under Fieldnotes' app
  container draws exactly two new Serving edges onto it and none onto the MCP container — so the
  wire card needs no generator work and this slice does none for it.
- The Fieldnotes card that adds those three wires to the Fieldnotes deploy repo, parked as Later,
  moves to New now at planning rather than at delivery, since its blocker is gone, with a comment
  giving the working shape it did not know — each wire must name the provider's container, and
  the models wire still needs the models URL set in the prd values; it stays the Fieldnotes
  project's work, and this slice does not edit the Fieldnotes deploy repo.
- The YAML that actually broke was written by IoTSupport's own generator, not the shared
  deploy-repo generator, and IoTSupport fixed it on 2026-10-01 with a dumper that quotes strings
  a YAML 1.2 reader would take for numbers; the same unprotected dump still exists in the shared
  deploy-repo generator in ArgoCDTools and in the Home Assistant fleet generator in the
  Architecture repo (which writes live firmware and version strings, so the more exposed of the
  two), and the slice fixes both the same way.
- Archive-on-failure is already in place — every generated architecture file is archived in the
  stage that generates it, before validation runs: IoTSupport's pipeline since its restructure on
  2026-10-01, every deploy repo's through the shared library template; hand-authored files are
  validated before archiving but are in git, so nothing is lost — so the card's conditional third
  item is closed as already done and no pipeline change is owed.
- The validation message comes from the Architecture service, not the validate command — the
  command only uploads the file and prints the service's errors, and the YAML 1.2 parsing that
  reads a firmware string as Infinity lives in the service — so the source-line fix lands in the
  Architecture repo's web service, and a push of that repo builds the service image and pins it
  to production through its normal pipeline, with no separate promotion step.
- A type error reads with the line and the source text next to the parsed value, as the card's
  example: `line 42: firmware: 9e10234 (parsed as float Infinity)`; every error that maps to a
  spot in the file gets its line, the service returns it as a field, and both copies of the
  validate command — the toolchain image's and the one the Architecture repo ships to producers —
  print it and change together.
- Size: about three phases across two repos — the Architecture service (errors carry the line and
  source text), ArgoCDTools (the deploy-repo generator quotes number-like strings; the validate
  command prints the line) and the Architecture repo's Home Assistant fleet generator (the same
  quoting) — plus the loop's test and doc phases; a fourth phase in ArgoCDTools only if D1 goes
  the other way.
