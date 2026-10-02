# P4 code review — round 1

Range `b2fb04f..d7db58f` on ArgoCDTools `phase/037-P4`. The gate (`kc project test`) is green on
`d7db58f` (`phases/P4/gate_r1.log`), and I took it as given.

**Readiness: sign-off.** The destroy mode does what P4 requires. It is a separate entry point
(`python3 -m presync.destroy`). `cli.py`, `ArgumentContractTests` and the `ENTRYPOINT` are
untouched, and the Dockerfile change is a smoke import. The run inits against the stage's existing
key. It forgets only `hashicorp/kubernetes` managed instances that carry a namespace, and a dry run
plans against a local copy of the state through a `_override.tf` file. No path in a dry run locks,
writes or commits. An apply forgets, plans with `-out`, applies the saved plan, and runs
`state list` before it touches TerraformState. An empty lineage reads as "no state", so a stage
without state gets none.

The suite covers every case the plan names: a dry run against an apply, a Secret beside a PV and an
RBD image, an empty state, a missing state, a folder already gone, a clone without
`config/<stage>/`, and a configuration that does not plan. The `RealTerraformTests` show with
Terraform 1.16 that orphans are planned for deletion even under `prevent_destroy`, and that the dry
run makes no backend write. They also show that a no-state run creates nothing and that a re-run
writes nothing.

I probed further:
- The HCL reader returns the right top-level blocks for every root `*.tf` of the seven deploy repos
  under `/work/scratch`. It also handles braces inside interpolated strings, heredocs, comments,
  escapes and `$${`.
- Real Terraform accepts `state rm -no-color`, which the apply runs and the real-Terraform tests do
  not reach.
- No `*.tf` the gitblit index holds uses a `helm` or `kubectl` provider, so restricting the forget
  to `hashicorp/kubernetes` misses nothing today.
- `kc project lint` is green.

One more fact concerns P5 rather than P4. GitHub clones a repo under any case of its name, but
TerraformState's paths are case-sensitive. A `REPO` typed in the wrong case therefore gets a green
"nothing to destroy" Job. I recorded it in the plan under P5 ("Review P4 r1 (fact)") because the
guard and the `config/<stage>/` removal live there. It is not a P4 defect: P4 does what its plan
asks when the state is already gone.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**Every init or plan failure is blamed on the empty configuration.** `_declared`
(`argocd-hook/presync/destroy.py:259-268`) wraps every `init` (`:90`, `:136`) and every `plan`
(`:137`, `:149`). Whatever the cause, the run's last line is `presync: the empty configuration,
terraform/ reduced to its terraform, provider and variable blocks, does not init|plan`.

Many of these failures have nothing to do with the declarations:
- **At init**, the backend failing to read the state repository.
- **At plan**, refreshing the resources still in state against live systems: Ceph unreachable for
  the RBD image, a `403` on a cluster-scoped object the `tf-presync` identity cannot read, or the
  GitHub API failing on a webhook.

Those refresh errors are the most likely way a real destroy fails. The done-record still hands P6
this message as what "a root whose declarations do not plan alone" looks like
(`plan.md:396-401`). An operator following the runbook would look for the fault in the deploy
repo's declarations rather than in the infrastructure. Terraform's real error is printed above, and
the message points to it, so nothing is hidden. It is a wrong headline, not a wrong outcome.
