# Code review — slice 020, phase P1, round 1

Range: `c0d943d..797b530` on `phase/020-P1` (Ansible). Two files: `.ansible-lint` and
`ansible/roles/microk8s/tasks/elect-primary.yml`.

**Readiness: ready to merge. No findings.** The phase delivers its outcome (plan §P1, AC V01).
`.ansible-lint:20` is now `strict: true` and the "once roles stabilize" comment is gone. The
`jinja[spacing]` warning is fixed in the task itself, with no `skip_list` entry (`skip_list: []`
at `.ansible-lint:8`) and no `noqa`. The mandatory-var placeholders at `.ansible-lint:15-18` are
unchanged. I made two targeted checks beyond the green gate:

- **Strict is live from `ansible/`.** As a mutation, I put the pre-phase `elect-primary.yml` back
  and ran `ansible-lint roles/microk8s/tasks/elect-primary.yml` from `ansible/`, which is the
  gate's working directory. It exited 2 with "Listing 1 violation(s) that are fatal", the
  `jinja[spacing]` warning at `:44`. So the root `.ansible-lint` is found through the git root and
  makes warnings fatal, and the plan's "P2 needs no `--strict` flag" note (plan.md:77-78) holds. I
  restored the file afterwards and the tree is clean.
- **The rendered value is unchanged.** I took the two `_microk8s_node_state` expressions from
  `c0d943d` and `797b530` through the YAML loader, so the folded-scalar joining is real. I then
  rendered them side by side under jinja2 (`trim_blocks`, with `bool`/`from_yaml` stand-ins) across
  44 cases. Those cover the worker flag as true, false, "yes" and "no", crossed with 11 status
  shapes: a missing stdout, an empty one, a plain message, a YAML list, and running with 3, 1, null
  and absent HA nodes. Every case gave the same output in {worker, down, in-cluster, running-solo}.
  Structurally, every tag in the new layout (`elect-primary.yml:45-57`) strips on both sides. Each
  branch word therefore sits between two stripping tags, just as before. Dropping the parentheses
  is precedence-neutral: `|` binds tighter than `or`, and each `set` right-hand side was already a
  single expression.

## Findings

None.
