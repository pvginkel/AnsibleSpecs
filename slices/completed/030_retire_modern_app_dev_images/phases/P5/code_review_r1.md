# P5 code review, round 1: ModernAppTemplate root v0.1.2

Range: `acfc588..0e6cde2` on `phase/030-P5` (ModernAppTemplate). Tag `v0.1.2` points at `0e6cde2`,
and both it and `main` are on origin.

**Readiness: ready to merge.** The phase meets its outcome. `root/template/Jenkinsfile.jinja`
now runs the validation Job in `registry:5000/kube-coder-modern-app-toolchain:node-24` (`:65`).
The lockfile lookup and `validationImage` are gone. Because nothing in the image creates `/work`,
the pod mounts an emptyDir there (`:60-62,70-72`). The suite runner's comment no longer claims a
pre-baked browser (`local.py.jinja:235-237`), and `docs/copier_approach.md:74` names the new
image. The changelog gets a Root v0.1.2 entry, and the lightweight tag follows the v0.1.1
convention. `git grep` finds no mention of either retired image outside the historical changelog
entries.

I checked what else the Job might have relied on that only modern-app-dev provided:
- `libmagic1t64` is present for EI's and IoTSupport's `python-magic`.
- Every package in the four apps' backend and root `poetry.lock` has a wheel usable on cp313, so
  the image needs no compiler (it has no `build-essential`).
- No app backend or frontend test calls `ffmpeg`, `psql` or `pg_dump`.
- `HOME=/home/ubuntu` is `ubuntu:ubuntu`, and `~/.cache/ms-playwright` can be created.
- No `PLAYWRIGHT_*` variable is set at runtime.

I also rendered the template with `use_s3` false and true, and the Job YAML parsed both times with
the volume, the mount and the new image; `s3storage` is present only when `use_s3` is true.

**Gate state:** `kc project test` ran no tests on `0e6cde2`: none of the three projects declares a
test verb (`.kubecoder/project.yaml`), so the branch's test state is unverified. The plan makes
P6's Jenkins build this release's proof. The targeted probes above and in F1 are the only runs
behind this review. The Chromium download from the Job pod and Node 24 are D1's premises and
belong to P6. I did not probe them.

## Findings

### F1: Minor · advisory · anchor: repro-trace (witnessed) · confidence: high

**The Job's extraction into the new `/work` emptyDir fails its `.` entry and exits 2 on every run.**

- The emptyDir mounted at `/work` (`root/template/Jenkinsfile.jinja:60-62,70-72`) is `root:root`
  with mode 0777. The Job runs as uid 1000 (`:67-69`). The context archive is created with
  `tar czf … .` (`:25`), so it carries a `./` entry.
- `tar xzf /work/staging/context.tar.gz -C /work` (`:80`) therefore cannot set the mode or mtime
  of `/work`.

I witnessed this on the actual image, in a throwaway pod in `development` (deleted afterwards)
with the Job's securityContext and the same emptyDir mount:

```
root:root 777 /work
tar: .: Cannot utime: Operation not permitted
tar: .: Cannot change mode to rwxr-xr-x: Operation not permitted
tar: Exiting with failure status due to previous errors
tar exit=2
```

The files are extracted, and the Job's script has no `set -e`, so `poetry install` and
`run-suite` still run. `exit-code` records `run-suite`'s status (`:83-84`), so the build result is
unaffected.

The consequence: every `validation.log` archived from v0.1.2 on carries a tar failure right after
"Code received, extracting...". On modern-app-dev, `/work` was owned by uid 1000
(`DockerImages/modern-app-dev/Dockerfile:138-139`) and the same step was silent. Someone
diagnosing a red validation build will meet a spurious failure line first.

The consequence is advisory: the output is misleading, and no build result changes.
