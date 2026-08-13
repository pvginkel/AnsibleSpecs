# PA — code review r1

`git diff a8506f53b57cb64c6b2b20c8507eecfe6851591e..HEAD` (c3a4d642b1f0), branch `phase/013-PA`.
One file, 29 insertions: `Jenkinsfile.iac-image`.

## Readiness

The gate itself is built the way the plan and the rulings demand, and the parts I expected to be
wrong are right: the input set is exactly what `support/iac-image/Dockerfile` reads (I re-derived
it — `pyproject.toml`/`poetry.lock` at `:11`, `homelab-root.crt` at `:72`, `smallstep.sources` at
`:85`, `terraform.rc` at `:121`, `known_hosts.d/homelab` at `:142`; every other `COPY` is
`--from=build` at `:25` or a pinned external image at `:129`, and there is no `.dockerignore` or
`copyArtifacts` to widen it), all five patterns full-match under `==~` with the directory prefix
carrying its `/.*` and the literal dots escaped, the gate watches `support/iac-image/.*` rather
than `support/.*` so PB's tree cannot trip it, `checkout scm` stays, the Dockerfile path, context
and both tags are byte-identical to the base, and no build parameter was added. The two comments
earn their place (a non-obvious library contract and a non-obvious ordering dependency), not
narration. What the phase did **not** stress is the other side of the signal this job produces:
`helmCharts.kaniko` stamps `version-poller` labels onto the image it pushes, and the fleet's
version-poller consumes them to drive the weekly patch rebuild by triggering this job with no
parameters and no SCM changeset. The new gate turns that rebuild into a permanent no-op — verified
against the live registry, not inferred. That is one Blocker; everything else is a Minor.

---

## Blocker 1 — the gate silently kills the version-poller's weekly rebuild of `registry:5000/iac`

**Impact: blocking. Confidence: high (live evidence, not inference).**

`Jenkinsfile.iac-image:16` builds through `helmCharts.kaniko(...)`, which in the shared library is
a thin delegate to `kaniko2` (`pvginkel/JenkinsPipelineUtils.git`, `vars/helmCharts.groovy:52-59`).
`kaniko2` stamps every image it pushes with the version-poller contract
(`vars/helmCharts.groovy:96-108`): `org.webathome.poller.rebuild-at` = now + 7 days,
`org.webathome.poller.tracking-tag`, `org.webathome.poller.pipeline` = `env.JOB_NAME`, and
`org.webathome.poller.params` **only if the caller passed `params`** — the positional `kaniko`
signature cannot.

Those labels are live on the image this job pushes. Read this pass off the registry
(`http://registry:5000/v2/iac/manifests/latest` → config blob
`sha256:bcd89087ef5ab…`, image created 2026-08-12T17:44:33Z):

```
org.webathome.poller.pipeline    = IaC/IaC Docker Image
org.webathome.poller.rebuild-at  = 2026-08-19T17:41:44Z
org.webathome.poller.tracking-tag = latest
(no org.webathome.poller.params)
```

The consumer is `pvginkel/DockerImages.git`, `version-poller/app/poller.py`. It walks
`registry.catalog()` — every repo in `registry:5000`, so `iac` is in scope, not just DockerImages'
own images (`poller.py:81-86`; the redesign doc calls driving off the registry rather than a
hand-maintained list the whole point, `docs/version-poller-redesign.md:40-48`). For `iac:latest`
the tag name equals the `tracking-tag` label, so it is the governing tag (`poller.py:129-130`);
when `now >= rebuild-at` it becomes due (`poller.py:157,177-178`) and the poller triggers
`labels[PIPELINE]` — `IaC/IaC Docker Image` — with `{}` params, since the `params` label is absent
(`poller.py:185-202`, `:89-103`; the label table spells out "Absent ⇒ trigger with no parameters",
`docs/version-poller-redesign.md:114`).

**Failing input, dated.** On 2026-08-19 the poller triggers `IaC/IaC Docker Image` via the REST
build endpoint with no parameters. That build's `currentBuild.changeSets` is empty — nothing was
pushed that Jenkins has not already changelogged into an earlier build, and the trigger carries no
commits of its own. `utils.hasChanges` is `currentBuild.changeSets.any { … }`
(`vars/utils.groovy:33-41`), so all five calls in `imageInputChanged()`
(`Jenkinsfile.iac-image:34-42`) return false on an empty list. The stage marks itself skipped
(`Jenkinsfile.iac-image:22`), kaniko never runs, no tag is pushed — and therefore **no fresh
`rebuild-at` is stamped**. The consequences chain:

1. `rebuild-at` on `iac:latest` stays `2026-08-19T17:41:44Z`. The poller's `TriggerState` records
   the value it fired on and suppresses a re-fire while it is unchanged (`poller.py:165-176`), so
   the retry does not happen next cycle.
2. Once `now - rebuild_at > STALE_GRACE` (2× the 7-day interval, so ~2026-09-02) the poller stops
   triggering altogether and logs `iac:latest rebuild-at stale by … — likely orphaned/renamed/dead
   job` on every poll (`poller.py:158-164`). The image is permanently misreported as an orphan, and
   the fleet's own orphan-detection channel is poisoned with a false positive.
3. The `iac` image then never rebuilds again except on an image-input push. Everything this
   Dockerfile deliberately floats stops being patched: `FROM ubuntu:questing` (`:1,:23`), the
   unpinned `apt-get install … kubectl step-cli terraform` (`:109-113`), `curl … get-helm-4 | bash`
   (`:98`), and the uv installer (`:64`). The timer is the *only* mechanism that refreshes those —
   `docs/version-poller-redesign.md:50-61` is explicit that a periodic rebuild is what closes the
   OS/system-layer CVE surface, and `:40-44` calls an image the poller cannot reach "a security
   problem, not a tidiness one".

Before this change the push flood masked it: every Ansible push rebuilt the image and pushed
`rebuild-at` a week out, so the timer never came due. Removing the flood is exactly what exposes
the missing path.

The sibling this phase copied has the path. `DockerImages/Jenkinsfile:46` gates on
`utils.hasChanges("${img}/.*") || (img in force)`, where `force` comes from `params.image`
(`:33-40`) — and `:103` stamps `params: [image: image]` precisely so the poller can replay it. That
`||` half is not an operator convenience; it is what keeps a changeset gate compatible with a
parameter-less, changeset-less rebuild trigger. PA took the changeset half of the pattern and left
the bypass behind, while continuing to stamp the labels that promise the bypass exists.

Note for whoever resolves this: the "gate only, no escape hatch" ruling (`plan.md:33-40`) weighed a
`FORCE` parameter as an operator convenience and accepted a hole scoped to *"a build that fails on
an image-input push is not retried by the next unrelated push"*. Neither the ruling nor PA's
section mentions the poller, and the poller cannot do what the ruling offers instead ("replay the
job from a commit that touched an input"). This is a fact the ruling did not have, not a ruling
being overridden.

---

## Minor 1 — `Jenkinsfile.iac-image` is not an input to its own gate

**Impact: advisory. Confidence: high.**

The five patterns at `Jenkinsfile.iac-image:34-42` do not match `Jenkinsfile.iac-image`, yet the
file holds three things that decide what gets built and pushed: the Dockerfile path, the build
context, and both destination tags (`:16-19`). A push that changes only this file — this very
commit is one — runs a build that skips the stage, so a change to the build recipe is never
exercised until some unrelated input happens to change. The operator's recovery ("push a trivial
change to `support/iac-image/`", `plan.md:36`) works, but nothing in the build output says the
recipe change went unbuilt; the stage just reads *skipped for conditional* the same way an
unrelated push does. HelmCharts' `changed()` has the same shape, so this is consistent with the
precedent rather than a deviation from it — recording it as advisory, not as something to resolve.

---

## Checked and clean

- **Input set completeness.** Re-derived from `support/iac-image/Dockerfile` independently of the
  plan's list; it matches, and `support/iac-image/` holds exactly the three files the Dockerfile
  reads. No `.dockerignore` at the repo root, so the `.` context adds nothing the `COPY`s don't.
- **Full-match correctness.** `'pyproject\\.toml'` in a Groovy single-quoted string is the regex
  `pyproject\.toml`, which full-matches only the root file — the repo has no second
  `pyproject.toml`/`poetry.lock` to be wrongly caught or missed (`find` over the tree returns one
  of each). `support/iac-image/.*` matches nested paths too, since `.` spans `/` in Java regex.
- **PB non-interference.** `support/iac-image/.*` cannot match `support/iac-agent/…`.
- **No escape hatch** (V05): no `properties([parameters(...)])`, no `params.` reference.
- **Method placement / CPS.** `def imageInputChanged()` after the `podTemplate` block, calling the
  `utils` library global from a script-class method, is the HelmCharts `changed(entry)` shape
  verbatim and resolves through the script binding as it does there.
- **Comments.** Both additions carry non-obvious contracts (`checkout scm` → `changeSets`; `==~`
  full-match semantics). Neither narrates change history nor restates the code.
