# P2 — Publishing: package, index, and the chart-repo image — code review r1

**Commit under review:** `6da54f8` on `phase/006-P2` (`git diff 5b99e9e..HEAD`, `/work/Charts`)
**Gate:** green on this commit (`kc project test` — both `tests/render-consumer.sh` and
`tests/publish.sh`), taken as an input.

## Readiness

The phase lands its outcome. `dist/homelab-shared-0.1.0.tgz` is committed; `tools/build-index.sh`
regenerates a full-directory index whose entry URLs are absolute under `https://charts.home`
(`dist/index.yaml` regenerated during this review carries
`https://charts.home/homelab-shared-0.1.0.tgz`, `type: library`, and a digest);
`Dockerfile` + `nginx/default.conf` bake tarballs and index into `nginx:alpine` and serve them at
the repository root over plain HTTP on :80; the `Jenkinsfile` runs the index step in
`containerTemplates.helm` and pushes `registry:5000/charts-home:<build>` **and** `:latest` through
`helmCharts.kaniko2` — a destination pair `resolveTrackingTag`
(`/work/JenkinsPipelineUtils/vars/helmCharts.groovy:144-165`) accepts — then calls
`cicd.helmDeploy()`, which is the estate's `build job: 'IaC/HelmCharts'`
(`/work/JenkinsPipelineUtils/vars/cicd.groovy:1-3`). The interface P3 was written against
(`registry:5000/charts-home`, port 80, `/index.yaml` at the root) is delivered. V07's additivity is
proven by real execution rather than inspection, in the sequence the repo actually goes through
(`tests/publish.sh:70-88`), and I confirmed the stale-`dist/` assertion bites by mutating
`charts/homelab-shared/values.yaml` and re-running the gate (red, with the offending diff printed).
I also ran the uncovered half — `kc project build` — end to end: `tools/build-index.sh` then
`kaniko --context . --no-push` both green, so the Dockerfile guard (`test -f …/index.yaml &&
nginx -t`) and the vhost are real rather than asserted. Note the image build sits under `build:`,
outside the loop's `test:` gate, which is the manifest convention (`/work/KubeCoder/.kubecoder/project.yaml`)
and not held against the phase.

No Blockers and no Majors. Three Minor findings follow, all tagged advisory: they are true, cheap
to know about, and none of them harms the product on merge.

---

## Findings

### 1 — The published image serves nginx's stock welcome page at `/` and `/index.html`

**Severity: Minor · Impact: advisory · Confidence: high (demonstrated by build probe)**

`Dockerfile:8` copies the store into the base image's existing document root:

```
COPY dist/ /usr/share/nginx/html/
```

`nginx:alpine` already ships two files there. Probed by building `FROM nginx:alpine` with
`RUN ls -la /usr/share/nginx/html/` through the same kaniko builder CI uses:

```
-rw-r--r--    1 root     root           497 Jul 15 16:53 50x.html
-rw-r--r--    1 root     root           896 Jul 15 16:53 index.html
PROBE_INDEX_HTML_PRESENT
```

`COPY` merges rather than replaces, so both survive into `registry:5000/charts-home`, and
`nginx/default.conf:17-19` (`location / { try_files $uri =404; }`) serves any file that exists —
`GET /index.html` returns the nginx welcome page with 200, and `GET /` resolves through the
directory to that same `index.html` rather than to a 404.

**Failure this produces.** The plan's P3 section states the interface as *"`/` is a 404 — there is
no `index.html` — so any probe must target `/index.yaml`"* (`plan.md:314`, as written before this
review). That is false for the image P2 ships. Concretely: `curl -sf https://charts.home/` returns
200 for an image whose `dist/` contains nothing but the base layer's leftovers — the root of the
chart repository answers healthy while resolving no charts, which is the exact failure mode
`Dockerfile:15`'s `test -f …/index.yaml` guard exists to prevent one layer down. Anything that later
takes `/` as a liveness signal (a probe, an operator smoke check, a monitor) reads green off a page
that has nothing to do with this repository.

No product consequence today: P3 follows `charts/tfmirror`, which declares no probes, and Helm only
ever fetches `/index.yaml` and the tarball URLs the index names. I have corrected the P3 interface
sentence in `plan.md` to record the verified behaviour so the next phase is not written against a
wrong premise.

---

### 2 — The gate passes an already-published version whose tarball has been silently rewritten

**Severity: Minor · Impact: advisory · Confidence: high (demonstrated)**

`tests/publish.sh:33-56` proves `dist/` *matches* the sources. It does not prove that a tarball
already in `dist/` is never rewritten — and `tools/package-chart.sh:18-20` unconditionally repacks
every chart at its current version into `dist/`, overwriting in place.

**Failing sequence, run against this commit:**

```
$ printf '\n# review probe\n' >> charts/homelab-shared/values.yaml
$ cexec iac tools/package-chart.sh
Successfully packaged chart and saved it to: /work/Charts/dist/homelab-shared-0.1.0.tgz
$ cexec iac tests/publish.sh
dist/ matches the chart sources; the index is absolute and additive      # EXIT=0
$ git status --porcelain
 M charts/homelab-shared/values.yaml
 M dist/homelab-shared-0.1.0.tgz
```

Version `0.1.0` now has different bytes and a different `digest:` in the index, under the same
version number. That is the mirror image of the property the script's own header claims to defend
(`tests/publish.sh:5-8`: *"A published version is immutable"*), and it is the path of least
resistance: the assertion the developer trips is finding 2's sibling — *"dist/… is stale … bump the
version in Chart.yaml and run tools/package-chart.sh"* — and running only the second half of that
sentence produces a green gate. A consumer pinned to `0.1.0` (D17's whole premise,
`decisions.md:117-129`) then resolves different content than it did yesterday, and a `Chart.lock`
recording the old digest fails to verify.

Two things keep this advisory rather than Major: the rewrite shows up as ` M dist/…tgz` in the
commit — a human-legible signal in review — and it requires a deliberate wrong move rather than an
ordinary one. Worth knowing that nothing mechanical stops it, and that CI never runs this gate
either (`Jenkinsfile` has no test stage, matching `/work/DockerImages/Jenkinsfile`), so a direct
push to `main` publishes whatever `dist/` holds.

---

### 3 — `tools/package-chart.sh` is never executed by anything

**Severity: Minor · Impact: advisory · Confidence: high**

`tools/build-index.sh:22` takes the store directory as an optional argument specifically so the gate
runs the real script (`tests/publish.sh:60`, `:74`, `:82`, and `.kubecoder/project.yaml`'s `build:`
verb) rather than a copy — a deliberate and good choice, recorded in the done-record.
`tools/package-chart.sh` gets the opposite treatment: `tests/publish.sh:44` and `:71-80` call
`helm package … --destination` directly, re-implementing what the script does, and no verb in
`.kubecoder/project.yaml` invokes it. It is the one new executable in this diff with zero coverage.

**Failure this produces.** Drift between the packaging the gate simulates and the packaging a
publish actually performs goes unnoticed. Sketch: give `package-chart.sh` a `--destination
"$ROOT/dist/$name"` (per-chart subdirectory), or a `--version` derived from something, or a
`--dependency-update`; `tests/publish.sh` keeps repacking flat with plain `helm package` and stays
green while every real publish now writes somewhere `helm repo index` and the `Dockerfile` do not
read the same way. The blast radius is small today because the script is five lines and its failures
are loud to the human running it — hence advisory — but the asymmetry with `build-index.sh` looks
unintended rather than chosen.

---

## Checked and clean

- **Tag scheme (V08).** `Jenkinsfile:36-40` passes `[…:${currentBuild.number}, …:latest]`;
  `resolveTrackingTag` (`helmCharts.groovy:144-165`) accepts `latest`/`<digits>` and returns
  `latest` as the tracking tag, so `resolve-helm-args`' digest pin at deploy time keeps working
  (`/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:118-135`).
- **`--merge` avoided (grounding).** `tools/build-index.sh:25` re-indexes the whole directory, the
  one `helm repo index` shape whose semantics do not move between `alpine/helm:3.9.1` (CI) and the
  sidecar's 4.2.3 (gate). The store being the checkout is what makes the first build a non-case.
- **Index correctness.** Regenerated during review: absolute `https://charts.home/…` URL, `type:
  library`, per-tarball digest — so a republished index is byte-stable for unchanged versions.
- **`.dockerignore` / `.gitignore`.** Context reduced to `dist/` + `nginx/`; `/.publish-gate.*`
  gitignored and dockerignored, `/dist/index.yaml` gitignored so a stale committed index is
  impossible. `git status` is clean after a `kc project build` and after both mutation probes.
- **Pipeline shape.** `library`/`podTemplate`/`node(POD_LABEL)`/`git branch: 'main'`/`container('kaniko')`
  matches `/work/DockerImages/Jenkinsfile` line for line in kind; `disableConcurrentBuilds()` +
  `githubPush()` matches `/work/HelmCharts/Jenkinsfile:27-30`. The unconditional
  `cicd.helmDeploy()` (DockerImages guards it on `built`) is correct here — every Charts push
  changes the image, so there is no no-op case to guard.
- **Done-record.** Records what the operator must create at `IaC/Charts`, the SCM/branch/credentials
  /script path, and the run-once requirement for `properties()` to take effect — the one thing this
  phase genuinely could not prove itself.
- **Comment density.** Header comments carry rationale (why POSIX `sh`, why no `--merge`, why
  cexec-free, why `no-cache` on the index only) rather than restating the code, and nothing narrates
  change history. Correct for this repo.
