# Code review — slice 030, P1, round 1

Range: JenkinsPipelineUtils `6f87d09..f08b4da` (`phase/030-P1`), one file, +14 lines.

**Readiness: ready to merge; no findings.** P1 is meant to add a `containerTemplates` entry for
`registry:5000/kube-coder-modern-app-toolchain:node-24`, running as uid 1000, placed beside
`iac_toolchain`, with `modern_app_dev` left in place. `vars/containerTemplates.groovy:62-64` does
all of that. The entry sits directly after `iac_toolchain` (`:52-56`), and `modern_app_dev` is
unchanged (`:103-105`). The gate is green, and origin `main` is at `f08b4da`, as ruling A1 and the
Ordering constraints require. The review checks were:

- **The image exists under the name the template uses.** The registry lists
  `kube-coder-modern-app-toolchain` with `tags: ["node-24"]`, the only variant its matrix builds
  (`DockerImages/kube-coder-modern-app-toolchain/build-matrix.json`).
- **The new image covers what the moved stages use from `modern-app-dev`.** P3 and P4 run
  `uv sync`, `uv run ruff|pytest`, `npm ci` and `npm run typecheck` (`KubeCoder/Jenkinsfile:37-87`,
  `FieldnotesApp/Jenkinsfile:24-31`), and the FieldnotesApp suites need a real `git`. Each tool is
  in the new image's chain:
  - uv, poetry and ruff: `kube-coder-modern-app-toolchain/Dockerfile`
  - Node 24 and npm: `kube-coder-frontend-toolchain/Dockerfile`
  - git: `kube-coder-dev-base/Dockerfile:40`

  `modern-app-dev` carried no `USER`, no git identity and no `safe.directory` config, so the new
  image loses none. Its only `HOME`-dependent setting was an npm `prefix` in `~ubuntu/.npmrc`,
  which `npm ci` does not use.
- **The doc comment is accurate** (`:52-61`). The toolset list matches the Dockerfiles. The
  comment says `COREPACK_HOME`, `PNPM_HOME` and the store dir point at home-overlay paths, and
  `kube-coder-frontend-toolchain/Dockerfile:29,46-47` confirms that. The comment gives the reason no
  env override is needed, much as `iac_toolchain`'s comment does. It does not narrate history.
- **The done-record's P5 note fits the Job it will be used for.** The note is conditional on
  "uid 1000". The validation Job runs as `runAsUser: 1000`
  (`ModernAppTemplate/root/template/Jenkinsfile.jinja:68-69`), so the condition holds.
- **Test coverage.** `LibraryCompileTest` compiles every `vars/*.groovy`, so the new method is
  compiled. No test asserts the image string or pod behaviour. The library has no such test for
  any template, and the phase's own outcome does not call for one. P3's and P4's Jenkins builds
  are the live proof. No acceptance criterion is left uncovered at P1's scope: V09's "the
  library's modern-app toolchain template … is present" holds.
