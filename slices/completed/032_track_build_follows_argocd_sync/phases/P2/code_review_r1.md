# P2 code review — round 1

Range `242be03..eac626e` (one commit) on `phase/032-P2`.

**Readiness.** P2 is ready to merge. `tools/ai_workflow/` is gone, and nothing in the repo refers to
it any more: `git grep` finds no `track_build` or `ai_workflow` outside the two rewritten doc
paragraphs, and no config (`.kubecoder`, lint configs, Jenkinsfiles, `pyproject.toml`) names
`tools/`. No coverage is lost (V12). The deleted `track_build.py` is byte-identical to DockerImages
`origin/main:kube-coder-dev-local-home/track_build.py`. The deleted test differs from
`kube-coder-dev-local-home/tests/test_track_build.py` only in the `Run:` docstring line (`:10`) and
the import path's `.parent` depth (`:19`), so every case has its successor. I checked both with
`diff`. The two paragraphs the plan names (`docs/live-infra-access.md:57-59`,
`docs/design-philosophy.md:62-63`) now point at DockerImages. The root gate is green (input). One
advisory prose inaccuracy follows. It does not block.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high — the new paragraph names the wrong image

`docs/live-infra-access.md:57-59` says the tracker "is built into the dev image from DockerImages
`kube-coder-dev-local-home/`, tests included". Two parts of that are wrong:

- **The image.** `kube-coder-dev-local-home/Dockerfile:17-24` builds its own `FROM scratch` image,
  the local-home image. The environment mounts it at `~/.local`: the Dockerfile's comment says "The
  image root is ~/.local", and KubeCoder `docs/platform/shared-home.md:81` describes the mount.
  The dev image is DockerImages `kube-coder-dev`, a separate image.
- **The tests.** The Dockerfile copies only `track_build.py` (`:24`). If "tests included" means the
  image ships the tests, it is wrong. If it only means the directory holds them, it is true.

The consequence is small. The paragraph names the right directory, so a reader who wants to change
the tracker still goes to the right place.
