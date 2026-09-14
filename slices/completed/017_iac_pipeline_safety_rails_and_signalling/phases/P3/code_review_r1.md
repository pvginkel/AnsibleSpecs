# P3 code review — round 1

Range `82d34ace..ddca1078` (one commit, `Jenkinsfile.iac-apply` only). Gate: green on `ddca1078`,
but `root` has no test statements (close-out N1), so the green covers nothing in this diff.

**Readiness: ready to merge. Nothing is blocking.** The phase's outcome is met. `iac-apply`'s two
Terraform stages are now one, `Terraform plan + destroy check + apply (prd)`
(`Jenkinsfile.iac-apply:64-82`). It runs in one `iac -c`, which `iac-impl` runs as
`sh -c` (`support/iac-agent/bin/iac-impl:500`), so `set -e` applies to every line. The steps in
order are `init`, then `plan -out=/tmp/plan.tfplan` (exits on any rc other than 0 or 2, :75), then
`show -json`, the guard (:77) and `terraform apply … /tmp/plan.tfplan` (:78). A plan Terraform
refuses exits at :75. A guard exit of 1 (a VM delete) or 2 (a usage error, which includes srviac's
old installed script until A1 runs) stops the script before :78, so neither applies anything. The
plan file is created and used only inside that container. The Ansible stages (:84-174) are
byte-identical to the base, and there is still no `input` step. The two comments are accurate:
:13-18 says why plan, check and apply share one call, and :62-63 says why the plan file must not
leave the container. Neither narrates change history.

Targeted run, to check the path the executor's record covers only in prose. I took the stage body
verbatim (`sed -n 68,78p Jenkinsfile.iac-apply`, with only the `cd` target and the guard's path
rewritten) and ran it with `sh -c` in the `iac` sidecar (Terraform 1.16.2, `/bin/sh` → dash).
The test config was a `terraform_data` whose input comes from a variable set only through
`TF_VAR_`, because that is how `terraform/prd/variables.tf` gets its values in the container.
- No-change plan: `No changes.` then `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.`,
  rc 0. A converge-only `iac-apply` run (no Terraform changes) is not turned red by applying an
  empty saved plan.
- Changed `TF_VAR_v`: `Plan: 0 to add, 1 to change`, applied, rc 0, state shows the new value.
  Variables from the environment do not trip the saved-plan variable check, because plan and apply
  run in one environment.

## Findings

None.

## Notes for later phases (not findings)

- Doc phase: `docs/runbooks/iac-agent.md:26-32` still describes `iac-apply` as "inside one
  `iac -c '…'` per stage" and lists "Repeats the plan + destroy check" and "Applies
  `terraform/prd`" as steps 1 and 2. Those two now share one stage and one call. The P3 record's
  "nothing outside the Jenkinsfiles names either old `iac-apply` stage" is true of the literal stage
  names only, so this is now noted in the plan's P3 later-phases list.
