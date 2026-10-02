# P8 code review, round 1: KubeCoder's build file is in line with the guide

Range: `3f277a53..HEAD` on `phase/036-P8` in Ansible is empty. The phase's work is the one unpushed
commit `0b6ced99` in `/work/scratch/KubeCoder` on `main`, plus its ledger row. That commit is what
this review covers.

**Readiness: ready to merge.** `KubeCoder/Jenkinsfile` meets P8's outcome. It has the FILE-3 header,
and its `Controller config:` block matches the live job dump: `*/main`, script path `Jenkinsfile`.
`options {}` holds PROP-2's four entries in order, `Checkout` comes first with `checkout scm`, and
the `node` container is a named map. The old string entry derived that same name, so `container('node')`
still resolves. All eight images build through `helmCharts.kaniko2(dockerfile:, destinations:)`. The
context still defaults to `.` and the tracking tag still derives to `dev-latest`. Every label passes
LABEL-1–6, and `Test root` names a `.kubecoder/project.yaml` component.

I checked the old and new files command by command. Every gate command survives, and so do the eight
destinations and the pin map. The load-bearing order holds: the `npm ci` before both suites, each
suite before its packaging, the desktop packaging before the manual image, and `Test worker` before
`Validate CLI reference`.

`Lint` now runs `go vet ./...` before `Validate contracts` re-emits the contracts. That is safe:
every `go:embed` input it compiles, `tooldefs.json` included, is tracked. The controller's linter
answers "Jenkinsfile successfully validated." I ran it myself against the commit.

No consumer outside the repo keys on the old stage labels. I searched `track_build.py`,
KubeCoderDeploy's `Jenkinsfile.promote`, KubeCoderConfig and DockerImages. R17's P6 line
(`pipeline-dependencies.md:27`) now names `Validate architecture` and its `architectureProducer`
steps, as `Jenkinsfile.architecture:38-42` has them.

The review has two advisory findings and nothing blocking.

## Findings

### F1 — Minor · advisory · comment-prose · anchor: none · confidence: high

The commit renamed the stage references in KubeCoder's docs and comments, but it missed four places
that still cite the old labels as the stage's name:

- `vscode-desktop/scripts/package-extension.sh:9`: "It must run BEFORE stage('Build kubecoder-manual')". The stage is now `Build kubecoder-manual image` (`Jenkinsfile:387`).
- `worker/scripts/package-extension.sh:7`: "before stage('Build kubecoder-vsix')". It is now `Build kubecoder-vsix image` (`Jenkinsfile:324`).
- `packages/kubecoder-contracts/docs/go-codegen.md:56`: "CI's `Contracts drift gate` stage". It is now `Validate contracts`.
- `manual/mkdocs.yml:86`: "CI's \"CLI reference drift gate\"". It is now `Validate CLI reference`.

A reader searching the Jenkinsfile for the quoted label finds nothing, although the constraint
each comment states is still true. The plan's done-record says the doc phase does not see this
repo (`plan.md` P8 Record, last bullet). Nothing later in the slice will catch these.

### F2 — Minor · advisory · test-gap · anchor: none · confidence: high

`vscode-desktop/test/publish.test.ts:103-109` asserts that CI packages the desktop extension before
it builds the manual image, and that assertion cannot fail. Its
`indexOf('vscode-desktop/scripts/package-extension.sh')` first matches the comment inside
`Validate contracts` (`Jenkinsfile:124`), not the packaging step (`:219`).

I ran a mutation that moved `Build kubecoder-desktop.vsix` after `Build kubecoder-manual image`.
The test's comparison still held (6768 < 20611), while the real packaging step sat at 21208, after
the manual stage. That is the order the comment at `Jenkinsfile:207-213` says would silently
publish the previous build's artifacts.

This predates the phase: the old file had the same comment at `:101`. P8 edited only this test's
`stage(...)` string and kept the order correct.
