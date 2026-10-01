# Slice 036 — plan review r1

Reviewed: `plan.md`, `verification.json`, `attachments/consumer-files.md` at AnsibleSpecs `cfe3adf`,
against `slice.md`, `refinement.md`, the library and guide in `/work/JenkinsPipelineUtils` (`e62b3dc`),
and the consumer clones (all clean and level with origin today).

What holds: R1–R18 map 1:1 onto V01–V18 in the operator's wording, and V19–V25 add the rulings and
the jobs that only prove their files on a later run. The task shape (`cross-cutting`) fits: the
work spans the library, about 40 consumer repos, Ansible and KubeCoderConfig, and sets a new
library-step pattern. Every `Target:` resolves to the right place. P4/P5/P6/P8 use `root` plus a
ledger, as slice 035 did. KubeCoderConfig is adopted in `/work/scratch` and has a manifest. The
phase order puts the library first and its cleanup last. The attachment stays at the right level
of detail, and the plan has no auto-doc section. I checked the load-bearing citations against the
code: podYaml `:70-75/:115/:126-127`, containerTemplates `:46-49`, helmCharts `:20-27`, library.md
`:61/:64/:69`, the type pages, PaperClock, ha-fleet, YouTrackConfiguration, IoTSupport `:99-107`,
`Jenkinsfile.architecture:57`, the ArgoCDTools README and the KubeCoder doc line. They all hold. I
also derived the caller set of the describables and the positional kaniko independently. It
matches G5: 34 positional sites in 20 in-scope files, plus CanonApp. KitchenDisplay calls only
`rsync`/`dockbuild`. The `KEYCLOAK_*` globals are read only by IoTSupport's two files.

## Operator-decidable

### Q1 — R18's "Each push still needs the operator's OK" is dropped, and nothing in the rulings replaces it

**Problem.** slice.md R18 ends: "Each push still needs the operator's OK." (`slice.md:170-171`). The
plan's R18 stops one sentence earlier (`plan.md:73-78`). Its Ordering constraints then have the
test phase push every repo in one go with no stop (`plan.md:250-261`). That is about 45 repos,
including JenkinsPipelineUtils (which rolls pipelines.home to prd), the 22 pin writers (prd
rollouts), the eight firmware jobs (OTA re-flashes), KubeCoder (rolls `kubecoder@dev`) and
KubeCoderConfig (the skill marketplace). The rulings section has no ruling that authorises this.
Ruling D3 covers only the GitHub renames and the Jenkins job and global writes ("No per-write
confirmation"). Slice 035 had exactly such a ruling, its Ruling P1: "starting `/dev:run-slice` on
035 is the operator's OK for the one push … This authorises the run to push every repo the slice
touches, including repos that are not a phase's `Target:`, and to roll prd through those pushes"
(035 `plan.md:94-104`). 036 has no counterpart.

**Impact.** Nobody downstream reads slice.md. The test agent therefore pushes the whole estate on
the plan's word, and the operator's stated gate is lost. The other possibility is that some session
honours the user-level "Re-ask on every push" rule and stops the run mid-push, with no ruling to
point at.

### Q2 — SEC-1 forbids `withVault` around a test, and IoTSupport's suite needs a secret. The plan requires SEC-1 compliance anyway, without a ruling

**Problem.** SEC-1 says: "`withVault` MUST NOT wrap `pipeline {}`, the agent, the checkout, a lint or
a test" (`docs/pages/guide/secrets.md:8-9`). IoTSupport's validation suite needs the Keycloak admin
client. The app reads `KEYCLOAK_ADMIN_CLIENT_ID`/`_SECRET` (`backend/app/app_config.py:64-65`), and
today's file hands them to the Job (`IoTSupport/Jenkinsfile:27-32, 102-105`). P3 says "`withVault`
wraps only the steps that use it" (`plan.md:380-386`). V22 says "`withVault` wraps only the steps
that use its secret (SEC-1)". Neither acknowledges that the step which uses this secret *is* the
test. The plan rules on SEC-2 and SEC-4 for the Job manifest, but not on SEC-1's ban.

**Impact.** No form of the IoTSupport file or of the P3 step can comply with SEC-1 as written. The
executor may drop the secret, which turns the suite red. Under the plan's own ordering that also
blocks the `KEYCLOAK_*` deletion (V13), which waits for IoTSupport to go green. Otherwise the
code-reviewer flags SEC-1 on P3 and P4 every round. The guide is the operator's, so only the
operator can say how its rule meets this suite.

### Q3 — V01 says the firmware files become "a few lines". S1's design leaves them near reference length, and no ruling records that trade-off

**Problem.** V01 says: "'The pipelines that can become a few lines' (the firmware files) are a few
lines on library steps." S1 keeps each firmware file's own header, `pipeline {}`, agent, `options`,
`triggers`, a `Checkout` stage that clones the repo and `esp-libs` (plus `opentherm_library` for
ThermostatProxy), the build and deploy stages, and the abort `post` (`plan.md:110-119`, P2
constraints). The steps take over two `sh` lines in the build, and the `withVault` plus upload in
the deploy. Today's reference file is 94 lines (`docs/examples/firmware.groovy`). A file on the
steps is in the same range. Slice 035 met the same conflict between the guide and "a few lines",
and the operator ruled on it: "Accepted trade-off: the files are ~40 lines, not 'a few lines'"
(035 `plan.md:91`). 036's S1 is settled by the session, records no such trade-off, and the
criterion claims the opposite.

**Impact.** The test agent will either fail V01 or pass it on a stretched reading of "a few lines".
Either way the operator's R1 request is softened without a ruling. (V04's "…is green, so its
devices took the upload" makes a similar over-claim: a green build shows that the upload to
IoTSupport succeeded, not that the devices flashed.)

## Blocking

### B1 — The push mechanics leave AaC/Architecture exposed during the churn, so V18 cannot hold as written

**Problem.** Slice 035 paused `AaC/Architecture` for its push and built it once at the end (Ruling
P1). Its plan review (r1 B5) had found that the collector is downstream of every `AaC/*` producer,
with `abortPrevious=true`, so each producer success during churn starts it or aborts its running
build. 036 lists that pause only as history (G11, `plan.md:235-240`). Its Ordering constraints
neither keep the pause nor order Architecture's push ahead of the other consumers. They also forbid
starting a job by hand (`plan.md:280-282`). Two scenarios follow, both derived from the code rather
than from the plan:

- The library goes out first with P11's deletions. The next consumer pushes start their `AaC/<Repo>`
  twins, each of which takes a minute or two. Each success starts `AaC/Architecture`. Until
  Architecture's own push lands, that build runs the live file, which calls
  `containerTemplates.k8s`, `containerTemplates.python` and the positional `helmCharts.kaniko`
  (`/work/Architecture/Jenkinsfile:39-40, 141`). Those calls fail against the stripped library.
- After that, dozens of upstream successes re-trigger the collector: the app twins, plus the
  `AaC/*Deploy` jobs that the ~22 pin commits start. The migrated file keeps
  `disableConcurrentBuilds(abortPrevious: true)` (`architecture-collector.groovy:28`), so running
  collector builds are aborted one after another. Each one that completes pins `architecture_viewer`
  into WebathomeOrgDeploy, which is a prd roll.

**Impact.** V18's "Every build the push started finished SUCCESS" fails on red or aborted collector
builds that the plan itself sets up. The test phase then turns this into appended phases or a
failed criterion. 035's review already caught this; 036 brings it back.

## Advisory

- **A1 — P11's precondition is checked at a time when origin still holds the unmigrated files.**
  P11 checks that "no Jenkinsfile on the branch that an enabled Jenkins job builds calls what this
  phase removes", with the branches taken from the live job list (`plan.md:591-595`). Nothing is
  pushed until the test phase. On origin, all 40-odd consumer files still call the describables,
  and the four renamed repos' jobs still build `*/master`. The text does not say that the check reads
  the ledger's local commits. It also does not say what P11 does when it finds a caller outside the
  slice's files. An executor that reads it literally blocks.
- **A2 — The KubeCoder push rolls `kubecoder@dev` outside KubeCoder's own devlock.** KubeCoder's
  `CLAUDE.md:48-52` says: "Pushing `main` rolls `kubecoder@dev`, and the run loop arranges that
  itself … takes the spec repo's devlock". That lock lives in KubeCoder's environment, and this run
  cannot take it. If a KubeCoder slice is in its test phase when 036 pushes, dev is rolled under it.
  The plan (S8) names the dev roll, but not this collision. The operator may want to know before
  the push.
- **A3 — The doc phase cannot see the ledger repos.** The ledger repos are not in the run's
  `bases`, so their docs fall outside the doc phase's diff (`docs/slice-doc-plan.md` § Other repos:
  "A repo the slice did not touch gets no commit"). Two of them name the overload P11 deletes:
  `NewsFilter/README.md:116` and `DHCPApp/docs/slice-test-plan.md:15` (`helmCharts.kaniko(...)`).
  `Home/docs/plan.md:270-283` quotes a scripted `podTemplate` with `containerTemplates.helm`. These
  go stale with no one owning them.
