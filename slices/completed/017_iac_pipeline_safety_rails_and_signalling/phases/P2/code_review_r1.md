# P2 code review — round 1

Range `b495c24..82d34ac` (branch `phase/017-P2`). Gate: green on 82d34ac (`kc project test --project root`, which runs nothing — close-out N1).

**Readiness: ready to merge; no findings.** P2's outcome is met.

- **Guard filter** (`support/iac-agent/bin/check-protected-vms.sh:35-49`). It keys on `type == "proxmox_virtual_environment_vm"`, the only resource of that type in `terraform/prd` (`terraform/modules/managed-vm/main.tf:52`), and on any action list containing `delete`. Tested against synthetic plan JSON:
  - `delete,create`, `create,delete` and a deposed `delete`: rc 1, one verdict line each.
  - `update`, `forget`, and a DNS-reservation delete next to a VM create: rc 0.
  - Invalid JSON, a missing file, and zero or two arguments: rc 2.

  The HEAD~ guard, given the same plan with `srviac`, missed the VM's `delete,create` and flagged only the DNS reservation's `delete`. That is the defect P2 fixes.
- **Rollout skew** (plan constraint: a caller and script that disagree must fail). The old installed guard, called with the new one-argument form, exits 2 (`[[ $# -lt 2 ]]`). All three callers run it as a plain command under `set -e`: `Jenkinsfile.iac-apply:73`, `Jenkinsfile.iac-on-push:47`, `Jenkinsfile.iac-scheduled-drift:193`. So the job goes red and never passes a plan unchecked. The new guard called with names also exits 2.
  - `iac` bind-mounts only the installed copy (`support/iac-agent/bin/iac:49`), and the `iac` image bakes in no copy of its own.
  - No caller outside this repo exists.
  - The rollout order is recorded in the Done record and in close-out A1.
- **Drift `|| true`** is gone (`Jenkinsfile.iac-scheduled-drift:193`).
- **Refusal naming** (`Jenkinsfile.iac-scheduled-drift:108-119`). I checked the verdict line on both sides:
  - The guard prints `check-protected-vms: plan deletes or replaces prd VM <address> (<actions>)` starting at column 0. `iac-impl` runs `sh -c` with no output rewriting, so `:86` matches it.
  - The refusal pattern runs over a sample refusal log where one address wraps between `Resource` and `has`. It yields one `Terraform refused to destroy …` line per instance, ahead of the plan headers, so the refusals survive the 10-line cap.

  Two things remain unproven without a JVM, as the Done record says, and are owed to a live drift run on a refusal (V08):
  - that the Groovy itself runs;
  - that the sandbox allows `Matcher.find()` and `Collection.addAll`. No other sandboxed Jenkinsfile in the estate calls either.
- **Comments.** The new comments carry a reason and match the code.
- **Doc drift, left to the doc phase.** `support/iac-agent/README.md:12` and `docs/runbooks/iac-agent.md:23` still describe named VMs. The plan already routes both to later phases.

## Findings

None.
