# Close-out — slice 011 kubecoder_ci_version_pins

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — DockerImages/registry-cleanup: the per-prefix cap has already deleted the dev-511 build that KubeCoderDeploy's committed pins name · major

All seven `Build-Main` images in `KubeCoderDeploy/chart/values.yaml` pin `dev-511`. The registry
no longer holds that tag for any of them: the `dev` family runs `dev-428, dev-441, dev-443,
dev-457, dev-470, dev-479, dev-482, dev-495, dev-509` then jumps to `dev-514 … dev-523`. The nine
survivors below 514 share digests with `prd-26 … prd-36` and are held by the shared-digest guard;
`dev-511` was not promoted, so the newest-10 per-prefix cap evicted it while KubeCoderDeploy's
chart referenced it in git.

`plan.md`'s G11 frames this exposure as prd-only, un-promoted and TTL-based. The realised case is
a *dev* pin, deleted by the *cap*, with a git reference standing. Under D47 the dev stage's
deployed reference becomes exactly such a pin, and the protection D47 designs — `prd-<n>` created
at promotion, sharing a digest with `prd-latest` — covers prd only.

Two adjacent observations from the same registry read, recorded for whoever picks this up:

- Six of the seven images already carry a bare-numbered family, `175`/`176`-`185`, from a
  pre-`dev-` scheme; `kubecoder-vsix` and `kubecoder-claude-shim` carry none. D47's bare `<n>`
  family is therefore not empty for most of the set, and its cap is already full at 10.
- `prd-26 … prd-36` are the promote job's own build numbers, not image build numbers — the
  mismatch S1 records, confirmed live.

**Consequence:** A git-committed deployment reference is not in registry-cleanup's protection set, so once Argo deploys KubeCoder from a stage file the pinned tag can be deleted under the cap while git still names it — the Application then fails to pull. It has already happened to the pins in the repo today.

**Provenance:** witnessed — plan-reviewer, plan review r1; http://registry:5000/v2/kubecoder-*/tags/list queried 2026-09-20, KubeCoderDeploy/chart/values.yaml:11-18,668,671, DockerImages/registry-cleanup/app/main.py:285-299
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — Deploy-PRD numbers its prd-<n> tags with the promote job's build number; D47 numbers them with the image build's · minor

`Jenkinsfile.deploy-prd:33-38` retags `dev-${sourceDevBuild}` to `prd-${currentBuild.number}` — the promote job's own build number, in a numbering space unrelated to Build-Main's. D47 pre-writes `prd-<n>` into the prd stage values file at build time, where `<n>` is the image build's number, and has the promote job create exactly that tag. Slice 012's replacement therefore changes numbering space, not just mechanism, and the `prd-*` tags already in the registry belong to the old space. This slice writes `prd-511` into the prd stage file as its first forward reference.

**Consequence:** If slice 012's promote job keeps the old numbering, it creates a tag nothing references while the stage file's prd-<n> stays unpullable — and the sync fails on an image that does not exist, which is exactly the loud-and-local failure D47 designed for, landing for the wrong reason.

**Provenance:** read — plan-writer, plan pass r1; /work/KubeCoder/Jenkinsfile.deploy-prd:33-38, argo-cd/decisions.md:493-498
**Disposition:**

### S2 — The pins this slice writes are forward references: slice 012 must build before it points Argo at KubeCoderDeploy · minor

P1 leaves `config/dev/values.yaml` naming build 511's bare tag and `config/prd/values.yaml` naming `prd-511`; the registry holds `dev-511` and neither of the two. Nothing creates them until a Build-Main run under the new scheme (slice 012, Ruling 1). Nothing consumes the repo today (G7), so the gap is inert — but it is an ordering constraint on the cutover, not a defect to fix here.

**Consequence:** A dev Application created before the first cutover build syncs to an image tag that does not exist and fails to pull; sequencing the build ahead of the Application avoids it entirely.

**Provenance:** read — plan-writer, plan pass r1; KubeCoderDeploy/chart/values.yaml:11-18,668,671, plan.md G7 and Ruling 1
**Disposition:**

### S3 — HelmCharts: the gitToken PAT rides the helm command line for all 45 releases, and only version-poller consumes it · minor

`argo-cd/design.md` records it, and slice 011's `slice.md` carried it into planning "so it isn't
lost", asking the planner to decide deliberately because `version-poller` is one of requirement
3's tag-prefix readers:

> **`gitToken` travels as a helm CLI argument for all 45 releases**; only `version-poller`
> consumes it. It must become an ESO leaf when version-poller migrates — Argo has no such
> argument to inject — and a PAT on a command line lands in process tables and echoed commands
> regardless.

**The decision (Ruling 7, operator, 2026-09-20): out of scope for slice 011.** `design.md`
assigns the fix to the version-poller migration, and nothing in slice 011 touches the helm
invocation that carries the argument — the slice moves image tags between values files in
KubeCoderDeploy and adds a library method. Recorded here so the item survives the slice rather
than closing with it.

**Consequence:** A GitHub PAT is visible in process tables and echoed commands on every one of 45 release deploys, to serve the one release that needs it; nothing changes until version-poller migrates and the token becomes an ESO leaf.

**Provenance:** read, plan-writer r2 (review fix pass) — Ruling 7 in plan.md; carried in slice.md's source material from argo-cd/design.md
**Disposition:**
