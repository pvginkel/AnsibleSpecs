# PC — code review r1

Branch `phase/013-PC`, `git diff 8eba51a..7461c61` (one commit, four files, prose and comments only).

## Readiness

The phase hits its stated bar. `grep modern-app-dev support/iac-agent/` returns nothing; every
factual claim the rewritten README makes checks out against the working tree — the five bind-mounts
(`bin/iac:63-69` vs `README.md:9`), the six `iac-controller` jobs (each file's `agent { label
'iac-controller' }`) with charters that match their own header comments, `iac-image`/`architecture`
correctly separated as `podTemplate` pod-agent jobs that touch none of the tree's helpers (verified
by grepping the helper names across `Jenkinsfile.*`), `check-protected-vms.sh` used by three jobs
(`iac-on-push:45`, `iac-apply:69`, `iac-scheduled-drift:64`), the dead
`Jenkinsfile.iac-dqlite-watchdog` dropped, and the corrected design link resolving to a file that
exists on `AnsibleSpecs` `origin/main` (`phases/completed/iac-agent.md`). No executable line moved:
the only non-comment edit is the `echo` text at `bin/iac:27`; N4's held-out duplicates
(`tools/ai_workflow/send_message.py`, both `daemon.json`s) are untouched, and the tree's other three
files are byte-identical to PB. One real problem is outside the commit but inside the phase's work:
the gate step's `py_compile` run left a build artifact in the tree the role rsyncs, which
falsifies the parity signal PB handed the operator. Everything else is advisory.

## Findings

### 1. Major — `py_compile` residue in the synced tree breaks the R6 parity signal · impact: blocking · confidence: high

`support/iac-agent/bin/__pycache__/send_message.cpython-313.pyc` sits in the working tree, written
`Aug 13 20:23` — the same minute as commit `7461c61` and the product of the phase's own verification
step (`plan.md:420-421`, "`python3 -m py_compile` on `send_message.py`"). It is invisible to
`git status`, because `support/iac-agent/.gitignore:1-2` ignores `__pycache__/` and `*.pyc`, so
nothing in the normal review surface shows it.

The role syncs the tree with `delete: true` and exactly one exclusion —
`ansible/roles/iac_agent/tasks/main.yml:88-95`, `rsync_opts: ["--exclude=.git"]` — from
`iac_agent_local_checkout` (`defaults/main.yml:7`), i.e. `/work/Ansible/support/iac-agent`. That is
the tree the operator-owed parity apply runs against (`plan.md:343-344`: `cd /work/Ansible/ansible
&& … playbooks/site.yml --limit iac_agent --check`).

Reproduced, HEAD's tracked tree standing in for `/opt/IaCAgent`:

```
$ git archive HEAD support/iac-agent | tar -x -C /tmp/sim-opt --strip-components=2
$ rsync -rin --delete --exclude=.git support/iac-agent/ /tmp/sim-opt/
>f..T...... .gitignore
… (13 tracked files, timestamp-only)
cd+++++++++ bin/__pycache__/
>f+++++++++ bin/__pycache__/send_message.cpython-313.pyc
```

PB's review-settled rule is explicit (`plan.md:353-354`): "Read a timestamp-only itemization as
parity; anything carrying a content or size flag is not." The extra entries are a brand-new
directory and file, so the operator's parity check — the proof R6/V10/V11 turn on — now reports a
genuine transfer, and a real apply drops a stale `.pyc` under `/opt/IaCAgent/bin/` on srviac, where
it will be re-synced from every workstation apply. Blast radius on the host is limited:
`install.sh:47-54` installs an explicit file list, so nothing is materialized into
`/usr/local/bin` and no service behaviour changes.

Nuance for the record: no committed byte is wrong, and the CI path is clean (`iac-impl` clones from
GitHub, where the file is gitignored and absent). The damage is confined to the operator's
workstation checkout — which is precisely where the slice's next owed step runs.

### 2. Minor — `iac-prune`'s new clause attributes a command `iac` does not run · impact: advisory · confidence: high

`etc/cron.d/iac-prune:4-5` now reads "Single-tag pulls (`docker pull registry:5000/iac:latest`,
which `iac` does on every call)". `bin/iac:40` never invokes `docker pull`; it passes `--pull=always`
to `docker run` (`docker_flags=("--rm" "--pull=always" "--quiet")`). The retag/untag effect the
comment explains is the same, so nothing downstream is wrong — but a reader who greps `bin/iac` for
the cited command finds nothing, in a file whose entire edit was made for accuracy.

### 3. Minor — two dead spec pointers survive, one in a file this commit edited · impact: advisory · confidence: high

`/work/AnsibleSpecs/phases/` now holds only `README.md` and `completed/`, so `bin/iac:4`
(`/work/AnsibleSpecs/phases/iac-agent.md`) and `bin/iac-impl:6`
(`/work/AnsibleSpecs/phases/openbao.md`) both point at nothing. The commit fixes the identical
staleness in `README.md:3` (`phases/` → `phases/completed/`) and edits `bin/iac` in the same breath
without touching line 4, so the tree's self-description is now internally inconsistent about the
same target. `plan.md:414-417` records this as deliberately carded rather than fixed; recorded here
once so the disposition is visible, not as a demand.

### 4. Minor — the new `bin/iac` error path is srviac-only · impact: advisory · confidence: medium

`bin/iac:27` now says "run `/opt/IaCAgent/install.sh`". That path exists only on hosts the
`iac_agent` role syncs — `iac_agent_install_dir` (`defaults/main.yml:10`), and `ansible/playbooks/
site.yml:32-41` applies the role to the `iac_agent` group only. `README.md:63-65` documents a
supported second context ("The same `install.sh` runs on `wrkdev` if you want `iac` parity there"),
where the installer is run out of a checkout and `/opt/IaCAgent` need not exist; an operator hitting
the error there is pointed at a path that isn't on their disk. The replaced text ("run IaCAgent's
install.sh") was location-agnostic. No product consequence — the message is a hint, not a code path.
