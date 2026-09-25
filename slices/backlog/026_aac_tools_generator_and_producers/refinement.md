# Slice 026 — refinement

## D1 — The validator migration: the run pushes every carrier repo itself, including the twelve whose push redeploys an app to production and the eight that re-flash or restart a physical device

**Context.** You ruled at triage that moving every copied validator script onto the aac-tools
toolchain is done automated, in this slice, not by hand. The copies are not where the card put
them: the 48 deploy repos already call the validator from the image (the migration tooling wrote
them that way); the copies sit in about 30 application and infrastructure repos, 26 identical to
the canonical script and 7 drifted in lint-only ways. The card's precondition holds — the
KubeCoder catalog lists the toolchain, and the image's validator is byte-identical to the
canonical script.

**The ask.** In each carrier repo, switch the architecture Jenkinsfile to the aac-tools container,
delete the script, and push — about 28 pushes, alongside the 48 one-line pointer edits in the
deploy repos.

**Background.** A push that touches only the architecture Jenkinsfile still starts each repo's
main build; the estate has no skip-ci convention and only three pipelines skip unchanged work.
Twelve app repos build and pin unconditionally — every push rebuilds the image, commits a pin to
the deploy repo, and Argo CD auto-syncs it to production — so each redeploys its unchanged code
once (SSEGateway pins into four deploy repos in one run). Seven firmware repos flash real hardware
over the air on every push, and KitchenDisplay restarts a service on a Raspberry Pi. This is what
any docs-only commit to those repos already does; the sweep adds no mechanism, just about twenty
of them at once. Pushing all ~80 repos together would queue ~80 Jenkins pod builds against the
Kubernetes cloud's container cap, which stalled builds two days ago under a slot leak. Not
verified: whether a rebuild pulls newer base images — that is, whether "unchanged code" comes out
byte-identical.

**Why yours.** It is an outage and risk procedure you carry — production rollouts and unattended
device flashes — and your "done automated" ruling came before these consequences were known.

**Recommendation.** The run pushes every carrier repo itself, under stop rules: small batches of a
few concurrent builds, each batch's builds green and its rollouts healthy before the next; the
device repos last, one at a time, each waiting for its flash upload to succeed; stop and report on
the first red build, failed rollout or failed flash. The deploy-repo pointer edits ride the same
batches (they start only an architecture build and a no-op sync). Trade-off: twelve production
apps restart once on unchanged code and seven devices re-flash with no operator present — the
same a README commit does to them today — and a failed flash (the heating controller among them)
could leave a device down until you reflash it by hand.

**The other way.** The run pushes everything except the eight device repos and prepares their
commits; you push each at a moment you pick, and the run's acceptance for them is owed after that
push. Costs eight manual pushes, and the migration stays unfinished until you do them.

**If this is wrong.** An app restarts on a rebuilt image that does not start — caught by the stop
rule, rolled back by reverting the pin — or a device fails to flash and stays down until reflashed
by hand.

**Operator.** "Agreed" (chat, 2026-09-25)

## D2 — The app-name equality check: drop it and close the card as won't-do, on the measured exposure

**Context.** The generator keys every element id on the chart's name; Argo CD keys the app on its
registry directory. Nothing records, checks or fails on their equality, and you agreed at triage
that something should. Two of the card's premises have moved: the registry lives in HelmCharts,
not ArgoCDDeploy, and all 50 enabled entries across the 48 deploy repos were compared with each
repo's chart name — zero mismatches, because the migration tooling wrote both sides from one name.

**The ask.** Add something that checks the equality, so a deploy repo whose chart name differs from
its registry directory cannot publish a full architecture keyed to a namespace the app is not
deployed in — green, no gap line, every cross-producer edge into the real ids dangling.

**Background.** A mismatch arises only by a deliberate hand edit: registering a new app under a
directory name that differs from its chart name, or renaming a deploy repo's chart. The damage is a
silently wrong model, not an outage; it survives until someone notices. The two names meet in no
place a build can see: the registry is in HelmCharts, the chart name in each deploy repo, and a
deploy repo tracks main, so a chart rename reaches Argo with no registry change. HelmCharts is to
be archived with its pipelines removed at the end of the Argo CD move (a recorded decision), so a
check built into its build dies with it; the records name no future home for the registry (not
exhaustively searched). The Argo CD runbook already states the two must be equal and that nothing
checks it.

**Why yours.** You agreed to this card at triage; dropping it reverses that on new evidence.

**Recommendation.** Rule the check out of this slice and close the card as won't-do; the runbook's
warning stays. Trade-off: a hand-made registry entry with a mismatched name goes unnoticed until
someone looks at the model.

**The other way.** Build the check where the registry lives: HelmCharts' build reads each Argo
entry's deploy-repo chart name and fails on a mismatch. It catches a mismatched entry when it
lands, misses a later chart rename inside a deploy repo until that entry next changes, and lives
only until HelmCharts' pipelines go — about one phase, plus network reads of every deploy repo on
each HelmCharts build.

**If this is wrong.** One future app publishes a wrong-keyed model until someone notices; no outage.

**Operator.** "Agreed" (chat, 2026-09-25)

## D3 — Architecture's edits: this environment gains the tool Architecture's gates run through, and you restart it before the run, rather than moving those edits out of the slice

**Context.** You agreed D1 and D2 on 2026-09-25, and the plan now has eleven phases: three in the
generator, three that publish it and make the judgment-layer edits in KubeCoder's, Argo CD's and
Prometheus's deploy repos, one in the Architecture repo, and the push sweep in the order D1 set.
The run merges a phase only on a green gate. Every one of Architecture's gates runs through a
sidecar tool (modern-app) that this environment does not carry: the planner ran Architecture's
test gate here and it failed before testing anything. This environment dropped Architecture as a
declared repo on 2026-09-20 for that reason — pod start ran Architecture's setup through the
missing tool and reported a permanently failed environment — and kept only the checkout, to read
the contract from.

**The ask.** Three settled items land in Architecture: the producer manual stops telling producers
to copy the validator script and points at the toolchain; the central update agent's instructions
learn to take the contract from `gen-architecture --help`; and Architecture's own environment
config gains the aac-tools toolchain. The question is where that work runs so its gate can go
green.

**Background.** Slice 027's planning is running in this pod now, and a restart ends it. The pod
has an 8 GiB memory limit shared with its sidecars; not verified: what the extra sidecar adds to
that. A side benefit: this pod's aac-tools sidecar runs an image pulled at pod start on
2026-09-23, older than the published generator (for PrometheusDeploy it writes an empty artifact
and exits 0), and a restart refreshes it. The plan already works around that by running every
generator from source, so the slice does not depend on the restart for it.

**Why yours.** It is a procedure you run — a restart that ends every session in this pod, at a
moment you pick — and it changes what this environment carries; the other way moves settled work
out of the slice.

**Recommendation.** Add the tool to this environment's config, and you restart the environment
before the run starts, at a quiet moment — after slice 027's planning. The Architecture phase
then gates like any other. Trade-off: one restart you time, and one more sidecar in the pod's
memory budget.

**The other way.** Take the Architecture edits out of this slice and do them as a change in the
Architecture environment, where its gates run. The slice keeps its other ten phases, and the two
criteria for the manual and the central update's contract pointer are owed after that work;
meanwhile the deploy repos point at `--help` before the central update's instructions and
environment can use it, and the manual keeps telling producers to copy a script the carriers have
just deleted.

**If this is wrong.** A restart at a bad moment interrupts running work, or the pod runs short of
memory, visible at start; under the other way, the Architecture half sits undone until someone
runs it there.

**Operator.** "Agree" (chat, 2026-09-25)

## D4 — Argo CD's redis edge: the per-container scoping covers the upstream wire as well as the capability, so the wire keeps its hard fail

**Context.** A premise correction first. The settled list below told you that, with a
per-container realizes and ConfigMap-sourced values, "the redis edge falls out of the existing
wiring". Read against the code, it does not. The upstream wire is declared on an image entry and
applies to every container of that image, and it fails the whole generation on any container that
does not set the named variable — a deliberate, documented hard fail. The Argo CD image also runs
containers that do not read the redis variable (only the server, repo-server and
application-controller do), so declaring the wire on the image would fail generation. The other
wire, boundBy, reads recipes that consumer producers publish against their own products; a
judgment layer has no way to author one. The plan's generator phase and its Argo CD phase are
written for the recommendation below, so agreeing needs no replanning.

**The ask.** The published model shows Argo CD and its redis side by side with no edge between
them; the card asks that the generator reach that edge, alongside the capability that puts Argo CD
in the Delivery pipeline view. The question is which mechanism draws the edge.

**Background.** The scoping this refinement already introduced lets a judgment layer name which
containers of an image an entry applies to; it was settled for the capability only. The value
that names redis is sourced from a ConfigMap, which the generator now resolves. What still keeps
the existing upstream resolver from the edge is the wire's image-wide reach.

**Why yours.** It corrects a settled item you were told, and the choice changes a guarantee every
producer relies on.

**Recommendation.** The container scoping covers the upstream wire too: Argo CD's deploy repo
declares the redis wire only on the containers that read it, and the existing upstream resolver
draws the edge from the value now resolved from the ConfigMap. The hard fail on a mistyped
variable stays. Trade-off: the judgment layer's scoping applies to two keys, not one — one
concept, documented in the help text.

**The other way.** An image-level upstream wire silently skips containers that do not set the
variable. No scoping of the wire is needed, but it softens the hard fail for every producer: a
mistyped variable that fails loudly today would pass silently.

**If this is wrong.** Nothing breaks; at worst the contract carries a scoping on one more key than
strictly needed.

**Operator.** "Agree" (chat, 2026-09-25)

## Open facts — questions only you can answer

None — nothing in this slice rests on something only you know.

## Settled

- Two of the validator copies sit in DesignAssistant and SomfyRemote, which are not registered
  producers and are archived on GitHub; they cannot be pushed and are left alone. Architecture's
  producer manual, which still tells producers to copy the script, is changed to point them at the
  toolchain.
- Alertmanager's dependency on the Telegram Bot API needs no generator work: the generator already
  lets a judgment layer declare that an image is served by a named service (four deploy repos use
  it in production), the Telegram service element is already declared in Architecture's shared
  external-services file, and Alertmanager still sends to api.telegram.org — so the fix is one line
  in PrometheusDeploy's judgment layer.
- The stale "generator's docstring" pointer is in all 48 deploy repos' instructions files (the
  cards said two) and in two of their architecture-file headers; `gen-architecture --help` today
  prints only usage and a one-line description, and the docstring behind it omits a key the
  generator already supports, so the help text is completed to the full contract before the
  pointers are switched to it.
- The Argo CD gap is wider than its card said: nothing in the estate realizes the
  configuration-management capability, so the Delivery pipeline view is empty on that predicate;
  the judgment layer gains a per-container realizes and the generator resolves an env value
  sourced from a ConfigMap against the same render, so Argo CD takes the view and the redis edge
  falls out of the existing wiring.
- The central architecture update runs its sessions in the Architecture repo's KubeCoder
  environment, which does not carry the aac-tools toolchain; to honour the `--help` ruling the
  slice adds the toolchain to that environment's config, effective at the environment's next
  restart — yours to pick, and central update runs are held anyway until the promotion-branch card
  lands.
- The central update agent's instructions in Architecture learn that a generated producer whose
  sources lack the generator takes its contract from `gen-architecture --help`.
- In-house service resolution looks only at the container behind the Service, and KubeCoder's
  deploy repo then maps the tunnel-reclaim image; that repo publishes from its prd branch, so the
  mapping lands on main and reaches the published model at the next KubeCoder promotion, which is
  yours and not this slice's.
- A generator change goes live estate-wide the moment ArgoCDTools is pushed, because every
  architecture build pulls the image's floating latest tag; before that push the run regenerates
  all 48 deploy repos' models with the old and the new generator and accepts only the intended
  differences.
- Out of scope: teaching the twelve app builds to skip unchanged code, the reason an
  architecture-only push redeploys them — a close-out observation, not this slice.
- Size: about 9 phases. Repos: ArgoCDTools (the generator); Architecture (the producer manual, the
  central update agent's instructions, its KubeCoder environment config); Ansible (the Argo CD
  runbook's template and the migration tool's template); all 48 deploy repos (a one-line pointer,
  plus judgment-layer edits in KubeCoderDeploy, ArgoCDDeploy and PrometheusDeploy); and about 28
  application and infrastructure repos (the validator migration).
