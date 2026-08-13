# Phase PB — code review r1

`git diff 3e3aa33..8eba51a` on `phase/013-PB`

## Readiness

Ready to merge. The phase's two claims both hold under direct verification rather than on the
executor's word. **History (R5/V07):** the 28 IaCAgent commits are present as `3911c33^2`, with
author, author-email, author-date, committer, committer-email, committer-date and subject
byte-identical to `/work/IaCAgent` `973d330` in the same order, and each rewritten commit's
`ls-tree -r`, with the `support/iac-agent/` prefix stripped, equals the original commit's exactly —
so the rewrite carried the trees, not just the messages. No path anywhere in that history escapes
the prefix (`git log --pretty=format: --name-only 3911c33^2` has zero non-`support/iac-agent/`
entries), so IaCAgent's `README.md`/`install.sh`/`.gitignore` never become root-level blobs
reachable from `main`, and `refs/original/`, the temp branch and the local remote are all gone
(`git for-each-ref` shows only `main`, `phase/013-PB`, `origin/*`; `.git/config` has only `origin`).
**Tree (V06):** `diff -r -x .git` against `/work/IaCAgent` is silent and every blob SHA and file
mode in `git ls-tree -r HEAD support/iac-agent/` matches the source, including the six `100755`
scripts — the move commit adds 1248 lines and changes nothing else. **Repoint (V08):** the one line
that can actually break was executed offline — a throwaway `hosts: localhost` playbook under
`ansible/playbooks/` resolved `iac_agent_local_checkout` to
`/work/Ansible/ansible/playbooks/../../support/iac-agent` and stat'd both files the role reads
(`etc/iac/secrets.example.yaml`, `install.sh`) as existing; the same arithmetic holds for the
container, whose `git clone --depth 1` of the whole repo (`support/iac-agent/bin/iac-impl:372-383`,
no sparse checkout or partial-clone filter) carries the tree. The hold-outs held: no Jenkinsfile,
`.kubecoder/config.yaml`, `Ansible.code-workspace` or duplicate-pair file is in the diff (V12, V14,
V15, N7), and the only reference to a sibling checkout left anywhere outside prose is the
deliberately-kept fallback. Cross-pillar, PA is untouched: `support/iac-image/.*`
(`Jenkinsfile.iac-image:50`) does not match `support/iac-agent/…`, and no `COPY` in
`support/iac-image/Dockerfile` reaches the new tree (lines 11, 25, 72, 85, 121, 129, 142), so the
tree joins the kaniko context and nothing else. Both findings below are advisory — neither changes
what lands on a host. Unrelated: the working tree is dirty with an uncommitted edit to
`scripts/bao-login.sh:22` (adds a `cexec iac` prefix) that is not part of this phase; worth not
letting it ride along on a later `commit -a`.

## Findings

### 1. The parity apply is not the strict no-op the phase record promises — the repointed source's mtimes force all 13 files to re-transfer · Minor · impact: advisory · confidence: high

`ansible/roles/iac_agent/tasks/main.yml:87-95` syncs `{{ iac_agent_local_checkout }}/` to
`/opt/IaCAgent/` and notifies `Run IaCAgent install.sh`
(`ansible/roles/iac_agent/handlers/main.yml:6-8`, `changed_when: true`). rsync's default quick check
is size **and** mtime. `/opt/IaCAgent`'s mtimes were set by previous applies from
`/work/IaCAgent`'s working tree; the new source at `ansible/roles/iac_agent/defaults/main.yml:7`
has mtimes from this branch's checkout — `/work/IaCAgent/install.sh` is `17:40:13`,
`support/iac-agent/install.sh` is `20:05:52`. Same content, different mtime, so every file
transfers.

Demonstrated locally against a `/tmp` stand-in for `/opt/IaCAgent` seeded from the old source with
`rsync -a --delete --exclude=.git`: a second pass **from the old source** itemizes nothing (today's
strict no-op); a `--dry-run` **from `support/iac-agent/`** itemizes `>f..t......` for all 13 files
and `.d..t......` for 7 directories — the `t` flag only, no content or size flag.

Consequence chain: V11's check-mode command reports the sync task `changed` (the handler is skipped —
`ansible.builtin.command` has no check mode), and a real apply re-transfers identical bytes and fires
`install.sh`, which `cmp -s`-compares each target, prints `install.sh: nothing to do.` and restarts
nothing (`support/iac-agent/install.sh:28-36,84-94`). Nothing on the host changes and the second
apply is clean — hence advisory. What it costs is the shape of the proof: PB's done-record says
"R6's parity apply has to be a strict no-op" and the plan says the run "should converge with the
host's materialized files untouched", so a `changed=2` comes back looking like a regression the
operator and the test phase must then reason out from scratch. Recorded in `plan.md` under PB's
"For later phases" so the test phase reads a timestamp-only itemization as parity rather than as a
V10 failure.

### 2. `tools/ai_workflow/send_message.py:6` cites a checkout the slice retires, and no phase in the queue owns the line · Minor · impact: advisory · confidence: high

The docstring reads "Copied from `/work/IaCAgent/bin/send_message.py`". After R6 that path is gone
from disk and the repo is archived, leaving the only provenance pointer for one of N4's held-out
duplicates aimed at nothing — while its twin now sits at `support/iac-agent/bin/send_message.py` in
the same repo. Correctly *not* fixed here: N4 pins all four duplicate-pair files to their current
content, and PC's charter is bounded to inside `support/iac-agent/`. But the doc phase's surfaces
(`docs/slice-doc-plan.md:9-45` — `decisions.md`, `docs/runbooks/`, the specs README, role/module
docs, `CLAUDE.md`) do not reach `tools/` either, so unless it is picked up deliberately the line
survives the slice pointing at a dead path. Flagged for disposition, not for this phase to fix.
