# Consult 3 — completion judgment

**Outcome: `complete`.** No outstanding work clears the blocking bar. Three findings carded; no
phases appended; no edits made (there was no mechanical residue to fix).

## Every criterion, and the work that implements it

| AC | Implementing work | How I checked |
|----|-------------------|---------------|
| V01 | `charts/homelab-shared/templates/{_helpers.tpl,_tf-presync-hook.tpl}` | read both |
| V02 | `tests/consumer/` takes the library as one `dependencies:` entry; `tests/render-consumer.sh` renders and asserts all nine surfaces, and proves the `homelab-shared.*` prefix is real by requiring an unprefixed include to fail | read the fixture and the gate |
| V03 | `homelab-shared.tf-presync-hook` | compared field for field against `design.md:331-357` — `generateName`, `namespace: argocd-hooks`, PreSync, `BeforeHookCreation`, `backoffLimit: 0`, `activeDeadlineSeconds: 1800`, `serviceAccountName: tf-presync`, `restartPolicy: Never`, `envFrom` → `argocd-hook-credentials`, and `hook.repo`/`revision`/`stage` `required`-guarded |
| V04 | — | HelmCharts `git diff --stat` against the base is seven **added** files; `charts/shared/` untouched |
| V05, V06 | `tools/package-chart.sh` → `dist/`, `tools/build-index.sh --url https://charts.home`, `Dockerfile` (`COPY dist/` + `test -f …/index.yaml && nginx -t`), `nginx/default.conf` (root, `=404`, `no-cache` on the index), `Jenkinsfile` | read all five |
| V07 | `tests/publish.sh`'s additivity block, run as the real sequence | read; the gate is green in the sweep |
| V08 | `Jenkinsfile` destinations `:${currentBuild.number}` + `:latest` | checked against `helmCharts.kaniko2` — `dockerfile`/`context` default to `Dockerfile`/`.`, so omitting them is correct, and `resolveTrackingTag` accepts `latest`/`<digits>` |
| V09, V10 | `configs/prd/charts/{_shared/infrastructure.tf,prd/values.yaml}` | modelled on `tfmirror` field for field |
| V12, V13 | `charts/charts/templates/charts-service.yaml` annotations + `serverName: charts.home, charts` | matches `tfmirror-service.yaml` exactly |
| V15 | `charts/charts/Chart.yaml` carries no `dependencies:` | read |
| V16 | `charts/homelab-shared/values.yaml` → `hook.imageTag: "1"`, quoted; the gate asserts both the default reaching a consumer and an app override | read |
| V17 | `.kubecoder/project.yaml`, `jenkins: IaC/Charts` | green in the r2 sweep |
| V19 | `charts/charts/templates/_helpers.tpl` | `git ls-files -s` → mode `120000` |
| V11, V14, live V12/V13, V18 | test phase and operator, by design | V18 holds now: HelmCharts `main` is ahead 1 and unpushed |

## Other things I verified

- **No mechanical residue.** `git diff --check` clean across both repos' slice diffs; all four
  scripts pass `bash -n`; `tools/build-index.sh` passes `dash -n` (its POSIX constraint). All four
  scripts are mode `100755` in git, so Jenkins' `sh 'tools/build-index.sh'` works from a fresh
  clone.
- **The test phase can prove V12/V14 honestly.** The `iac` sidecar carries `homelab-root.crt` in
  `/usr/local/share/ca-certificates/` and `https://ca.home/acme/acme/directory` verifies from
  there (HTTP 200). So `helm repo add https://charts.home` needs no
  `--insecure-skip-tls-verify` — if the test phase reaches for one, that is evidence of a real
  TLS failure, not of a missing trust root.
- **`pvginkel/Charts` exists on GitHub and is empty** — `git ls-remote origin` returns zero refs
  and exit 0, where a nonexistent repo gives `Repository not found`. The test phase's push
  therefore succeeds and creates `main`. This is also what makes carded finding 2 true.

## The one recorded exception, judged

P4's done-record admits that `refute 'TF-owned rbd branch emits no PV'` could not be confirmed to
bite: forcing the branch it guards makes `helm template` error at `rbd-pv`'s `.imageName` split
before any refute runs. That is a limit of the mutation, not a hole — the regression it defends
still fails the gate, as a red render rather than as that line, and its cephfs twin does bite. Not
a leftover.

## Findings, and why none of them blocks

1. **HelmCharts' base moved under the slice.** `origin/main` is now `e87150d` — two commits past
   the `62917d6` the run branched from, touching `charts/nginx/files/snippets/proxy.conf` and
   `scripts/setup-env.sh`. Local `main` reads `ahead 1, behind 2`. The operator's push (the
   slice's last keystroke) is rejected until `git pull --rebase`. No code work and no conflict:
   P3 only adds paths that did not exist. I ran `git fetch` to establish this, which updated the
   remote-tracking ref and nothing else.

2. **The first-keystroke ordering as recorded cannot be followed.** P2's done-record and the
   plan's ordering constraints say the `IaC/Charts` job must exist *and have run once* before the
   test phase pushes `Charts` — because `properties()` only registers `githubPush()` after a
   first build. But the GitHub repo is empty, so a *Pipeline script from SCM* build has no `main`
   to check out: it fails before any Groovy executes, and `properties()` still never registers.
   The order that works is: create the job → let the test phase push → **manually run
   `IaC/Charts` once** (that manual run is what produces the image V11 requires) → pushes
   auto-trigger from then on. Cost of not fixing it: a confused minute at the console and a test
   phase that reports the live criteria unverified until the operator triggers the build. No code
   changes, so it goes to a card and to this write-up rather than to a phase.

3. **`containerTemplates.helm` has no other user in the estate.** Nothing else under `/work` uses
   it; `KubeCoder` uses `containerTemplates.k8s` in the same idiom, which is what makes the shape
   credible. So the first `IaC/Charts` build exercises not just the Helm 3.9.1-vs-4.2.3 indexing
   gap P2 recorded, but the container template itself. Fallback if it misbehaves:
   `containerTemplates.modern_app_dev`, which carries Helm 4.
