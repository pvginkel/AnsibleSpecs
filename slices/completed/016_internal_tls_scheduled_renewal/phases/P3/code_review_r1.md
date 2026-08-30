# P3 code review — round 1

Range: `3b971a5d71ba668b811777b9da07c6665b686e78..1f7c7ec9edc1` (branch `phase/016-P3`),
one commit, one file: `Jenkinsfile.iac-scheduled-certs` (+101/-19).

## Readiness

**Ready to merge.** The phase's outcome holds: `iac-scheduled-certs` now runs four stages on the
one Friday cron (`Jenkinsfile.iac-scheduled-certs:62`) — host certs prd, host certs dev, TLS leaves
prd, TLS leaves dev — and the two leaf stages drive `playbooks/renew-internal-tls.yml` on exactly
the two scopes P2 verified cut cleanly (`:150` `--limit "!k8s_dev"`, `:183` `--limit k8s_dev`),
so R1's "no hand-started `iac-apply` in the loop" is closed. The host-cert stages are renamed only
(`:75`, `:102`) and still run first with their playbook, scopes, 10m dev bound and `devUp()`
handling intact; nothing outside this Jenkinsfile changed, so V14's "no regression" surface is
untouched by construction. The dev convention the ruling names is reproduced faithfully on the new
stage (`:173-176` skip → UNSTABLE, `:187-190` genuine failure → UNSTABLE + flag), and the
no-`timeout` decision on the prd leaf stage is correct and correctly argued: 3 × 180s of
`microk8s_kubelite_ready_timeout` (`ansible/roles/microk8s/defaults/main.yml:249`) genuinely
exceeds the 10m the dev stage above it uses, and the prd host-cert stage has always carried no
bound either. I checked the file's brace and paren balance mechanically (0/0) since no Groovy
parser exists in this environment; stage-level `post` after `steps` with a `script` wrapper around
the `currentBuild.description` assignment is valid declarative, and `Failure`'s stage-level
condition does not fire on a build merely already UNSTABLE (`Result.UNSTABLE` is not
`worseOrEqualTo(FAILURE)`), so the dev host-cert stage yellowing the build cannot spuriously write
the leaf stage's description.

Three things I stressed and found sound: the description split is truthful in both directions — a
red `Host certs (excl. k8s dev)` really does abort before either leaf stage, which is what `:88`
claims, and `:157` is written for the only other stage that can red the build; the `--limit
"!k8s_dev"` quoting is byte-for-byte the idiom the working host-cert stage already uses through
`iac -c`, so no new shell-quoting exposure; and the header's "Both playbooks are a no-op outside
that window … a fast changed=0" (`:21-23`) survives inspection of the renewal path — the only
`changed_when: true` tasks on it are inside the issuance block
(`ansible/roles/internal_tls/tasks/issue.yml:88`, `:178`), and microk8s's SNI `lineinfile`
(`ansible/roles/microk8s/tasks/internal_tls.yml:49-54`) is a re-assert.

The largest residual risk in this arrangement — a red SSH host-cert stage costing all ten leaves
their weekly renewal, because declarative fails fast — is real and probable in a homelab where any
one unreachable host reds `renew-host-certs.yml`. It is already recorded by the executor as
close-out **S4** with its remedy and the reason P3's constraints ruled it out, and the description
at `:88` makes it visible to the operator when it happens, so I have not re-filed it; merging is
strictly better than the status quo, where the leaves are never renewed at all. Both findings below
are advisory: neither harms the product on merge.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**A dev-stage failure loses its Telegram warning when a later prd stage then reds the build.**

`notify.warning` is not a delivery path of its own: it echoes a `[raisealert|type=warning]` marker
into the build log (`/work/JenkinsPipelineUtils/vars/notify.groovy:46-48`), and the only place this
job echoes it is inside `post { unstable }` (`Jenkinsfile.iac-scheduled-certs:205-217`). Jenkins
runs that handler only when the build's final result is UNSTABLE. Before this diff the dev
host-cert stage was the last stage in the job, so nothing could downgrade an UNSTABLE build to
FAILURE after the flag was set and the page was structurally guaranteed. The diff puts prd work
after a dev stage for the first time: `Host certs (k8s dev)` at `:102-125` sets
`env.DEV_STAGE_FAILED` and yellows the build, and `TLS leaves (excl. k8s dev)` at `:144-161` can
red it afterwards.

Failure scenario: srvk8sdev is powered on; its host-cert renewal exits non-zero → `:120-121` sets
the flag and the build goes UNSTABLE; the prd leaf run then fails because, say, `pve2` is
unreachable → build FAILURE. `post { unstable }` does not run, no marker reaches the log, and the
operator gets one Telegram message — the bot's own FAILURE report carrying `internal_tls leaves may
lapse` — with no push-side hint that dev host certs also failed. The distinction V07 asks for
(genuinely-failed dev vs. merely-powered-off dev) survives only in the build log.

Why advisory: the build is red and the bot reports FAILURE loudly by itself, so the operator is
still pushed — louder than the warning that was lost — and the dev attribution is one click away in
the stage's own `unstable()` message. The same shape already exists in
`Jenkinsfile.iac-scheduled-drift`, whose dev k8s stage at `:119-142` precedes two prd stages at
`:144-161` and `:195-229`, so this is the repo's standing flag idiom rather than a hazard class this
diff invents.

### F2 — Minor · advisory · anchor: none · confidence: medium

**A red build whose failure is not in one of the two prd stages now carries no description at all.**

The job-level `post { failure }` that unconditionally set `currentBuild.description = 'host certs
may lapse'` is removed (`Jenkinsfile.iac-scheduled-certs:196-204`; base commit `:113-124`), and the
description is now written only from two stage-scoped handlers, `:85-91` and `:154-160`. Anything
that reds the build outside those two stages therefore leaves the description null.

Failure scenario: the `library identifier: 'JenkinsPipelineUtils'` step at `:34` fails, or the
`iac-controller` agent is not allocatable, or SCM checkout of the Jenkinsfile fails. The build is
FAILURE, no stage `post` ran, and the bot's message — which per the comment at `:197-200` appends
what a red build of this job costs, taken from the description — carries no cost line where before
it read `host certs may lapse`.

Why advisory: the message still names the job and links the build, and a blanket
`host certs may lapse` on an agent-allocation failure was itself a claim the job had not earned, so
this is a thinner alert rather than a wrong one. Worth knowing that the catch-all is gone before
the next stage is added to this job.
