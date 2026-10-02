# P6 code review, round 1

**Ready to merge.** The phase's four commits each sit alone on `main` in their clones: DockerImages
`df3906d`, YouTrackConfiguration `c878458`, KubeCoderDeploy `c9dfe03` and SSEGateway `a3aa6bc`. A
`git ls-remote` shows each clone's `origin/main` is still origin's head, and the ledger has a row
for each. Each file is its type's reference file with the section markers removed
(`diff -u docs/examples/<type>.groovy <file>`). The one exception is Promote-PRD's bare-run
refusal (`Jenkinsfile.promote:129-135`) and the header sentence that describes it, which the
done-record hands to P11.

I ran the controller's declarative linter on all four files as committed, and all four passed.
I then compared each new file with the scripted file it replaces. They build the same images and
tags: kaniko2's positional wrapper (`helmCharts.groovy:20-27`) gave the old calls the same
labels, and the matrix destinations are unchanged. They write the same pins to the same repos, push
the same `stable` branch, apply the same configuration, and run the same Promote-PRD gate, retag,
prd fast-forward and release tag. Promote-PRD's handoff lines are unchanged, and they still match
`track_build.py`'s `_HANDOFF_RE` (`:173-178`).

Promote-PRD's gate now reads the clone that `checkout scm` makes. That works because the job's
`config.xml` sets no refspec and no extensions (`jenkins-config/xml/KubeCoder/Promote-PRD.xml:29-43`),
so the fetch takes every branch, `origin/prd` included, and every tag. SSEGateway's Job manifest
no longer sets a namespace, which is safe because `kubectl.startJob` fills it in
(`kubectl.groovy:18`). PROP-3 lists all four jobs as plain `disableConcurrentBuilds()`, and each
file carries the abort marker. The P6 record's claims about the UI's `abortPrevious` and triggers
match the jobs' `config.xml`. No describable and no positional `kaniko` is left in the four
repos.

One advisory prose finding remains.

## F1 — Two operator docs name Promote-PRD stages that no longer exist · Minor · advisory · anchor: none · confidence high

**Evidence.** The migrated `Jenkinsfile.promote` names its stages `Checkout`, `Validate commit`,
`Retag images`, `Advance prd` and `Tag release` (`KubeCoderDeploy/Jenkinsfile.promote:101-205`).
Two docs still use the old scripted names:

- KubeCoder's `docs/operations/deploy-operations.md:150` says "A run that fails at *Recording the
  release* has already moved `prd`".
- Ansible's `docs/runbooks/kubecoder-cutover.md:780-784` names *Advancing prd*, *Recording the
  release* and *Resolving the commit* in its failure procedure.

**What it costs.** An operator reading a red Promote-PRD build against either doc looks for a
stage the stage view no longer shows. The renamed stage is easy to recognise, and what each doc
says happens is still true, so following them does no harm. The Ansible runbook belongs to the doc
phase, since Ansible is one of the run's own targets. KubeCoder is not one of the run's targets,
so the doc phase does not see that line. P8 commits to the same KubeCoder clone. Entered in the
close-out report.
