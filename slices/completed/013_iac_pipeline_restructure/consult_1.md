# Consult 1 — 013_iac_pipeline_restructure — `complete`

Generation 0, all three phases merged, loop-tail sweep green on `60ca07b` (12/12 rows).

## Requirement → delivering work

| Req | Delivered by | Checked how |
|---|---|---|
| R1, R2 | PA (`99e8416`, `3e3aa33`) | `Jenkinsfile.iac-image:28-56`. Input set re-derived from the Dockerfile this pass: the only `COPY`s are `:11` (root `pyproject.toml`/`poetry.lock`), `:25` (build stage), `:72` (`homelab-root.crt`), `:85`/`:121` (`support/iac-image/`), `:129` (pinned external image), `:142` (`known_hosts.d/homelab`). Every one is watched or is not a repo input. `support/iac-image/` holds exactly the three files the Dockerfile reads. |
| R2 ruling (full-match) | PA | All six patterns are anchored regexes with escaped dots; the one directory prefix carries `/.*`. |
| R3, R5 | PB (`3911c33`, `8eba51a`) | 28 prefixed commits; `iac_agent_local_checkout: {{ playbook_dir }}/../../support/iac-agent` resolves to `<repo>/support/iac-agent` from `ansible/playbooks/`. |
| R4 (in-tree) | PC (`7461c61`, `60ca07b`) | `grep modern-app-dev support/iac-agent/` empty; README's five bind-mounts match `bin/iac:63-69`, its six `iac-controller` jobs match the root's `Jenkinsfile.*` set, `iac-image`/`architecture` correctly split out as pod-agent jobs. |
| R4 (outside the tree) | doc phase | PB and PC both hand it over by name: `ansible/roles/iac_agent/README.md:12,20`, `docs/runbooks/iac-agent.md:15,154`. Role documentation is surface 4 of `docs/slice-doc-plan.md`. |
| R6 | operator-owed, handed back by the test phase | `docs/slice-testing-strategy.md:63-75` makes the deploy-owed command the test phase's close-out. PB's done-record already carries it, and `iac_agent` is a real group (`ansible/inventories/prd/hosts.yml:53`). |
| R7 / V13 | doc phase | `docs/slice-doc-plan.md:46-55` — the model is a nudge, not an edit; `ansible-architecture.yaml:338` is what the nudge is about. |

## Held-out lines, verified still held out

`Jenkinsfile.iac-apply:94` and `Jenkinsfile.iac-scheduled-drift:86` both keep `--limit "!iac_agent"` (V14). `.kubecoder/config.yaml:12` and `Ansible.code-workspace:16` still declare IaCAgent and `/work/IaCAgent` is still on disk (V12, N5/N7). All four N4 files are unchanged apart from the single `bin/send_message.py` docstring line V15 permits. Every Jenkins call site of the moved helpers goes through `iac -c` and the container's bind-mounts, never a repo path, so the move cannot have broken them (V16).

## Mechanical residue — fixed here

Ansible `d1005fa`, AnsibleSpecs `cee6c05`; comments only, `kc project lint` green afterwards.

- `support/iac-agent/bin/iac-impl:6` cited `openbao.md §Secrets resolver`. That file's sections are *Where the design lives / What shipped / Operational lessons / Caveats / Followup* — no such anchor. Dropped the anchor; the file pointer and the `iac-secrets-resolver` slice pointer beside it both resolve. (PC r2 flagged this; it is in a line PC's own commit rewrote.)
- `Jenkinsfile.iac-image:29-30` asserted that a build with no changeset *is* the version poller's weekly rebuild. A hand-started build with no new commits since the last one takes the same branch — job history #117 is one. Reworded to say the poller is the case in practice and that rebuilding is right for both; the rationale that follows is unchanged, and no code moved.
- `plan.md`'s PC done-record still described the pre-r1 wording of `bin/iac`'s missing-`iac-impl` hint (`/opt/IaCAgent/install.sh`), which the r1 note 35 lines below supersedes with the location-agnostic text the file actually carries.

## Why nothing was appended

The three open items are advisory or need a ruling, so they are carded:

1. **No AC covers the empty-changeset branch.** PA's r2 reviewer said so and it still holds — the branch that keeps the weekly rebuild alive is the only part of the gate the test phase has nothing to check off. Writing a criterion is not phase-shaped work, and V01/V02 are pipeline-observed anyway.
2. **The residual poller hole.** A poller build that absorbs commits touching no image input is skipped and never retried. The r2 reviewer tagged it advisory and said resolving it likely needs an operator ruling; the "no escape hatch" ruling weighed *manual* forcing, not the poller, so it is not a decision this loop should take.
3. **`tools/ai_workflow/send_message.py:6`.** Its provenance pointer at `/work/IaCAgent/bin/send_message.py` went stale with the move, and no phase owns it — but absorbing it would break V15 as written, which bounds the content change across those four files to the one `bin/send_message.py` docstring line. Operator's call, not a touch-up.
