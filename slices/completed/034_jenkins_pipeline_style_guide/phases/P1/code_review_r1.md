# Code review — slice 034, P1 (the §6a webhook test), round 1

Range: `983d076..1656c41` on `phase/034-P1` (AnsibleSpecs).

**Readiness: ready to merge, no findings.** The phase meets its outcome. report.md's Appendix A R1
now carries the §6a result and a step-by-step new-repo recipe that says who takes each step.
Review plan §6a is ticked. Close-out A1 (delete the repo) and P5 (the argocd runbook's token
sentence) are entered, and P8, P9 and Ordering steps 2–3 are edited to the recipe. The recipe is
one P5 can take over as it stands. AnsibleSpecs has no `.kubecoder/project.yaml`, so no gate
exists and the "unverified" gate state bears on nothing here. I checked the record's claims
against live state instead:

- **Throwaway repo.** `pvginkel/jenkins-trigger-test` is private. Its commits `b3c25d0`,
  `9004f50` (15:53:52), `d064fd7` (15:56:24) and `765d474` (15:58:21) match the timeline. It
  keeps one hook, 689753852: `web`, `push` only, `json`, secret set, URL
  `https://jenkins.webathome.org/github-webhook/`, created 15:58:03. Its deliveries are a ping at
  15:58:05 and the `765d474` push at 15:58:23, both 200. That fits "build #1 by push at 15:58:30"
  with no hand-started build.
- **Job and saved configs.** The job is gone (`/job/jenkins-trigger-test/api/json` → 404). Both
  configs are in `jenkins-config/xml-deleted/`. `jenkins-trigger-test.xml` holds one
  `GitHubPushTrigger`, and its `DeclarativeJobPropertyTrackerAction` lists that trigger. That
  bears out step 3 of the recipe, "the file's `triggers {}` owns the trigger".
- **Jenkinsfile and linter.** The throwaway Jenkinsfile on `main` is declarative, with
  `triggers { githubPush() }`, `skipDefaultCheckout()` and a `checkout scm` stage. Re-posted to
  `/pipeline-model-converter/validate`, it returns `Jenkinsfile successfully validated.` (V18).
- **Manage hooks.** The controller's `/manage/configure` shows `_.manageHooks` checked.
- **Existing hooks.** JenkinsPipelineUtils has the Jenkins hook, in the same shape.
  PipelinesDeploy has 0 hooks. All 87 repos in `jenkins-config/repos.txt` carry exactly one
  Jenkins hook, so "every repo with a job today" has the hook, as the note says.
- **Runbook sentence.** The sentence close-out P5 corrects is at Ansible
  `docs/runbooks/argocd.md:134-136`.
- **P8's premise.** 78 of 79 `xml/AaC/*.xml` configs already carry `GitHubPushTrigger`. Creating
  `AaC/PipelinesDeploy` with the trigger matches the estate's shape. The one exception is
  `Home Assistant Fleet`.

**Unexercised, and why it does not block.** The record lists `createItem` inside a folder as
untested (plan.md:290, report.md recipe step 2). P8 relies on that form for `AaC/PipelinesDeploy`.
The observed split between the two forms fits Jenkins starting a trigger as a new instance only
during an XML load: `createItem`, or a `config.xml` POST. The declarative `properties` path does
not. A folder's `createItem` goes through the same XML load. P8 also checks the hook itself with
`gh api …/hooks`, and report.md's re-post variation covers the case where the hook is missing. No
finding.

The executor's edits to P8, P9 and Ordering are within its remit (code-writer rule 2: later
phases are edited in place). Each follows from the witnessed result. The done-record has the
template's two-part shape.

## Findings

None.
