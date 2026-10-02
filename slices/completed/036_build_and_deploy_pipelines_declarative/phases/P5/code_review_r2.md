# Code review — slice 036, P5, round 2

Ready to merge. The Ansible range `3f277a5..HEAD` is empty again: P5's work is the ledger's clone
commits. Round 2 changed only the four commits named in r1 F1. Each was amended in place, and
`git diff` of each against its r1 SHA shows the same three added lines and nothing else:
`yamlMergeStrategy merge()` after `inheritFrom 'jenkins-agent-large'`, with a two-line comment
saying why.

| Clone | r1 commit | r2 commit |
| --- | --- | --- |
| MyDownloadsClient | `f3ba771` | `5512a55` |
| MyDownloadsServer | `62827f1` | `86eb8f9` |
| ScanToPdfClient | `c9769ca` | `5fac958` |
| HomelabTerraformProvider | `a0300c2` | `160ad9b` |

Each clone is clean, with that commit as its only one ahead of origin on the branch the job
builds. The ledger carries the new SHAs (AnsibleSpecs `82611bc`).

**The fix restores the placement.** Checked in the plugin source, kubernetes plugin
4557.ve746270f672f:
- `Merge.merge` combines every YAML in order.
- `PodTemplateUtils.combine(Pod, Pod)` (`PodTemplateUtils.java:267-391`) starts the spec from the
  parent's spec (`withNewSpecLike(parent.getSpec())`). It overrides only the fields it names, and
  affinity is not one of them, so `jenkins-agent-large`'s nodeAffinity survives. Tolerations are
  concatenated.
- podYaml renders only `spec.containers`, with container-level `securityContext`. `combine(null, c)`
  returns the child's container unchanged (`:133-134`). So the go, iac-toolchain (uid 1000), mvn and
  androidsdk containers are the same as under Override.

The executor's Script Console witness reached the same result.

**Checks run in this review:**
- All four amended files pass the controller's declarative linter ("Jenkinsfile successfully
  validated.").
- A grep of all 19 P5 files finds no other `jenkins-agent-large` agent without `merge()`.
- The one P5 file on bare `jenkins-agent` (ScanToPdfServer) loses nothing under Override. The
  live `jenkins-agent` template's YAML is empty (read-only GET of
  `/manage/cloud/Kubernetes/template/ed7657a3-…`).

**The comment** states a constraint, not what the code does, so it meets FILE-7
(`docs/pages/guide/file-layout.md:80`).

**Already in the close-out report** (entered by r1): the same defect in the guide's POD-3 premise
and in P4's firmware files (B2), and r1 F2 (P6).

No findings.
