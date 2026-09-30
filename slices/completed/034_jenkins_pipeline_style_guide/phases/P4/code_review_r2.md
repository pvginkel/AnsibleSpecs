# Code review — slice 034, phase P4, round 2

Range `d5f3dcb..be5bb39` (AnsibleSpecs `phase/034-P4`). `76d0db7` is round 1's own close-out
commit. The fix commit `be5bb39` touches `rulings.md` §2, §5 and §14, and the P4 done-record in
`plan.md`.

**Readiness.** Round 1's §2 and §14 findings are resolved. §5's sub-choice is now on the page, and
its facts are correct. But the text for option (a), which is Claude's lean, understates what (a)
costs: it says the gap reaches only the guide's reference files. It also reaches this slice's own
live deliverable, P8's `Jenkinsfile.architecture`, whose first build V14 requires to be green
(F7). That is a one-place correction on the page. Nothing else in the fix commit is wrong beyond a
nit in §14 (F8).

**Gate state.** AnsibleSpecs has no suite, so the gate is unverified, but that has no bearing
here. Every finding comes from reading the page against the library source and the plan. The
`podYaml` refusal F7 relies on is plain in the code (`JenkinsPipelineUtils/vars/podYaml.groovy:37-39`)
and pinned by `PodYamlTest.java:256-289`. I did not re-run that test.

## Round-1 blocking findings, re-opened

- **r1 F1 (§5 relies on templates that do not exist): resolved as asked.** `rulings.md:239-253`
  now puts (a), extend `podYaml`, against (b), inline `images:` entries. I checked each fact
  against the source:
  - "It has two" is true (`podYaml.groovy:69-73`), and so is "any other name throws" (`:37-39`).
  - The four named sidecars are the ones `containerTemplates` declares beyond `k8s` and
    `modern-app-toolchain` (`vars/containerTemplates.groovy:12-78`), leaving out `dockbuild` and
    `rsync`.
  - Their users match the inventory (`inventory.md:361-368`): `python` in T8, T10 and T11 is
    YouTrackConfiguration, DockerImages and Architecture. Home's `helm` is on §5's retire list.
  - `iac_toolchain` does carry a uid and an environment (`containerTemplates.groovy:46-47`).
  - The response slot takes the sub-choice (`rulings.md:283`), and the done-record passes it to
    P5 (`plan.md:466-467`).

  The fix's wording introduces a new problem; see F7.
- **r1 F2 (rule 6 against §13): resolved.** Rule 6 (`rulings.md:95-96`) now allows a computed
  label only for a section-13 generator. The retire entry (`:124`) is scoped the same way. §13's
  DockerImages bullet (`:638-643`) calls itself the one such place, and Intercom's labels are
  constants (`:652-653`). The three texts agree, and rule 6 is still a string check.
- **r1 F3 (a scheduled job's cron never registers): resolved.** Step 4 (`rulings.md:715-717`)
  now starts a non-push job's first build through the API. It says that this build is what puts
  the file's `triggers {}`, a cron included, on the job. That matches P1's result
  (`plan.md:259-261`). A new job is created without `parameters`, so a plain `/build` is
  accepted. For the path of a job in a folder, see F8.

## Findings

### F7 — Major · blocking · anchor: repro-trace · confidence: high

**§5's option (a) says the missing templates affect only the guide's reference files. They also
break the first build of P8's `AaC/PipelinesDeploy` producer, which this slice must get green.**

Option (a) (`rulings.md:245-247`) says:

> That changes a library var, so the migration slice does it, before the first file that names
> one. Until then the guide's reference files name templates that do not exist.

That is Claude's lean (`:252-253`), and the done-record tells P5 the same
(`plan.md:466-467`). But this slice itself writes a file that names one of these templates and
has to run:

- **P8 writes a T2 producer to the guide.** P8 writes PipelinesDeploy's
  `Jenkinsfile.architecture` "written to the guide" (`plan.md:588-589`). It is a T2
  deploy-repo producer. All 72 T1/T2 files run their `gen-architecture`/`arch-validate` steps
  in the `aac_tools` sidecar (`inventory.md:362`). P8's precedent,
  `ChartsDeploy/Jenkinsfile.architecture`, does the same with `containerTemplates.aac_tools`.
- **Its first build must be green.** V14 requires "`AaC/PipelinesDeploy`'s first build is
  green and archives the producer's artifact". The test phase's ordering puts that build ahead
  of the Architecture and ArgoCDDeploy pushes (`plan.md:220-224`), so V12's site-live check
  waits on it as well.

Repro: the operator rules (a), per the lean. P5 then writes the guide's pod rule with
`aac_tools` under `templates:`, and P6 writes the T2 reference file with it. §12's lean (a)
makes that reference file the full declarative file, not a helper call. P8 writes the producer
to that guide. The file passes the linter, because the linter never evaluates the agent's `yaml`
expression. In the test phase, `AaC/PipelinesDeploy` build #1 fails with
`podYaml: the library has no template 'aac_tools'; it has k8s, modern-app-toolchain`
(`podYaml.groovy:37-39`). V14 fails, and the P11 and ArgoCDDeploy pushes are held behind it.

The only ways out are the ones the page did not show the operator, so the decision comes back
mid-run:

- add the template in this slice, which the page's own text assigns to the migration slice and
  which touches V19's "no library var changes what it does";
- let the slice's first guide-conformant file depart from the ruled guide.

The page also argues against itself. §12 rejects option (b) because a guide that names a call
that does not exist leads a session to "write a Jenkinsfile that fails" (`rulings.md:610-611`).
It recommends its own (a) because "the guide names only calls that exist" (`:603-604`). With §5
at (a), that argument no longer holds for T1 and T2, and the page does not say so.

### F8 — Minor · advisory · anchor: none · confidence: high

**§14 step 4 gives no path for starting a job in a folder.**

Step 2 gives the folder form of `createItem` (`rulings.md:709-710`). Step 4 gives only
`POST /job/<job>/build` (`:715`). A hand-started or scheduled job placed in `IaC/` or `AaC/`
per step 6 answers at `/job/<Folder>/job/<job>/build`, so following step 4 literally gets a 404.
The failure is loud, and the fix is local. Entered as close-out P9.
