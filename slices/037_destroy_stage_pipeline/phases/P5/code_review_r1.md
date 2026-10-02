# P5 code review — round 1

**Range:** ArgoCDTools `d7db58f..fa32363` (`phase/037-P5`), one file: `Jenkinsfile.destroy-stage`.
Gate: `kc project test` green on `fa32363` (`gate_r1.log`), taken as given.

**Readiness: ready to merge.** The pipeline delivers P5's outcome. The guard runs before any Job
and checks both things Ruling D2 names. The registry check (`:47-57`) reads `main` and compares
repo URLs case-insensitively, with `.git` and a trailing `/` dropped. The live check (`:67-81`)
counts single- and multi-source Applications, so it matches the shapes the registry template
renders (ArgoCDDeploy `releases/templates/applications.yaml`). The failure names every deployer
it found, and REPO must be spelled as GitHub spells it (`:228-232`), which closes Review P4 r1's
gap. The Job manifest renders to what P4's done-record asks for (parsed here): `argocd-hooks`,
`destroy-stage-<build#>`, `tf-presync`, `argocd-hook-credentials` through `envFrom`,
`argocd-hook:latest`, a `command` override with `args` plus `--apply`, `backoffLimit: 0` and a
1800 s deadline. The build calls only the `kubectl` steps P3 allows. The agent runs as
`destroy-stage` (`:155`). `APPLY` defaults to false, and an apply removes `config/<stage>/` only
after the Job has succeeded (`:308-339`). That stage clones and pushes inside `withCredentials`,
as `cicd.writeVersionPins` does. Re-runs skip a missing state or folder. The parameter-less build
fails on the empty `REPO` before any kubectl call.

The file follows the style guide (FILE, PROP, CHK, SEC, POST-3, LABEL, GRAN rules), and the
controller's declarative linter validates it ("Jenkinsfile successfully validated", run here).
Its Groovy constructs all have precedent in the estate's other sandboxed Jenkinsfiles:
`stripIndent` (FieldnotesApp, SSEGateway), `==~` (KubeCoderDeploy `Jenkinsfile.promote`) and
`readJSON` (DockerImages). The `k8s` sidecar is alpine/k8s and has the `curl` and `git` the
stages call. `kubectl get applications` resolves to `argoproj.io` alone on prd. The job
`IaC/Destroy Stage` exists with `<properties/>`, `*/main` and `Jenkinsfile.destroy-stage`, and
has no builds (`nextBuildNumber` 1). The three findings below are advisory. The guard's helpers
have no committed test, which close-out T3 already records.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high
**A destroy Job that overruns its deadline, or whose pod never starts, fails the build without
the Job's log or the reason.** `runDestroyJob` waits with `kubectl.waitForJobContainer`
(`Jenkinsfile.destroy-stage:129`) before it saves the log (`:131`). Two paths make that wait exit
1:

- **The Job passes its 1800 s deadline (`:112`).** Kubernetes deletes the pod, and the library
  exits with `Pod … no longer exists while waiting …` (JenkinsPipelineUtils
  `vars/kubectl.groovy:70-73`).
- **The pod never starts** (image pull failure, a missing Secret). The wait runs the full 30
  minutes, then ends the same way, or with `Job … failed before pod was created` (`:55-61`).

Either way the step throws, so the build never shows the Job's log, and `finally` deletes the Job
(`:144`). The `getJobFailReason` branch (`:135-137`) cannot catch these paths. It runs only when
a terminated container reports no exit code, and a terminated container always has one. A pod
that is gone makes `getContainerExitCode`'s `kubectl get pod` fail before that branch is reached.
The build does fail. What is lost is the record of what a killed destroy had already done, and
the reason for a 30-minute wait. Close-out **B3**.

### F2 — Minor · advisory · anchor: none · confidence: high (facts), the trigger is future-only
**The spelling check assumes the state folder is spelled as GitHub spells the repo, and nothing
holds the registry to that.** The hook files state under `hook.repo`, which is the registry
entry's URL as written. `releases/values.schema.json:46-50` lets that URL use any case. The
guard requires `REPO == .name` from GitHub (`:228-232`). Suppose an entry spelled a repo
otherwise:

1. its stage's state would lie under `argocd/<registry spelling>/`;
2. the guard would refuse that spelling and say `run with REPO=<GitHub's>`;
3. the build would then find no state, exit 0 with `nothing to destroy`, and on apply remove
   `config/<stage>/` (`:308-339`), leaving the resources and state behind.

Today every one of the 49 registry repos matches GitHub's `.name` exactly (`gh api`, checked
here), and so does every one of TerraformState's 48 `argocd/` folders. Nothing goes wrong now.
Close-out **I3**.

### F3 — Minor · advisory · anchor: none · confidence: high
**The style guide's pipeline types index is now false.** JenkinsPipelineUtils
`docs/pages/types/index.md` opens with "Every Jenkins job in the estate but those at the end of
this page is of one of these types". `IaC/Destroy Stage` fits none of the 13 types: it is not a
Validation Job, a Configuration apply or a Promotion, and the page does not list it at the end.
The omission is the same kind as close-out P4 (PROP-3's table), so it is a note on **P4**, not a
new entry.
