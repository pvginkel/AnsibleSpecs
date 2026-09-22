# P3 code review, round 1: the KubeCoder cutover runbook

**Readiness: sign off.** `docs/runbooks/kubecoder-cutover.md` carries every constraint in the
phase's list in the order the rulings set. Build-Main is rewritten before dev's flip. Each stage's
flip comes before its surgery. Deploy-PRD goes only after the promote job and prd's sync. `_shared/`
goes only after prd's surgery. prd's flip waits on `prd` born, then the producer green, then the
producer registered. The replay check runs before each diff review. It also covers V01–V22's
runbook-side content.

I checked the steps that can delete production against the code and the live estate, and they
hold:

- The `TFB` shorthand is the same URL, repository, ref and encryption keypair that the hook and
  HelmCharts' CLI use (`argocd-hook/presync/backend.py:22-26,57-64`, `deploy_cli/tf.py:47-68`,
  ArgoCDDeploy `values.yaml` SOPS recipients).
- HelmCharts' `static-zfs-pv` module and KubeCoderDeploy's `storage.tf` declare the same
  attributes, and the live PVs match them (`kubecoder-{dev,prd}-zfs-pv`, the claimRefs, `/zpool5/…`,
  srvk8s4). The plan's "1 to add / No changes" expectation is sound.
- The plan's environment matches every variable KubeCoderDeploy declares, and setup-env's message
  strings are quoted exactly.
- In Argo v3.5.1, `SyncPolicyAutomated.SelfHeal` is a `*bool`, so D9's `{"prune":true,"selfHeal":false}`
  is what the patch produces.
- Build-Main's `config.xml` holds exactly the two properties D1 re-declares. The `KubeCoder`
  folder holds only Build-Main and Deploy-PRD, so P12's job-list check is exact.
- The deploy CLI's refusal text, the hook Job's `BeforeHookCreation` policy and namespace, the
  `tf-presync` ClusterRole, the KubeCoderDeploy hooks list and every link and anchor all check
  out.
- I rendered HelmCharts' `charts/kubecoder` and KubeCoderDeploy's `chart/` for both stages and
  diffed them per object. prd's differences are dev's, row for row, with `prd-latest` in place of
  `dev-latest`. `Service/kubecoder-mcp-public` renders identically in both, so argocd.md's new prd
  paragraph and the corrected table hold.

What remains is four advisory findings, none of which changes what a stage ends up running.

## F1: the pre-flight dumps the stage's ESO Secrets in plaintext, but the Conventions say only the plan touches OpenBao-held credentials

- Minor · advisory · anchor: none · confidence: high
- Evidence: `kubecoder-cutover.md:23-25` states *"Claude reads no OpenBao value. Only the
  no-destroy plan needs OpenBao-held credentials."*
- The pre-flight (`:301-322`) runs argocd.md's `kubectl get …,secret,… -o json > /tmp/live.json`
  (`argocd.md:554-556`). That writes all eight ESO-materialised Secrets of the stage into a file in
  this container: `kubecoder-github-token`, `kubecoder-bot-token`, the step-ca provisioner
  password and the rest. Line 321 acknowledges the plaintext.
- The pre-flight does not say whose keystroke it is. Under the runbook's own Conventions a read is
  the accompanying session's. So a session that trusts line 24 runs a command that returns
  OpenBao-sourced credentials, without the per-path permission the house rule asks for. The values
  go to a file rather than into the transcript, which is why this is advisory.

## F2: P2's hand-written `release-<m>` command drops the image references its own prose requires

- Minor · advisory · anchor: none · confidence: high
- Evidence: `kubecoder-cutover.md:741-742` says the message is *"this line, a blank line, then the
  seven references from the build log"*. The command at `:745` passes a single `-m` with the first
  line only.
- The job writes `…\n\n<seven image:tag lines>` (`Jenkinsfile.promote:119-128`). A tag made by
  copying the command is the one D48 release record without the images it promoted. `git show
  release-<m>` then disagrees with every job-written tag.
- This is a follow-up to close-out S6.

## F3: X1 says `helm list` "must print nothing", but Helm 4.3 prints its header on an empty namespace

- Minor · advisory · anchor: failing-test · confidence: high
- Evidence: `kubecoder-cutover.md:919,923`. Run in the sidecar,
  `cexec iac helm list -n development` (v4.3.0, no releases there) prints
  `NAME	NAMESPACE	REVISION	UPDATED	STATUS	CHART	APP VERSION` and nothing else.
- An operator who holds the check to its words sees one line where none was promised.

## F4: P3 leaves the shared KubeCoderDeploy checkout detached, and later steps assume `main`

- Minor · advisory · anchor: none · confidence: medium
- Evidence: `kubecoder-cutover.md:757-758` has `/work/KubeCoderDeploy` checked out at
  `origin/prd`'s commit for the equality check, and nothing puts it back on `main`.
- P6's plan requires *"The working tree must be `origin/main`: run `git -C /work/KubeCoderDeploy
  pull --ff-only` first"* (`:248`), and P7's replay check runs `git pull --ff-only` (`:298`). Both
  fail on a detached HEAD whenever main has moved past `prd`. The failure is visible, not silent.
  It lands in the middle of prd's surgery and plan, and nothing there says what to do.
