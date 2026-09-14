# Straightforward changes from triage, 2026-09-14

**Cards covered:** #667 (documentation half), #506, #635, and slice 016's close-out entries B1, B4, S3,
S5 plus the dash finding in the close-out card's comment. Tracked on Operator Actions by #994.

**What this is.** Triage on 2026-09-14 sorted these out of the slice route at the operator's request:
"If there are a number of cards that are trivial changes, like adding the secret, or maybe small
rewriting of a decision, feel free to bundle these into a handover document and I'll run through all
of them in a single conversation. Clear obvious fix, low risk, not test suites required (although of
course the agent can run the suites when done)."

**How to work it.** One conversation with the operator, item by item; the items are independent. Each
states what its source says, verbatim where it matters, and what done looks like. Line numbers are the
sources' and may have drifted — find the text. Read the code before you edit; if an item turns out not
to be a clear, low-risk fix, stop and say so rather than designing it here. Run `kc project lint` and
`kc project test` in each repo you touched. Operator keystrokes stay the operator's: every
`ansible-playbook` against real hosts, every `bao` write. Commit in each repo; push only when the
operator says so.

**Before you start — environment restart owed.** Ansible `7b7b4ef` projects the `jenkins-token`
catalog secret as `JENKINS_TOKEN` in `.kubecoder/config.yaml`, for `tools/ai_workflow/track_build.py`
(signs in as `$JENKINS_USER`, default `admin`). It takes effect on `kc env restart`, which recreates
the pod and ends every session in it — so the operator runs it before this conversation, not during.
`kc env restart --help` says the controller "re-reads .kubecoder/config.yaml"; if that is the pushed
copy, `7b7b4ef` needs pushing first. After the restart, `printenv JENKINS_TOKEN >/dev/null && echo set`
confirms it without printing the value.

---

## 1. #667 + 016-B1 — make `decisions.md`'s Internal TLS section honest

**File:** `/work/AnsibleSpecs/decisions.md`, section "Internal TLS / homelab CA". Also any other doc
that presents step-ca's per-provisioner name lists as enforced — grep the Ansible docs and
AnsibleSpecs for `allowedSANs`, `allow.dns` and `ansible-jwk`.

**The operator's ruling on #667, verbatim:** "I don't feel like fixing this. It's a known gap. I have
bigger ones. I would like the following. Document that we should have these controls, but that
they're not in place. Make the documentation honest. Then file a card in the Later list (a clean card)
to implement the controls." That card is **#993** (Later); this item is the documentation half only.

**What #667 found** (the card's claims): step-ca 0.30.2 ignores per-provisioner name policy in a
file-based `ca.json` — "AllowedNames/DeniedNames/AllowWildcardNames carry `json:"-"`
(authority/provisioner/options.go:89-97), filled only via the remote-management API this estate does
not use" — so "ansible-jwk's committed options.x509.allow.dns list is dead configuration". Confirmed
live: "OpenBao's listener cert, issued through ansible-jwk, holds DNS:secrets.home and
DNS:srvvault1.home, neither on the list". `kubecoder-jwk` is configured the same way and is inert too.

**Two sentences the card's comments name** (2026-08-22):

- The mechanism sentence is wrong whichever way #667 lands. It reads: *"Scoping comes from the
  provisioner's `allowedSANs` regex (`*.home` plus the kube-apiserver internal names) rather than
  per-consumer credentials."* What is deployed has no `allowedSANs` and no regex — "it carries
  `options.x509.allow.dns` with 21 **exact** names (`pve`, `pve.home`, `pve1`, `pve2` and their `.home`
  forms, `srvceph1..3`, the `kubernetes*` and `kubernetes-api*` names) plus `allow.ip` with three
  addresses".
- 016-B1: the metric sentence says each leaf's expiry "is published as the Prometheus gauge
  `internal_tls_cert_not_after_seconds` — written by the `internal_tls` role to a node-exporter
  textfile collector for VM consumers, and by an equivalent in-cluster collector for the certbot path".
  The kube-apiserver SNI leaves (srvk8s1, srvk8s2, srvk8s3, srvk8sdev) get no gauge: "`roles/internal_tls/tasks/metric.yml:23-32`
  skips the textfile write when the node-exporter textfile directory is absent", which is the steady
  state on k8s nodes, and the in-cluster collector is deferred. "no alert exists on any leaf".

**Done when:** the section says the per-provisioner name controls are wanted and not in place (naming
#993), no longer claims an `allowedSANs` regex, and scopes the gauge to the leaves that actually get
one (the Proxmox and OpenBao leaves). No other doc still presents the name lists as a control. Match the
file's existing voice; this is a correction, not a new decision entry.

## 2. 016-S5 — the deferred monitoring design's stale urgency argument

**File:** `/work/AnsibleSpecs/slices/deferred/internal-tls-monitoring.md` (the entry cites `:10-17`).

**The entry:** the design says that until the gauge and alert land, "no expiry alert fires — a silent
renewer failure would surface only when a leaf actually expires", acceptable given "47-day leaves, a
working renewer, and a small fleet". "Both premises moved: the renewer now has a schedule rather than
depending on someone starting an apply, and a red or unstable iac-scheduled-certs is a detector for a
renewal that stopped happening — one that reaches the operator by Telegram, ahead of any leaf
expiring." What stays true: "the four kube-apiserver leaves emit no gauge at all (close-out B1), and
the certs job only detects a renewal that fails loudly, not one that silently stops covering a host."

**Done when:** the risk argument no longer rests on "no detector exists", credits the scheduled certs
job for renewals that fail loudly, and still names the remaining gap — no gauge on the kube-apiserver
leaves, no alert on any leaf.

## 3. 016-B4 — `ansible/playbooks/README.md` catalogue omissions

**File:** `/work/Ansible/ansible/playbooks/README.md`.

**The entry:** the certificate playbooks were added in slice 016's doc phase; "The catalogue's other
pre-existing omissions — site-openbao.yml, site-ceph.yml, refresh-calico-token.yml — are untouched".

**Done when:** those three are catalogued, and any other playbook in `ansible/playbooks/` the list
still lacks, in the README's existing entry style.

## 4. Close-out card comment — bash `[[ ]]` under dash in two Jenkinsfiles

**Files:** `/work/Ansible/Jenkinsfile.iac-scheduled-drift` (`:61,63`), `/work/Ansible/Jenkinsfile.iac-on-push` (`:43`).

**The finding, verbatim** (card #750 comment, 2026-08-30): **Separate, pre-existing, not this slice's doing** (#85 has it too, and neither file was touched by 016): `Jenkinsfile.iac-scheduled-drift:61,63` and `Jenkinsfile.iac-on-push:43` use bash `[[ ]]` inside `iac -c`, which runs under dash — the log shows `sh: 7: [[: not found` / `sh: 9: [[: not found`. In the drift job a real terraform rc=2 falls through both tests to `else exit $rc`, so the build still reds, but the `DRIFT: terraform plan proposes changes against prd` message and the `check-protected-vms.sh` call never run. Worth its own card.

**Done when:** those tests are POSIX (they run under `sh`/dash inside `iac -c`), and nothing else in
the repo's Jenkinsfiles uses `[[` inside `iac -c`. Before editing `Jenkinsfile.iac-on-push:43`, read
what its test guards and tell the operator what starts running once it works — in the drift job it is
the `DRIFT:` message and `check-protected-vms.sh`, which can turn a build red that used to fall through.
Jenkins cannot be exercised from the pod; the proof is the next build's log no longer showing
`[[: not found` (with `track_build.py` once `JENKINS_TOKEN` is live). Slice 017 also edits the drift
job (#127's "drop `|| true` in drift job"); this fix does not wait for it.

## 5. 016-S3 — `throttle: 1` on `Restart openbao`

**File:** `/work/Ansible/ansible/roles/openbao/handlers/main.yml`; doctrine in `/work/AnsibleSpecs/decisions.md`.

**The entry:** "`roles/openbao/handlers/main.yml:23` puts throttle: 1 on Reload openbao and its comment
states the doctrine: the limit belongs with the reload 'rather than restated on each caller'. Restart
openbao at :8-11 — a full service restart, strictly more disruptive to the Raft peers than a SIGHUP —
is left relying on playbooks/site-openbao.yml:171's serial being arranged by whatever drives it. It is
notified from config.yml and hardening.yml." Consequence today: nothing; it "becomes real the first
time a driver enters the openbao role at an entry point touching config or the hardening drop-in
without arranging serial itself — all three peers would restart at once."

**Done when:** `Restart openbao` carries `throttle: 1`, and `decisions.md`'s "Cluster changes are
serialized" bullet — which today names "`throttle: 1` on the `Restart microk8s kubelite` and `Reload
openbao` handlers" — names it too. No rollout keystroke: it changes nothing until the next converge that
notifies the handler.

## 6. #506 — remove the `/var/lock/iac.lock` flock

**Card, verbatim:**

- URL: https://trello.com/c/yzCrLvTB
- List: Inbox
- Labels: Ansible, Minor
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:32:26 AM

##### Description

The flock existed because `iac-impl` cloned TerraformState and did sync_state_in/out with no remote lock (decisions.md:503). That's gone — `terraform-backend-git` takes `locks/<state-path>` branches, wired via lock_address/unlock_address in both backend.tf. As a state guard the flock is also illusory: wrkdev and the KubeCoder pod write the same store and it sees neither.

Cross-job serialisation, its other job, is already covered — the `IaC Agent` node is set to 1 executor, and it queues instead of failing.

Why it actively hurts:
- `flock -w 60` fails rather than queues; a collision becomes a red build.
- Post-block `iac -c 'send_message.py …'` takes the same lock, so a build failing on contention can't page.
- Global: HelmCharts takes it once per release (~55 `iac -c` calls); Argo PreSync hooks would contend dev-vs-prd and fail at 60s, with `-w 60` hardcoded in the shim (argo-cd/qa.md:704, review-fable.md R1). Likely blocker for Argo CD.

Accepted loss: hand-run Ansible on srviac no longer interlocks with a running job (terraform still does, via lock branches).

Scope: `IaCAgent/bin/iac` + README; decisions.md 130/503; docs/runbooks/iac-agent.md 11/41/51/120; Jenkinsfile header comments (on-push, certs, calico) + HelmCharts Jenkinsfile; argo-cd plan.md/qa.md.

##### Comments (in the order the tool returned them)

###### Jeeves — 8/17/2026, 7:32:26 AM

Triage research, 2026-08-16 — the flock is still there and unchanged. `support/iac-agent/bin/iac:45-55` takes `/var/lock/iac.lock` on fd 9 with `flock -w 60 -x`, and exits 1 on timeout rather than queueing; the header comment at :10-11 restates the same. Nothing else in `support/iac-agent/` takes it — `bin/jenkins-agent-launch.sh:49,67` only bind-mounts `/var/lock` into the agent container so the host lock is visible across the boundary.

One of the card's three "why it actively hurts" bullets is now moot: `send_message.py` is gone (Ansible 7cdc788 / 123f0f2), so the post-block paging path no longer takes the lock. `install.sh:54-64` sweeps the stale on-host copy.

The card's scope list also predates the fold-in — `IaCAgent/bin/iac` is now `support/iac-agent/bin/iac`.

Triaged 2026-08-16: Minor. Operator ruling: "Agreed."

**Mentions found at triage** (`grep iac.lock`, 2026-09-14): `support/iac-agent/bin/iac`,
`support/iac-agent/README.md`, `docs/runbooks/iac-agent.md`, `Jenkinsfile.iac-scheduled-certs`,
`Jenkinsfile.iac-scheduled-calico`, `/work/AnsibleSpecs/decisions.md`. The card's `argo-cd plan.md/qa.md`
now live under `AnsibleSpecs/argo-cd/archive/` — leave archived documents alone. Also grep
`/work/HelmCharts` (the card cites its Jenkinsfile).

**One open point for the operator:** `bin/jenkins-agent-launch.sh:49,67` bind-mounts `/var/lock` into
the agent container only so the host lock is visible (triage research, 2026-08-16). Ask whether that
mount goes too; the card does not say.

**Done when:** the shim takes no lock, no live doc or comment describes one, the accepted loss is stated
where the lock used to be documented ("hand-run Ansible on srviac no longer interlocks with a running
job (terraform still does, via lock branches)"), and `grep -r iac.lock` finds only archived documents.
**Rollout:** srviac gets the new shim from the `iac_agent` role's converge — the operator's keystroke.

## 7. #635 — retire `HA_URL` / `HA_TOKEN` from the IaC agent — in order, with operator stops

**Card, verbatim:**

- URL: https://trello.com/c/ZpUz4EYx
- List: Inbox
- Labels: Ansible, Improvement
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:34:22 AM

##### Description

send_message.py is gone (Ansible 7cdc788): the IaC pipelines now report through jenkins-telegram-bot and raise the rest via JenkinsPipelineUtils' notify var. It was the only consumer of HA_URL and HA_TOKEN, which are still wired up.

Left out of that commit because retiring them touches four places plus a live host:

- `support/iac-agent/etc/iac/secrets.example.yaml` — the `HA_URL` literal and the `HA_TOKEN` `!bao kv/iac/homeassistant#token` ref
- `ansible/inventories/prd/group_vars/openbao.yml` — the `kv/iac/homeassistant` grant in `openbao_iac_agent_kv_paths`
- `docs/runbooks/iac-cold-boot.md` — its `HA_TOKEN` step
- the OpenBao leaf itself, and srviac's live `/etc/iac/secrets.yaml`

Order matters: dropping the grant while a `!bao` ref survives hard-fails iac-impl at next container start. Remove the refs and converge first, then the grant and the leaf.

The token is minted distinct from the homeassistant-mcp chart's (decisions.md, per-consumer named accounts), so nothing else loses access.

##### Comments (in the order the tool returned them)

###### Jeeves — 8/17/2026, 7:34:22 AM

Triaged 2026-08-16: Improvement — "It was the only consumer of HA_URL and HA_TOKEN, which are still wired up."

Operator ruling: "Agreed."

Kept out of the straightforward-changes document deliberately: the card states an ordering constraint with a live consequence — "dropping the grant while a `!bao` ref survives hard-fails iac-impl at next container start" — and the work touches the OpenBao leaf and srviac's live `/etc/iac/secrets.yaml` as well as the repo. The sequencing is part of the ask, so this wants a slice rather than an ad-hoc edit.

**Note on the comment above:** it records the 2026-08-16 view that this card "wants a slice rather than an
ad-hoc edit". The operator routed it here on 2026-09-14; the ordering it rightly insists on is why this
item stops for the operator between steps.

**The order, as the card rules it** ("Remove the refs and converge first, then the grant and the leaf"):

1. Remove the `HA_URL` literal and the `HA_TOKEN` `!bao kv/iac/homeassistant#token` ref from
   `support/iac-agent/etc/iac/secrets.example.yaml`, and the `HA_TOKEN` step from
   `docs/runbooks/iac-cold-boot.md`. Commit. **Stop:** the operator brings srviac's live
   `/etc/iac/secrets.yaml` in line (converge, or by hand — ask which applies) and confirms iac-impl
   still starts.
2. Remove `kv/iac/homeassistant` from `openbao_iac_agent_kv_paths` in
   `ansible/inventories/prd/group_vars/openbao.yml`. Commit. **Stop:** the operator converges the
   policy change.
3. **Operator:** delete the OpenBao leaf `kv/iac/homeassistant`.

**Done when:** no `HA_URL` / `HA_TOKEN` / `kv/iac/homeassistant` remains in the repo, and the operator
has confirmed steps 1–3 live.

---

## When the work is done

Commit in each repo you touched (`AnsibleSpecs` for items 1 and 2 and the doctrine lines of 5 and 6;
`Ansible` for 3–7), staged by name.
Pushes are the operator's call. Then archive Operator Actions card #994, which tracks this document, with a
comment naming the commits, and delete this file in its own AnsibleSpecs commit. The source cards —
#667, #506, #635 and the close-out card #750 — were archived at triage with a pointer here; nothing on
the board needs closing besides the tracking card.
