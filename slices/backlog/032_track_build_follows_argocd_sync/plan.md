# Slice 032 — track_build.py follows a green build into its Argo CD sync

## Requirements / rulings

- R1. **Follow a green build into the Argo CD deploy it triggers.** Card: "track_build.py
  (kube-coder-dev-local-home) gains an option to wait until the deploy the green build triggers
  has rolled". Operator (2026-09-27): generic for every Argo-deployed repo, not KubeCoder-only.
- R2. **On by default.** Asked "should it be opt-in (a flag) or the default?", operator: "By
  default."
- R3. **Git questions only from the environment's own clone.** Operator: "I would suggest it only
  attempts to find the information in Git if the deploy repo is in the current environment. It
  should be. If it's not, it should stop with a message stating that the repo isn't there, and it
  should be added. So look in /work for matching environments, and bail if it's not there."
- R4. **prd promotions too.** Asked whether the slice also covers Promote-PRD's fast-forward of
  `prd` (which prints no pin line today), operator: "Sure, add this."
- R5. **Say so when a pipeline gives the script nothing to follow.** Operator: "The script should
  remark if the line isn't there, so the agent understands that it may have to make a fix to a
  pipeline to get the script to track the Argo CD deployment."
- R6. **Default `--appear-timeout` of 5 minutes.** Card: "raise track_build.py's default
  `--appear-timeout` from 30 s to 5 minutes"; operator (2026-09-25): "yes, bump the timeout to 5
  minutes."
- Ruling (2026-09-27, refinement D1): the slice does **not** pre-add deploy-repo clones to the
  environments that lack them. When the deploy repo's clone is missing from `/work`, the script
  stops with a distinct exit status (the build was green, the deploy is untracked), names the
  missing deploy repo, gives the exact `git clone` line to run now, and says to declare the repo
  in the environment's `.kubecoder/config.yaml` for next time. Operator: "D1: Correct."

#### Settled by the planning session (operator saw these in refinement.md and did not object)

- **Argo CD state is read from the Kubernetes API directly**, over HTTPS with the bearer token
  and CA in `~/.kube/config` (context `prd`, read-only), not by shelling out to kubectl.
  Grounds: `~/.kube/config` is a KubeCoder kubeconfig entry with no grant, so it reaches every
  environment (KubeCoder `manual/docs/reference/config-yaml.md` "The kubeconfig grants";
  KubeCoderDeploy `chart/values.yaml` `kubeconfigs:`). kubectl is on no dev container's PATH;
  it lives only in the `iac` sidecar, which the ElectronicsInventory, FieldnotesApp, IoTSupport,
  ZigbeeControl, Architecture and ModernAppTemplate environments do not declare. The kubeconfig
  shape is plain: `clusters[].cluster.{server,certificate-authority-data}`,
  `users[].user.token`, `contexts[]`, `current-context: prd`. PyYAML 6.0.2 is importable from
  the dev image's system `/usr/bin/python3` (`/usr/lib/python3/dist-packages`). The Argo CD HTTP API
  (`https://argocd.home/api/v1/applications`) answers 401 without an OIDC session, so it is no
  substitute. Verified RBAC with the default kubeconfig: `get`/`list`
  `applications.argoproj.io -n argocd-prd` yes, `patch` no; `get`/`list` `jobs`, `pods`, `get
  pods/log` in `argocd-hooks` yes.
- **Ansible's copy is removed.** `tools/ai_workflow/track_build.py` and
  `tools/ai_workflow/test_track_build.py` in Ansible are deleted; DockerImages
  `kube-coder-dev-local-home/` (the image copies `track_build.py` to `~/.local/bin`, on PATH) is
  the only source. The two scripts are byte-identical today (478 lines, stdlib-only); the tests
  differ only in the import path. Nothing in Ansible invokes its copy (all callers — KubeCoder
  agents/skills/docs — use PATH). Ansible `docs/live-infra-access.md` paragraph "**`tools/ai_workflow/track_build.py` looks dead and is not.**"
  and `docs/design-philosophy.md`'s mention of `tools/ai_workflow/test_track_build.py` are
  rewritten to point at DockerImages. The DockerImages suite (`kube-coder-dev-local-home/tests/`,
  `pytest.ini`) is wired into DockerImages' `.kubecoder/project.yaml` test entry point — today
  it declares only `backup-server` and `architecture` ("The other in-repo suites are not
  declared yet"), so no gate runs the tracker's tests.
- **KubeCoder's docs**: `/work/KubeCoder/docs/operations/deploy-operations.md` section "A green
  build is not a rolled dev" (≈line 92), which has agents confirm the roll by hand, is updated to
  say the tracker now waits for the roll (and what its stop exits mean). Path 1 there (≈line 84)
  cites `track_build.py … --hash`.
- **prd promotions**: KubeCoderDeploy `Jenkinsfile.promote` is the only promote pipeline under
  `/work`. It fast-forwards with `git push origin '${sha}:refs/heads/prd'` and echoes only
  `Promoting ${sha} to prd as ${release}…` or `prd is already at ${sha}, and no release tag
  records it: recording it as ${release}`. It gains one handoff line in the pin-line shape
  naming the repo, the commit and the `prd` branch, which the tracker parses. No shared-library
  change.
- **The pin handoff today** (JenkinsPipelineUtils `vars/cicd.groovy`, `writeVersionPins`):
  `echo "${repo} ${sha} pins ${changed.join(', ')}."` after `git push --quiet origin HEAD:main`,
  or `echo "${repo} already carries these pins: nothing committed, nothing pushed."`. It always
  writes branch `main`; `repo` is `owner/Name` (e.g. `pvginkel/KubeCoderDeploy`); the files are
  deploy-repo paths such as `config/dev/values.yaml`, `config/prd/values.yaml`. Callers: the
  Jenkinsfiles of KubeCoder, IoTSupport, DockerImages, FieldnotesApp, ElectronicsInventory,
  DHCPApp, Architecture, Charts, ZigbeeControl, and ModernAppTemplate's `Jenkinsfile.jinja`. The
  pin line is printed by the build `track_build.py` already tracks (e.g. KubeCoder/Build-Main),
  so the script reads it from that build's console.
- **"Already carries these pins"** → nothing new was committed; the tracker follows the deploy
  branch's current head instead.
- **No pin line** (a repo that doesn't deploy, or a pipeline lacking the line) → R5's remark,
  and the script exits with the build's own result, not a failure.
- **Matching** Applications: `repoURL` (always `https://github.com/pvginkel/<X>Deploy.git`,
  mapping to `/work/<X>Deploy`) and `targetRevision` equal to the pushed branch, and a helm
  `valueFiles` entry naming a pinned file — so a dev-only change does not wait on a prd app
  tracking the same branch. Upstream-chart apps have `spec.sources[]` (8 are 3-source: chart +
  `ref: values` + companion `chart/`, argo-cd D18/D56) with per-source `status.sync.revisions[]`.
- **Done** = the app's sync revision is the pin commit or a descendant (`git merge-base
  --is-ancestor` in the `/work` clone, after a fetch), `status.operationState.phase` terminal,
  `health.status` not `Progressing`.
- **Stop rather than hang**: a deadline on Argo seeing the commit (push-only sync; argo-cd D6 "a
  dropped webhook is stale-but-green, not delayed"); a `SyncError` condition; an app with no
  `syncPolicy.automated` (argo-cd D63; today only the `argocd-prd` Application). On a failed or
  unhealthy roll, save the operation message, conditions, failed or Degraded resources and the
  `tf-presync-<app>-<stage>` hook Job's log (argo-cd D30) in `--log-dir`, beside the failing
  builds' console logs.
- **Rollout**: the image ships as `:latest` (no `deploy-pins.json`), so the updated script
  reaches each environment at its next restart; no deploy step. Live verification runs the
  script from the DockerImages checkout.

#### Premise corrections

- slice.md's matching sketch assumed dev and prd apps share a branch and differ by
  `valueFiles`. True for `keycloak-dev`/`keycloak-prd` (both `main`, `config/dev` vs
  `config/prd`); false for KubeCoder: `kubecoder-prd` tracks branch `prd`, `kubecoder-dev` tracks
  `main`. KubeCoder/Build-Main pins both `config/dev/values.yaml` and `config/prd/values.yaml` on
  `main`, so matching by repo + branch + valueFiles correctly waits on `kubecoder-dev` only; prd
  rolls at promotion (R4). No change to the design, only to the tests' fixtures.

## Task shape

cross-cutting — slice.md puts the change in four repos (the tracker in DockerImages
`kube-coder-dev-local-home/`, its copy in Ansible, R4's promote pipeline in KubeCoderDeploy, the
roll-by-hand guidance in KubeCoder's docs) and sets a handoff-line contract between Jenkins
pipelines and the tracker for every Argo-deployed repo (R1).

## Ordering constraints

- The promote pipeline's handoff line format and the tracker's parser must agree; land the
  pipeline line no later than the tracker phase that parses it.

### P1 — Promote-PRD hands the tracker the commit prd now names

Target: ../KubeCoderDeploy

Every green `Jenkinsfile.promote` run prints one handoff line naming the deploy repo
(`pvginkel/KubeCoderDeploy`), the full commit `prd` now names, and the branch `prd`. The line
takes the pin line's shape (`<owner/repo> <sha> …`, JenkinsPipelineUtils `vars/cicd.groovy:133`),
so one parser reads both, and cannot be mistaken for the pin line's `pins` form or for the job's
existing echoes (`Jenkinsfile.promote:98`, `:100`).

It prints once `prd` names the commit. That covers both the fast-forward (`:129`) and the
record-only re-run (`:97-98`), where `prd` already names the commit and nothing is pushed. A green
promotion must never look like a pipeline that lacks the line (R5). No shared-library change. P4
parses this line: put its exact form in the done-record.

### P2 — Ansible drops its copy of the tracker

Target: root

`tools/ai_workflow/` (`track_build.py`, `test_track_build.py`, and nothing else) goes, leaving
DockerImages `kube-coder-dev-local-home/` as the tracker's only source. The two places in this repo
that describe the copy are rewritten to point at DockerImages, per the ruling:
`docs/live-infra-access.md:57-59` ("looks dead and is not") and the sentence at
`docs/design-philosophy.md:62-63`. No coverage is lost. DockerImages' `tests/test_track_build.py`
carries every case of the deleted test; the two files differ only in the import path and the
"Run:" line (verified by diff).

### P3 — DockerImages gates the tracker's suite; `--appear-timeout` defaults to 5 minutes

Target: ../DockerImages
Creates: kube-coder-dev-local-home

DockerImages' `kc project test` runs the `kube-coder-dev-local-home/` suite (`pytest.ini`,
`tests/`) as its own component, named after the directory so that later phases can target it.
Today `.kubecoder/project.yaml` declares only `backup-server` and `architecture` and says "The
other in-repo suites are not declared yet" (`:20-22`), so no gate runs the tracker's tests. The
suite must run where kc runs it. Neither the dev container's `python3` nor the `iac` sidecar's has
pytest; both have PyYAML 6.0.2, and `iac` has `uv`/`uvx`.

R6: the `--appear-timeout` default becomes 5 minutes (`track_build.py:366-371`, now `30.0`), and
the help text agrees.

### P4 — The tracker follows a green build's handoff into its Argo CD sync

Target: kube-coder-dev-local-home

R1–R5. By default, once the tracked builds finish green, the tracker reads the handoff lines from
their consoles. It then waits until every Argo CD Application that a handoff touches has rolled
the handed-off commit, and it reports each app in the summary beside the builds. It returns only
when the commit is live. The requirements/rulings above settle the design: API access, matching,
done, stop, the missing-clone exit and the no-line remark. The constraints below are what the
executor would otherwise have to rediscover:

- **Handoff lines.** There are three kinds:
  - The pin line (`cicd.groovy:133`), whose branch is always `main` (`:79`, `:127`).
  - `<owner/repo> already carries these pins: …` (`:114`), which names no commit: follow `main`'s
    current head, read from the clone.
  - P1's promote line (branch `prd`).

  A single build can print several: DockerImages' build pins every deploy repo its images feed
  (`DockerImages/Jenkinsfile:171-186`).

  In the console, the pin line's owner always reads `****`, because Jenkins masks the GitHub
  credential's username inside `writeVersionPins`' credentials block. Seen in
  KubeCoder/Build-Main #551, ElectronicsInventory/ElectronicsInventory #255, IoTSupport/IoTSupport
  #145 and ZigbeeControl/ZigbeeControl #60 (`****/KubeCoderDeploy 46e0aa8… pins
  config/dev/values.yaml, config/prd/values.yaml.`). So the repo name is all the console reliably
  carries. The `git commit -m 'ci: image pins from …'` trace line just above it is not a handoff.
- **The environment's clone answers every git question** (R3, ruling D1). It is `/work/<Name>` for
  `<owner>/<Name>`, fetched before it answers. The tracker checks for missing clones before it
  waits on anything.
- **Runtime.** The script runs under the dev container's system `python3`. Nothing beyond the
  stdlib and PyYAML may be assumed. Every Application lives in `argocd-prd` on the `prd` context:
  50 today. The dev cluster serves no `applications` resource.
- **Matching.** An app's `valueFiles` name a pinned repo-root path in one of two ways:
  - relative to the source's `path: chart` (`../config/prd/values.yaml`);
  - through a `ref: values` source (`$values/config/prd/values.yaml`, on the 8 three-source
    upstream-chart apps).

  A handoff that names no files (promote, already-carries) matches every app on that repo and
  branch.
- **"Done" is what Argo reports live, not what it last compared.** Checks on 2026-09-27 showed
  why:
  - `argocd-prd` reads `status.sync.revision` 83b6cf8, OutOfSync, while its last operation
    deployed 307d94f. The compared revision moves before any sync.
  - A commit that renders no change leaves the app Synced at the new revision with no new
    operation: `grafana-prd` is Synced at fed8ed0 while its last operation synced 3bd4dc9. So
    waiting for a fresh operation would hang.

  On a multi-source app, the revisions that count are those of the deploy-repo sources
  (`status.sync.revisions[]`).
- **Stops.** Besides the stops the rulings name, a handoff that no Application matches is reported,
  not waited on. Every stop says what happened and what the agent can do about it. The docstring's
  exit-status list covers every new outcome next to 0/1/3.
- **Tests.** The fixtures take real Application shapes: single-source and three-source; KubeCoder,
  whose dev and prd apps track different branches (`main`, `prd`); and keycloak, whose dev and prd
  apps share `main` and differ by values file.

### P5 — A failed roll leaves its diagnosis on disk

Target: kube-coder-dev-local-home

This covers a followed app whose sync fails, which ends unhealthy, or which stops on a `SyncError`.
The tracker writes that app's diagnosis into `--log-dir`, beside the failing builds' console logs,
and the summary names the file. The diagnosis holds:

- the operation message;
- the conditions;
- the resources the sync failed (`status.operationState.syncResult.resources[]`);
- the resources that are not healthy;
- the log of the app's PreSync hook Job, `tf-presync-<app name>` in `argocd-hooks` (argo-cd D30;
  live names such as `tf-presync-kubecoder-dev`).

Argo CD v3.5.1 keeps per-resource health out of the Application. All 50 apps carry
`status.resourceHealthSource: appTree`, and no `status.resources[]` entry has a `health` field.
The unhealthy resources therefore come from the live objects the Application lists. The default
kubeconfig can read those objects:

- in the app namespaces: `list pods`, `get deployments`/`statefulsets`, and `list events` are
  allowed, and `get secrets` is denied;
- in `argocd-hooks`: `list jobs` and `get pods/log` are allowed.

### P6 — KubeCoder's docs stop sending agents to confirm the roll by hand

Target: ../KubeCoder

Per the ruling, `docs/operations/deploy-operations.md` "A green build is not a rolled dev"
(`:92-99`) says that the tracker now waits for the roll, and what its stop exits mean, taken from
the P4 and P5 done-records. The agent instruction that sends workers to that hand check follows the
section: `.claude/skills/card-pass/SKILL.md:131-133` ("then the roll check in
`docs/operations/deploy-operations.md`").

## Not in scope

- Adding deploy-repo clones or the `iac` sidecar to other environments' `.kubecoder/config.yaml`
  (ruling D1).
- Changing `cicd.writeVersionPins`' pin line.
- Any write to Argo CD (the kubeconfig cannot `patch` Applications anyway).
- Other deploy flows' docs outside KubeCoder; only KubeCoder's roll-by-hand guidance is in the
  slice.
- The stale `Progressing` health on eight `argocd-prd` apps (close-out) — an Argo CD estate issue,
  not the tracker's.
