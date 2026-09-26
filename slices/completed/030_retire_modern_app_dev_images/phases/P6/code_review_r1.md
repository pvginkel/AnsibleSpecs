# P6 code review — round 1

ZigbeeControl `8043c1a..0a2c4a9` (`phase/030-P6`, also `origin/main`), one commit: "Update to root template v0.1.2".

**Readiness: ready to merge. No findings.** P6 had to take P5's root-template release through `copier update`, with no hand edits, and prove D1's two premises on a real Jenkins build. The diff does exactly that. It changes three files, and they carry exactly the hunks of ModernAppTemplate `v0.1.1..v0.1.2` under `root/template`: `_commit`, the validation stage's opening comment, the image line, the `work` emptyDir with its `/work` mount, and the suite runner's browser-install comment. I rendered `v0.1.2` fresh with the app's answers (`uvx copier copy` in the `modern-app` sidecar). The app's `tools/suite_runner/*` is byte-identical to that render. Its `Jenkinsfile` differs from the render only by the app-local "No data sidecars" comment, which was already there at `8043c1a`. So V13 holds for this app. `git grep` finds no `modern-app-dev`, `playwrightVersion`, `validationImage` or pre-baked-browser text left in the repo (V07, this app's share).

I checked the build proof against Jenkins directly:

- `ZigbeeControl/ZigbeeControl` #60 ran on `0a2c4a9`. Result `SUCCESS`, `exit=0, 50 passed`, `SUITE_RESULT` backend 13 and frontend 37. That matches #59 on `8043c1a`, whose console shows `Validation image: registry:5000/modern-app-dev-playwright:playwright-1.60.0`.
- **First D1 premise (the Job reaches the browser download host):** #60's `validation.log` lines 351–391 show the Job pod downloading Chrome for Testing 148.0.7778.96, FFmpeg and Chrome Headless Shell from `cdn.playwright.dev` into `/home/ubuntu/.cache/ms-playwright`.
- **Second D1 premise (the frontend builds and tests on Node 24):** `vite build` runs at line 286, and the Playwright suite passes 37 of 37 at line 2042.
- **The image's Node version:** the `modern-app` sidecar, built on the same toolchain image, reports `v24.21.0`.

The done-record's Record claims also check out:

- The B2 tar errors are at `validation.log` lines 3–5.
- The `Failed to get git commit` trace is in #59's log as well.
- The "OS is not officially supported … fallback build" lines appear in #59 as well, so the image switch did not introduce them.

The gate ran green (`kc project test`: backend pytest and frontend Playwright OK). The only change under the gate is a comment in `local.py`. The phase's behavioral proof is the Jenkins build, and I confirmed it above.

B2 (the tar extraction into the root-owned emptyDir exits 2 on every run) is visible in this app's build. It is already in the close-out as a bug against P5's template, so I do not report it again here.

## Findings

None.
