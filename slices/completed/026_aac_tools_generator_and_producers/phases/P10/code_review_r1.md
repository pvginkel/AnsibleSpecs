# P10 code review — round 1

**Readiness.** The Ansible diff (`b92d01a`) is correct and complete. `Jenkinsfile.architecture:4,12-13`
runs `arch-validate` in `containerTemplates.aac_tools`, the same way every deploy repo does (e.g.
`ArgoCDDeploy/Jenkinsfile.architecture:22,32-34`). The `architecture` gate (`.kubecoder/project.yaml:55`)
runs `cexec aac-tools arch-validate`, and this environment declares `aac-tools` (`.kubecoder/config.yaml:113`).
The copy is deleted, no reference to it remains in the repo, and the branch is unpushed. The enumeration
also holds up on an independent re-run. Gitblit `find_files` `**/arch-validate.py` returns 36 files in 33
repos. GitHub's recursive trees of all 114 non-archived repos (none truncated) hold the file in 30 of them.
A wider `*arch*valid*` match finds only Architecture's `service/test/arch-validate.test.ts` in addition.
So 28 carriers, as recorded. The classification, however, puts four carriers whose push redeploys
production into the "rolls nothing out" class. P11 would push them without the health gate Ruling D1
makes the condition of the push. That is P10's own output, and it needs a fix round.

## F1 — Major · blocking · anchor: repro-trace · confidence: high

**Four carriers classed "no rollout" redeploy prd through downstream jobs their push starts.**

P10's job is to class each carrier by what a push to its default branch sets off
(plan.md:47 Grounding, :661-667), and its record says "the Grounding's lists hold, with two
exceptions" (plan.md:702). The Grounding's "legacy artifact builds, no image, no pin" (plan.md:48) is
true of the four carrier jobs themselves. It is false of what they start:

| Carrier (P11) | Its `Jenkinsfile` starts | That job | Argo CD Application |
|---|---|---|---|
| ScanToPdfServer | `build job: 'ScanToPdf'` (:31) | `ScanToPdf/Jenkinsfile:25-39` kaniko, `writeVersionPins` → ScantopdfDeploy, tag `:${currentBuild.number}`, no guard | `scantopdf-prd`, `automated: {prune: true}` |
| ScanToPdfClient | `build job: 'ScanToPdf'` (:50) | same | same |
| MyDownloadsServer | `build job: 'MyDownloads'` (:37) | `MyDownloads/Jenkinsfile:22-34` kaniko, `writeVersionPins` → MediaDeploy | `media-prd`, automated |
| MyDownloadsClient | `build job: 'MyDownloads'` (:50) and `build job: 'Webathome'` (:55) | the above, plus `Webathome/Jenkinsfile:22-34` → WebathomeOrgDeploy | `media-prd` and `webathome-org-prd`, automated |

Jenkins shows the chain firing on real pushes: `ScanToPdf/ScanToPdf` #33 was "Started by upstream
project ScanToPdf/ScanToPdfServer #20" and #34 by ScanToPdfClient #50. `MyDownloads/MyDownloads` #98 was
started by MyDownloadsServer #32 and #100 by MyDownloadsClient #68. `Webathome` #236 and #238 were
started by MyDownloadsClient #67 and #68. All jobs are buildable.

**Repro.** P11 pushes ScanToPdfServer in batch 2, and ScanToPdfClient, MyDownloadsServer and
MyDownloadsClient together in batch 3 (plan.md:727-737). The chain then runs:

1. Each push starts the carrier's job.
2. That job starts `ScanToPdf`, `MyDownloads` or `Webathome`.
3. Each of those builds a new image and commits a new pin.
4. `scantopdf-prd`, `media-prd` and `webathome-org-prd` auto-sync and roll prd on unchanged code.

**Effects.**
- **No health gate on these rollouts.** Neither the P11 section nor the ledger rows (sweep_ledger.md:89-92,
  class "no rollout") tell P11 to wait for those Applications to be Healthy at the new pin. Ruling D1
  (plan.md:15) requires "each batch's builds green and its rollouts healthy before the next". The
  attachment's done-rule (push-sweep.md:47) requires the same for "a carrier that pins into one".
  The next batch and the P12 class would proceed over an unchecked prd rollout.
- **Two builds pin MediaDeploy in batch 3.** MyDownloadsServer and MyDownloadsClient both start
  `MyDownloads`. That breaks P10's own assignment rule "Carriers that pin the same deploy repo go in
  different batches" (plan.md:706).
- **P11's wait figures are off.** They count only the carrier jobs (e.g. "ScanToPdfServer … about
  1 min", plan.md:735). They leave out the downstream image builds, e.g. `ScanToPdf` #36 took 483 s
  and `Webathome` #237 took 2456 s.
- **The prd-app count grows.** The apps that restart now include scantopdf and media. D1's
  accepted trade-off (plan.md:15) was "twelve production apps", and FieldnotesApp already makes
  thirteen.

Every other carrier's Jenkinsfiles were checked for downstream `build job:` triggers and pin
targets, and their classes hold. Only these four are misclassed. KitchenDisplay's job is confirmed
disabled (`Firmware/KitchenDisplay` buildable=false).
