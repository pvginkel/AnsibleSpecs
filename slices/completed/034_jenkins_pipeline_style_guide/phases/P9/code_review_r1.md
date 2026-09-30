# P9 code review, round 1: the site image and the library's build job

Range: JenkinsPipelineUtils `ab605b7..973257a` (`04d0198`, `973257a`) on `phase/034-P9`.

**Readiness: ready to merge. There are no findings.** The phase delivers every part of its outcome:

- **Image.** `docs/Dockerfile` runs `uv sync --locked`, then `mkdocs build --strict` and `check_site.py` in `docs/`, with `vars/` beside it (repo-root context). It serves `docs/landing/` at `/` and the build at `/docs/` from `nginx:alpine` on port 80, with `absolute_redirect off`, and runs `nginx -t` at build time.
- **Wiring into PipelinesDeploy.** The image name (`registry:5000/pipelines-home`), the port (80) and the pin (`images.pipelines` in `config/prd/values.yaml`, value `:<build#>`) match the chart P8 left in `/work/scratch/PipelinesDeploy` (`chart/templates/pipelines-deployment.yaml`, `pipelines-service.yaml`, `config/prd/values.yaml`). The pin also fits `cicd.applyPins`'s dotted-path lookup and `kaniko2`'s tracking-tag rule (`:N` + `:latest`).
- **Jenkinsfile.** The root `Jenkinsfile` has the shape of `docs/examples/image-build.groovy`. I checked it against FILE-1–7, PROP-1/3/6, CHK-1/3, POD-3/4/6, TIME-1, GRAN, LABEL-2 (`Build <image> image`, `Write image pins`) and POST (`abortPrevious: true`, so no `post { aborted }`) and found no deviation.
- **Job.** `IaC/JenkinsPipelineUtils` is live. Its `config.xml` equals the saved copy (`jenkins-config/xml/IaC/JenkinsPipelineUtils.xml`). It carries `GitHubPushTrigger`, `*/main` and `scriptPath` `Jenkinsfile`, and it has no builds. The library's single Jenkins push hook is in place.
- **Manifest.** The manifest's header now states the one job accurately. `jenkins:` sits on `root`, as KubeCoder's `project-yaml.md` puts repo-level keys, and `docs` gains a `build:` verb.

Targeted runs, all on `973257a`:

- `kc project lint docs` was green: the 14 examples plus the root `Jenkinsfile` all passed the controller's linter.
- `kc project build docs`, the committed build verb, exited 0. The builder's strict build, `check_site.py` and `nginx -t` all passed in the image.
- A read of the live job (`config.xml` identical to the saved copy; `builds: []`) and of the library's hooks (one Jenkins `push` hook).

Checked and not raised:

- **The allowlist `.dockerignore` (`*`, `!docs`, `!vars`).** No other estate kaniko build uses this pattern. Moby pattern semantics admit `docs/**` and `vars/**` and exclude the rest, and a fresh Jenkins workspace has no `docs/.venv` or `docs/site` in any case. A misread would fail loudly at `COPY` in the first build, not ship something wrong.
- **The job's push trigger before the Jenkinsfile is on `main`.** It only matters if something pushes the library before the test phase. The first build of a job with no builds polls as incomparable, so that push would start a build, and the build would fail red for lack of a Jenkinsfile and write no pin. The plan orders the job's creation into P9 and the first push into the test phase.
- **No `error_page` for MkDocs' `404.html`, and no gzip.** Neither is in the outcome, and the manual precedent serves without the former too.

No close-out entries: this round has no advisory findings.
