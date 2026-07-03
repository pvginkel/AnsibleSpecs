# Secrets remediation — rotate, relocate, purge history, automate rotation

**One line:** Rotate and relocate every secret the 2026-07 review found outside the tiered
design, purge TerraformState's pre-encryption git history, fix the two credential-exposure
leak paths in IaCAgent, and then build script-automated rotation for everything rotatable.

Triage source: 2026-07 IaC review C2 + I2/I3 + R4 (`../../reviews/2026-07-iac-review/
findings.md`), operator dispositions in chat 2026-07-03. Operator: "I know I need to
rotate all my secrets… I agree with everything in here."

## Committed/exposed secrets to rotate + relocate (review C2, verified)

- **step-ca root of trust** — `HelmCharts/configs/prd/step-ca/prd/manifests.yaml` commits
  `step-ca-secrets` (encrypted intermediate CA + SSH host CA private keys) **and**
  `step-ca-ca-password` + `step-ca-ssh-host-ca-password` — the passwords that decrypt
  them — as k8s Secrets in the same file. Encryption thereby moot; recoverable from every
  clone and the unauthenticated LAN git mirror. The fix shape already exists in doctrine
  (`decisions.md:143`): materialise at cluster bring-up via a small Ansible role from
  ansible-vault'd sources; only `step-ca-certs` (public) stays. This was a
  runtime-secrets-sweep loose end that never landed although the slice closed.
  Relocation is the minimum; re-keying the CA itself is larger — at minimum the passwords
  must leave git and rotate.
- `HelmCharts/configs/prd/newsfilter/prd/manifests.yaml:9-12` — two user passwords in
  `stringData` → behind `shared.externalsecrets` (ESO + OpenBao).
- `HelmCharts/configs/prd/elasticsearch/prd/values.yaml:8` — plaintext password (mirrored
  in a dev values file) → ESO.
- `HelmCharts/configs/dev/git-sync/prd/values.yaml:11` — live GitHub PAT
  (`gitSync.gitHubToken`) → revoke + OpenBao.
- `HelmCharts/configs/dev/homeassistant-mcp/prd/values.yaml:10` — Home Assistant JWT →
  rotate + OpenBao.
- `Ansible/terraform/prd/terraform.tfvars` (gitignored, workstation) — Proxmox root
  password + two bearer tokens; read during the review; rotate on principle (operator
  acknowledged; also noted these were read before).

## History + residue (review R4, operator-confirmed additions)

- **TerraformState: delete the git history from before encryption.** Operator explicitly
  wants the history purge *in addition to* rotation (pre-encryption commits contain
  plaintext state incl. per-VM host private keys and Proxmox credentials; encryption
  landed at commit `62a68b9`).
- **Exclude TerraformState from the LAN git mirror** — standing TODO at
  `decisions.md:131` (the daily sync exposes all repos unauthenticated on the LAN).
- **Fleet SSH private keys out of `/work/Obsidian/Attachments/`** (plus legacy plaintext
  cephx/S3/swarm credentials in old notes).
- **Execute the KubernetesConfig repo deletion** — marked for deletion ("it holds
  secrets") since the runtime-secrets-sweep; still exists.

## Credential-exposure leak paths (review I2/I3, IaCAgent)

- **I2:** `iac-impl` embeds the GitHub PAT in the clone URL (`bin/iac-impl:383`); an
  uncaught `CalledProcessError` on clone failure prints full argv — token included — into
  the Jenkins build log; the token also persists in each clone's `.git/config` for the
  container's lifetime. Fix shape: `GIT_ASKPASS` helper (or wrap + scrub).
- **I3:** Jenkins agent secret passed as argv (`jenkins-agent-launch.sh:76`) — visible in
  `ps`/`docker inspect` for the container's lifetime; the inbound agent supports
  `-secret @file`. The format-validation error path also echoes the rejected value into
  the journal.

## Automated rotation (the systemic half — operator's ask)

"My strong preference is to do this automatically. I.e. fully script automated secret
rotation (except for user passwords of course, and other very problematic keys). Anything
that can't be rotated automatically maybe becomes a message in the Telegram bot with
instructions on what to do?"

- Build scripted rotation for the rotatable set (AppRole secret_ids, app secrets in
  OpenBao KV, TF-minted per-app credentials, tokens). The four rotation patterns are
  already catalogued in `decisions.md` §"Secret rotation — TODO codify" (AppRole-in-KV /
  AppRole-in-consumer-UI / hand-staged k8s Secret / plain KV app secrets) — that TODO is
  absorbed by this bundle.
- Non-rotatable or human-gated secrets (user passwords, CA keys, seal key, vault
  passphrase) → scheduled instruction messages via the Telegram IaC bot
  (`../telegram_iac_bot/` dependency), replacing the never-looked-at rotation-dashboard
  pattern.
- Rotation cadence policy itself is uncodified (decisions.md TODO) — deciding it belongs
  to this work.

## Notes for the slice writer

- Rotation-first makes the HelmCharts history question optional, but the operator wants
  the TerraformState purge regardless; HelmCharts history scrubbing remains optional
  after rotation.
- Cross-repo: HelmCharts (configs), Ansible (step-ca materialisation role, vault files),
  IaCAgent (I2/I3), TerraformState (history), Obsidian (manual), GitHub (KubernetesConfig
  archive/delete, mirror exclusion). Ansible-led.
- Likely splits into (a) the immediate rotate+relocate sweep, (b) the history/residue
  purge, (c) the automated-rotation system — slice writer's call.
