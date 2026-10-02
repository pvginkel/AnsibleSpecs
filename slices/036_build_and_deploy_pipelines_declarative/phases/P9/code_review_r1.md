# Code review — slice 036, phase P9, round 1

Range: Ansible `3f277a5..90d69a0` on `phase/036-P9` (7 files). Gate: green on `90d69a0` (input).

**Readiness: ready to merge, no findings.** The seven `Jenkinsfile.iac-*` files are declarative
files to the guide, and none of the jobs' effects changed:

- **Reference files.** `Jenkinsfile.iac-scheduled-calico` and `Jenkinsfile.iac-image` are
  byte-identical to `docs/examples/iac-controller.groovy` and `change-detection.groovy` once the
  section markers are dropped (diffed).
- **Rules.** The other five follow that reference:
  - PROP-1/2 block and options order;
  - plain `disableConcurrentBuilds()` with a PROP-3 reason comment, matching the PROP-3 table
    (`job-properties.md:50-58`);
  - `skipDefaultCheckout()` and a `Checkout` stage (CHK-4);
  - `timeout(time: 4, unit: 'HOURS')` (TIME-2), and 60 minutes on the image build;
  - the POST-3 abort marker;
  - no `buildDiscarder` (PROP-5);
  - POST-2 dev stages with no `DEV_STAGE_FAILED` flag, each bounded in the shell (TIME-5);
  - a library line on `iac-on-push`;
  - FILE-3 headers with no trigger lines;
  - LABEL-1/3/4 labels.
- **What I checked against live state and the code:**
  - **Linter.** All seven files return "Jenkinsfile successfully validated." from the controller's
    linter (read-only POST, run in this review).
  - **Triggers.** The triggers match the live `config.xml` of each IaC job: `githubPush` on
    Build-Main and IaC Docker Image; cron `H 4 * * 3`, `H 4 * * 5`, `H 11 * * *` and `H 4 * * 0`
    on the scheduled jobs; none on Apply.
  - **Commands.** The effectful command lines are unchanged in every file: playbooks, limits,
    `--skip-tags`, shell bounds, the terraform plan/check/apply, and the kaniko destinations and
    `params`. The only removed line is a history comment inside drift's terraform shell script.
  - **Timeouts.** No historical build comes near either bound. The longest are Calico #1 at
    154 min, Update #13 at 63 min and the image build #212 at 27 min (successful).
  - **Checkout.** `iac -c` clones the default branch itself (`support/iac-agent/bin/iac-impl:371-384`),
    and no file reads `GIT_*`. So dropping the default checkout's SCM env vars changes nothing.
  - **Stage names.** The drift stage names passed to `prdCheck`/`recordDrift` match their stages.
  - **Builds.** No IaC job was started during the phase: every last build is a timer, a push from
    before the phase, or the operator's hand.

Accepted as recorded in the plan's done-record, so not findings:

- Apply's dev stage keeps site-k8s and site-ceph in one stage. The done-record gives the reason:
  split, site-ceph would run after a failed site-k8s.
- LABEL-3's iac examples do not match the files' labels. That is P11's to reconcile.

What remains:

- The runbooks and `decisions.md` still cite the old stage labels. That is prose for the doc
  phase. It is already close-out P10, and I noted the `decisions.md:165,175` cites on it.
- V24 and V25 are owed to the jobs' own next runs (close-out A3, A4).

## Findings

None.
