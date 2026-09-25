# Slice 027 — refinement

## D1 — The modern-app-dev retirement leaves this slice for a slice of its own

**Context.** This slice carries three build/test gates you agreed at triage on 2026-09-24 — a
Groovy check for the shared Jenkins library every job loads, a test stage before the Argo CD tools
job publishes its two images, and a promtool check over prd's alert rules — plus a fourth item
bundled the same day: retiring the last two pre-KubeCoder dev-container images, modern-app-dev
(1.2 GB) and modern-app-dev-playwright (1.6 GB, built on it), and moving their consumer pipelines
elsewhere. Triage bundled it because its work sits where the gates' work sits: the pipelines that
pick build and validation images, and the shared library's container templates. Your stated sweet
spot is about seven phases per slice.

**The ask.** The retirement is done when nothing outside DockerImages references either image, the
two image directories are removed, the modern-app-dev container template is gone from the shared
Jenkins library, and the registry repositories are deleted.

**Background.** modern-app-dev reaches three pipelines through the shared library's container
template: KubeCoder, FieldnotesApp and the homelab Terraform provider. modern-app-dev-playwright is
hardcoded — image and Playwright-version tag, no library indirection — in five app validation
pipelines: DHCPApp, ElectronicsInventory, IoTSupport, ZigbeeControl and DesignAssistant, which the
card missed; and in the frontend app scaffold template, so apps generated from it reintroduce it.
That is eleven repos to change besides DockerImages and the library, about thirteen phases on its
own; seven of those repos are not checked out in this environment and would have to be added to
its configuration first. Two existing toolchain images already fit three of the base-image
consumers (Node plus Python for KubeCoder and FieldnotesApp; the iac toolchain for the Terraform
provider). The genuinely open design question is the Playwright browser base for the five
validation pipelines — no current toolchain image carries browsers. The registry deletion is
irreversible, and you have so far deliberately held off deleting registry images.

**Why yours.** It is the slice's shape — what ships together — and you bundled the retirement
here yourself.

**Recommendation.** Split it out now into its own backlog slice, its card moving under it, planned
in its own session; this slice keeps the three gates at about four phases. The trade-off: two
planning sessions instead of one, and the retirement's slice builds on a container template for
the iac toolchain image that this slice adds for its test stage.

**The other way.** Keep it here — about seventeen phases across thirteen repos, the seven missing
repos added to this environment before the run, and the Playwright base decided in this
refinement.

**If this is wrong.** Nothing is lost but order; the retirement is planned a little later.

**Operator.** Agree (2026-09-25, in chat).

## D2 — The Prometheus deploy repo gets promtool unit tests for its alerts, not only a syntax check

**Context.** When the Prometheus release moved to its own deploy repo, your ruling of 2026-09-24
retired the old Helm monorepo's five alert tests for two stated reasons: deploy repos run no tests,
and those tests checked alert timings against backup CronJobs in other apps, which a copy in the
Prometheus deploy repo could not follow. prd's rules now live in that repo's prd values — five rule
groups, eight alerts: three memory-pressure, one node-reservation, S3 mirror staleness, YouTrack
backup staleness, and two backup-freshness. Nothing reads them in any test. The repo's local test
verb already renders the chart, runs its Terraform checks and validates its architecture artifact.
None of the 48 deploy repos has a Jenkins test stage; Argo CD deploys from main. prd runs
Prometheus 3.14.0, and no toolchain has promtool today.

**The ask.** The card asks for promtool in the iac toolchain so alert rules are unit-tested; its
stated consequence is that a PromQL precedence or matching mistake in a rule passes the gate and
first shows once Prometheus evaluates it. At triage the same day you called it "Good one" and it
moved to the Prometheus deploy repo. A second report adds the heavier failure: a syntax or
annotation-template error makes prd reject the reloaded rules file and keep evaluating the old one,
so the new alert never fires and nothing says so.

**Background.** promtool's syntax-and-template check catches the silent reject but not a precedence
or matching mistake; only rule unit tests — synthetic series fed to the rules, expected alerts
asserted — catch that. Such tests are self-contained: synthetic series, not other apps' CronJobs,
so the coupling that retired the old tests does not come back. An earlier slice already ran
promtool scenarios over the memory-pressure rules and they worked — starvation fires both stall
alerts; a wedged node fires only the wedge warning and holds through a 60-minute memory dip; a
reboot resolves it; a healthy memory-tight node stays quiet; overlapping chart-label series give
one alert per node — but they were never committed.

**Why yours.** Your "deploy repos run no tests" and your "Good one" on this card both stand; which
one governs the Prometheus deploy repo is yours to say.

**Recommendation.** Both: the syntax-and-template check over the rules as the chart renders them,
plus promtool unit tests covering every alert present today — a firing and a quiet case each, the
memory-pressure group carrying the scenarios already witnessed — run by the repo's local test verb,
which slice phases run as their gate; no Jenkins stage. The trade-off: the repo carries rule test
files that must be edited with every rule change, and nothing forces a future alert to come with a
test.

**The other way.** The check only — a lint-level gate like the chart lint the repo already runs,
honouring "deploy repos run no tests" to the letter; it leaves the card's own consequence, a
precedence or matching mistake, uncaught.

**If this is wrong.** Tests wrongly cost some test files to delete; check-only wrongly lets a
semantic rule mistake reach prd's alerting silently.

**Operator.** Agree (2026-09-25, in chat).

## Open facts — questions only you can answer

None — nothing in this slice rests on something only you know.

## Settled

- Every card's claims were re-checked on 2026-09-25 and hold; nothing is overturned.
- Two toolchain changes land during planning, before the run — this environment gains the Java
  toolchain sidecar (one line in its KubeCoder config, 1 GiB memory limit) and the iac toolchain
  image gains promtool — followed by one environment restart you run, which recreates the pod and
  ends every session in it; it cannot be a phase, since a run cannot survive its own pod restart
  and each gate needs its tool present to go green in its phase — so the procedure is: confirm the
  two pushes, restart the environment before starting the run.
- The Groovy gate compiles every library file through the Jenkins pipeline engine's own transform
  with the Groovy version Jenkins runs (2.4.21), not a bare parse — a superset an earlier slice ran
  successfully in this environment, catching constructs the engine refuses at load time as well as
  syntax errors; it does not catch the serialization hazards a resumed build trips on, which still
  need reading; its libraries come through Maven on the Java toolchain rather than the card's
  hand-downloaded runtime in a temp directory.
- The Argo CD tools job runs the repo's own suite before either image build, in the iac toolchain
  image — the same image its local test verb uses — and a red suite publishes nothing; the shared
  library gains a container template for that image, which the retirement will reuse.
- The shared-library gate and the Prometheus rules gate are local pre-push gates (the repo's test
  verb, which every slice phase runs as its gate), not Jenkins stages: the library has no job of
  its own, and no deploy repo tests in Jenkins.
- promtool is pinned to prd's Prometheus version, 3.14.0.
- Size: with D1 as recommended, about four phases in three repos — the shared Jenkins library, the
  Argo CD tools repo, the Prometheus deploy repo — plus the two toolchain changes landed before the
  run; with the retirement kept in, about seventeen phases across thirteen repos.
