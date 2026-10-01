# How a migrated Jenkinsfile lands

What P4–P9 share: the phases that rewrite the estate's build and deploy files. Each phase names
its own files and constraints. This page says what "to the guide" means for this slice, and how
a file reaches the test phase's one push.

## What the file is

- **Its type's reference file, with its own values.** `docs/pages/types/index.md` in
  JenkinsPipelineUtils names each type and the job each reference file comes from. A migrated
  file starts from that reference file as P1–P3 leave it. Its header, images, pins, stages and
  arguments are its own. Where a job *is* its type's reference job (PaperClock, Intercom, Ginbov,
  ScanToPdfServer, SSEGateway, YouTrackConfiguration, Promote-PRD, DockerImages, AaC/Architecture,
  AaC/Home Assistant Fleet, IaC/IaC Docker Image, IaC/Scheduled Calico Rollout, and the five apps'
  new type), its file becomes the reference file. If the live file now does something the
  reference does not, the job keeps doing it. The done-record names that difference so P11
  can bring the reference file into line.
- **The job keeps doing what it does today**, apart from what a requirement changes. That means
  the same images and tags, the same pins (deploy repo, values file, keys), the same artifacts
  archived and the same downstream jobs started, the same devices flashed, the same pushes and
  the same applies. A migration that drops or adds an effect is a defect, not a cleanup.
- **The header follows FILE-3.** Its `Controller config:` block comes from the job's live
  configuration: `GET …/config.xml` as `admin` with `JENKINS_TOKEN`, read-only. A why that an
  old comment carries and that still holds may stay (FILE-7). Comments that were true only while
  the file was being built go.
- **Job properties come from the guide alone** (Ruling D2). PROP-3's table decides
  `abortPrevious`. The trigger is the job's live one, in the file (PROP-6): a push, the UI's cron,
  or none for a hand-started job. Parameters go in `parameters {}` (PROP-7). There is no
  `buildDiscarder` (PROP-5) and no `properties` step (PROP-8; AaC/Architecture is the one
  exception). The UI's copies are left in place (S12). The file's value applies from the job's
  second declarative build (G3).
- **Every file passes the controller's declarative linter**: a read-only POST to
  `…/pipeline-model-converter/validate` as `admin` with `JENKINS_TOKEN`, the way
  JenkinsPipelineUtils' `docs/lint_examples.py` sends it. The linter does not evaluate library
  calls. A file calls only what P1–P3 put in the library, which the test phase pushes before any
  consumer.

## Where the edit lands

- **Repos this environment checks out are edited there**: `/work/Architecture`,
  `/work/ArgoCDTools`, `/work/Charts`, `/work/DockerImages`, `/work/HomelabTerraformProvider`,
  `/work/Ansible`. Their duplicates under `/work/scratch/` are stale and are not touched. Every
  other repo is edited in `/work/scratch/<Repo>`.
- **The branch is the one the job builds**, with the clone brought to origin's head first:
  `test` for TrelloMcp (`mcp-server-trello`; the clone has `main` checked out, and the
  Jenkinsfile exists only on `origin/test`). For the four repos R11 renames, it is `master` until
  the test phase renames them. KubeCoderDeploy uses `main`, the branch Promote-PRD builds.
- **One commit per repo**, its only commit ahead of origin. A clone that already holds a commit
  not on origin is not edited; the phase reports it.
- **Nothing is pushed** (R18). The test phase pushes every repo in one go.

## The ledger

`migration-ledger.md` in the slice folder is the test phase's push list for every repo the run
does not track itself. P4, P5, P6 and P8 commit in repos other than their `Target:` and leave no
commit on the Ansible branch. They add one row per file to the ledger, with these columns: Repo,
Job, Clone, Branch, File, Commit. P4 opens the ledger. The ledger is committed in AnsibleSpecs,
staged by name. The reviewer reads those phases' commits through it. P7 and P9 commit on their
own phase branches and need no rows.
