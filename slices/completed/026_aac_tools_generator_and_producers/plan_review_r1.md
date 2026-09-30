# Slice 026 — plan review, round 1

**Verdict: questions.** One finding needs an operator ruling (F1). Two blocking findings (F2, F3)
concern the R6 sweep's instrument and P5's gate. Two advisories follow.

**What holds.** I checked these and found no defect:

- **AC completeness.** V01–V15 cover slice.md's six requirements 1:1, in the cards' own words. R3
  is ruled out by D2 (V05), and R4 follows the triage ruling (V06–V09). Both `owed_after` items
  are real operator actions (V02: KubeCoder promotion; V09: Architecture restart and ARCH-14).
  No criterion falls to the doc phase.
- **Task shape.** `cross-cutting` fits. slice.md leaves R2's mechanism open ("a per-container
  realizes, or a wire that can read a ConfigMap-sourced value") and R6's carrier set unknown
  ("a cross repo scan").
- **Targets.** `run_loop.py --dry-run` resolves all 11. Each one is where its diff lands.
- **Code citations.** Every generator citation holds at `8914c0f`: `:935`, `:965`, `:977`,
  `:1008`, `:1017`, `:1078`, `:1224`, `:1282`, `:1348`, `:1388-1397` and `:1609-1614`. So do
  the Ansible citations (`Jenkinsfile.architecture:13`, `project.yaml:51`, `argocd.md:288-291`
  and `:330-340`, `argo_migrate.py:205-216`) and the Architecture ones (`producer-manual.md:6-11`
  and `:654-724`, `SKILL.md:149-150`, `update-architecture.md:47-48`, `delivery.yaml:10`,
  `capabilities.yaml:168`, `external-services.yaml:29`). The count of 48 `*Deploy` repos with
  the pointer, two of them with the header, is correct.
- **Independent derivation (R2).** I rendered ArgoCDDeploy prd. The `argocd` image runs these
  containers:
  - `REDIS_SERVER` as a `configMapKeyRef` on `argocd-cmd-params-cm`/`redis.server`
    (`argocd-prd-redis:6379`): repo-server, server, application-controller.
  - No `REDIS_SERVER`: applicationset-controller, notifications-controller.
  - One-shots: the `copyutil` init container and the `secret-init` Job.

  This matches D4's premise: an image-level `upstream` would hard-fail on two containers. The
  plan's expectation matches too.
- **Independent derivation (R1).** The controller Service's `target-port: "8080"` matches only the
  `kubecoder-controller` container's `containerPort: 8080` in `resolve_exposed_realizers`. The
  Service's real `targetPort` (8090) lands on the nginx `ingress` sidecar. So P1's scoping yields
  `svc:kubecoder-controller-api` only if it goes through the annotation, which is what P1 says.

---

## Operator-decidable

### F1 — Commits from another slice in this slice's target repos have no end state the run loop accepts

**Problem.** The plan knows slice 027 leaves unpushed commits in repos this slice pushes. Its
answer is push-sweep.md's rule: a default branch that carries commits that are not this slice's
"is not pushed. Record the repo in the ledger and leave it." For ArgoCDTools, P4 adds "Do not
push if … unpushed commits that are not this slice's". Neither says what happens next.

Three of those repos are phase Targets, and the driver requires Targets to be pushed.
run-loop.md § The push check: for every repo in `state.json`'s `bases`, the driver compares
`origin/<base>..<base>` before the doc phase. It nudges the test agent twice, then bails
`unpushed`. The plan declares no `## Push holds`.

**Evidence.**
- DockerImages `main` is one commit ahead of origin today: `1c1945a` (slice 027, promtool).
  DockerImages is P11's own Target. Nothing in P11 or the sweep pushes that diff, so the test
  phase pushes it, together with `1c1945a`. That contradicts V13 ("No commit that is not this
  slice's was pushed") and the attachment's rule.
- Slice 027 targets `../ArgoCDTools` (its P3) and `../PrometheusDeploy` (its P4). This slice
  targets both (P1–P3 and P6).
- `slices/DAG.md` was last updated 2026-09-20 and does not list 026 or 027. Nothing orders the
  two slices.

**Impact.** If 027's commits are still local when this run reaches those repos, one of three
things happens:
- P4 stops before publication.
- PrometheusDeploy (R5, V11) is left unpushed and the run bails `unpushed`. That comes after the
  prd rollouts and device flashes have happened.
- 027's work is pushed under this slice's name.

Which of these the operator gets depends on timing nobody has ruled on.

---

## Blocking

### F2 — The carrier enumeration and V12's proof rest on a GitHub code search that misses most of the carriers

**Problem.** The Grounding and P9 name the re-enumeration:
`gh api -X GET search/code -f q='filename:arch-validate.py user:pvginkel'`, "cross-checked
against `pipeline-producers.yaml`". They chose it because gitblit's sync is incomplete. V12
proves R6 done with the same instrument: "A GitHub code search finds only Architecture's
canonical `.claude/architecture/arch-validate.py` and the archived DesignAssistant and
SomfyRemote."

**Evidence (run 2026-09-25).**
- The search returns `total_count` 10: Ansible, Architecture, CalendarDisplay,
  ElectronicsInventory, InfraStatisticsDisplay, Intercom, IntercomServer, KitchenDisplay,
  NewsFilter, PaperClock. Page 2 is empty.
- `gh api repos/pvginkel/<R>/contents/…` shows the file on origin in repos the search omits:
  - DockerImages, HelmCharts, KubeCoder and SSEGateway (`scripts/arch-validate.py`);
  - the archived DesignAssistant and SomfyRemote;
  - ArgoCDTools (`aac-tools/image/arch-validate.py`, blob `8fc89c55`, the same as the carriers'
    copies).
- ArgoCDTools' copy is the toolchain's own source: its Dockerfile has
  `COPY image/arch-validate.py /usr/local/bin/arch-validate` at line 62. V12's closed list of
  exceptions leaves it out.

**Impact.**
- The cross-check against `pipeline-producers.yaml` recovers only registered producers. A
  carrier that is not registered and not in the Grounding list is invisible to the method.
- V12 cannot give a true result either way:
  - It can be ticked while copies remain, because the search already omits carriers that still
    hold the file.
  - Its expected output also can never match. The search never returns the archived pair, and a
    complete listing would include ArgoCDTools' copy, which V12 does not list.
- R6's "every copied arch-validate.py" is therefore unproven.

### F3 — P5's gate runs the pod's stale generator against a judgment layer written for P2's new key

**Problem.** P5's deterministic gate is ArgoCDDeploy's `kc project test`. Its last two
statements run `cexec aac-tools gen-architecture --stage prd --producer argocd-deploy` and
`arch-validate`. That is the pod sidecar's generator, pulled at the operator's pre-run restart
(D3), so it predates P1–P3 for the whole run. P3 says so, and P4 notes that its own gate "says
nothing". P5 gets no such note, and its case is worse.

**Evidence.**
- The old generator reads image entries with `img_ann.get("realizes")` and
  `img_ann.get("upstream")` (`:965`, `:977`). It ignores unknown keys, and it applies both
  realizes and upstream to every container of the image.
- Its env capture drops `valueFrom` (`:977`). All three `REDIS_SERVER` readers set that
  variable only through `configMapKeyRef`.
- An upstream wire the old generator sees at image level therefore fails on all five non-init
  `argocd` containers ("not set to a literal value", `:1609-1614`). The run then exits 1
  (`:1110-1114`).
- Whether it sees the wire at image level depends on the scoping syntax P2 picks. Neither P2
  nor P5 treats that as a constraint.

**Impact.**
- If the old generator reads the wire at image level, P5's gate is red in every fix round and
  the run ends in a `gate_red` bail. By then P4 has already published the contract estate-wide,
  so the shape can no longer change.
- If the old generator ignores the new key, the gate is green without testing P5.
- The loop-tail gate sweep re-runs the same gate after all phases.

---

## Advisory

### F4 — The sweep phases will likely hit the 2-hour executor cap, and a timeout ends the run

push-sweep.md says the ledger lets "a re-dispatch after a stop or a timeout" resume. But the
code-writer session cap is 7200s, and "A timeout is a bail, not a retry" (agent-dispatch.md
§ Timeouts). Nothing re-dispatches: the run stops until the operator relaunches it.

Each sweep phase waits on a lot of Jenkins work:
- P8 pushes 48 repos in batches of a few. Each batch waits for `AaC/<Repo>` and the downstream
  `AaC/Architecture`, which B1's loop keeps busy every ~6 minutes.
- P10 waits on twelve app builds and their rollouts.
- P11 waits on eight device flashes, one after another.

Expect a bail partway through the sweep, with the estate half-migrated until the operator
relaunches it.

### F5 — P8–P11 push outside their diffs before their review runs

Each sweep phase's own diff is a small part of its outcome:
- P8: the Ansible half. Its outcome includes 48 deploy repos.
- P9: Ansible. Its outcome includes about six more carriers.
- P10: HelmCharts. Its outcome includes twelve prd carriers.
- P11: DockerImages. Its outcome includes eight devices.

The executor commits the rest directly on each repo's default branch and pushes it during its
session, before the phase's code review. The reviewer sees only the ledger. A finding on a pushed
carrier commit can only be fixed with another push, which means another prd restart or device
flash.

D1 authorises the run to push. It does not say that the pushes come before review. For about 75
repos, the stop rules (a green build, a healthy rollout, a successful flash) are the only check
before a push. That is the operator's to accept knowingly.
