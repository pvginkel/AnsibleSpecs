# 08 — IaC agent secrets resolver: `!bao` refs via OpenBao AppRole

## Goal

Rewrite `pvginkel/IaCAgent`'s `bin/iac-impl` from bash to Python and
extend `/etc/iac/secrets.yaml` to support `!bao` references that resolve
at container startup against OpenBao. Pulls the
runtime-secrets-from-OpenBao pattern into a single bootstrap point — the
IaC container — without changing what downstream consumers see: Ansible,
Terraform, the Jenkins agent launcher, and `send_message.py` still read
their inputs from environment variables and files on disk, exactly as
today.

This slice ships in Phase 3 *after* OpenBao itself is up (the equivalent
of Trello cards 6–10) and *before* the runtime-secrets sweep (Trello
card 11 onwards). It is the gate that turns OpenBao into a usable
secrets source for the IaC agent.

## Decisions

- **Full Python rewrite of `iac-impl`.** Bash was fine while secrets
  parsing was 30 lines of `yq`. AppRole login, ref resolution, retry +
  error handling, and clean diagnostics on miss push the script past
  the point where Python is plainly cleaner. The clone / state-sync /
  exec / state-sync-back surface moves over alongside; one language,
  one entry point. *(Superseded: state-sync was later replaced by the
  `terraform-backend-git` http backend; `iac-impl` no longer syncs
  state.)*
- **`!bao` as a YAML custom tag.** Schema: `!bao
  <mount>/<path>#<key>`, e.g. `!bao kv/iac/git-api-token#token`. Parsed
  via a custom YAML constructor so typos can't accidentally fall through
  as literal strings (a `bao://...` string lookalike would).
- **AppRole, not a long-lived bearer token.** The IaC container's
  OpenBao identity is an AppRole; `role_id` + `secret_id` live in
  `secrets.yaml` as literals (part of the irreducible-literal set).
  Rotation is an operator procedure: generate a new secret-id in
  OpenBao, paste into srviac's `secrets.yaml`, restart.
- **Least-privilege policy.** The `iac-agent` AppRole's OpenBao policy
  grants `read` only on the KV paths referenced by `secrets.yaml`.
  Adding a new ref is a two-step change: edit the file *and* extend the
  policy. Mismatches surface as hard-fail at next container start.
- **Hard-fail on miss.** Unresolvable ref, AppRole rejection, or
  network failure terminates `iac-impl` before any clone / state sync /
  user command runs. The container is short-lived per `iac` invocation;
  running with stale or missing values is unsafe. No fallback, no
  warn-and-continue.
- **Cold-boot via literal substitution.** Operator pulls each ref's
  value from Roboform, replaces `!bao <path>` with the literal in
  `secrets.yaml`, runs the IaC container until the fleet + OpenBao are
  back, then flips refs back. Documented as a runbook.
- **Python deps land in the Ansible repo's `pyproject.toml`.** The iac
  image bakes `/app/.venv` from `pvginkel/Ansible`'s `pyproject.toml` +
  `poetry.lock` at image-build time (per existing `iac-impl` rebuild-
  warning logic). Any dep the resolver needs — `hvac` plus the YAML
  library already in use — goes into Ansible's Poetry config. The
  `iac-impl` source itself stays in `pvginkel/IaCAgent`.

## Steps

### A. Python deps in the Ansible repo

`poetry add hvac` in `/work/Ansible`. Run `poetry lock`. Commit
`pyproject.toml` + `poetry.lock` together. The next iac image rebuild
picks the dep up automatically; until then, `iac-impl`'s existing
"poetry.lock differs from baked /app/poetry.lock" warning fires
expectedly.

### B. OpenBao policy + AppRole + role provisioning

In the `openbao` role (which itself lands earlier in Phase 3), add a
post-init task block:

- Enable the `approle` auth method if not already enabled.
- Write a policy named `iac-agent` granting `read` on the KV paths
  `secrets.yaml` references. Derive the path list from the rendered
  `secrets.yaml.example` (or a static list maintained alongside the
  policy); do not grant `kv/*` blanket access.
- Write an AppRole named `iac-agent` bound to that policy. Token TTL
  short (1 h is generous for a single `iac` invocation); explicit
  `token_no_default_policy = true`, `token_max_ttl = 1h`, no renewal.
- At apply time, print the `role_id` once and generate a one-shot
  `secret_id`, surfaced for the operator to paste into srviac's
  `/etc/iac/secrets.yaml`. Re-runs of the role do not rotate
  automatically — rotation is the operator's call.

### C. Rewrite `iac-impl` in Python

Single Python entry point in `pvginkel/IaCAgent/bin/iac-impl`. Same
behaviour surface as today plus the resolver:

- **Flags**: `-v / --verbose`, `-c <script>`, no-arg interactive bash.
- **Env overrides**: `SECRETS_FILE` (default `/etc/iac/secrets.yaml`),
  `WORK` (default `/work`).
- **Hard-fail conditions**: missing secrets file; `files` entry without
  `mode`; missing `GIT_API_TOKEN` after resolution; OpenBao auth
  failure; any `!bao` ref that does not resolve.
- **YAML constructor** for `!bao` returns a sentinel carrying
  `(mount, path, key)`. After full parse, walk the tree and replace
  sentinels.
- **Two-pass resolve**: first pass reads literal `env:` entries to
  obtain `OPENBAO_URL`, `OPENBAO_ROLE_ID`, `OPENBAO_SECRET_ID`. AppRole
  login produces a short-lived token kept only in memory. Second pass
  resolves every `!bao` sentinel against OpenBao.
- **Materialisation**: env entries → `os.environ` for the eventual
  subprocess; files entries → `install -D -m <mode>` semantics
  (parents created, mode set after write so writes through 0600 files
  go through under root).
- **Sub-process exec**: `bash` for the no-arg case, `sh -c <script>`
  for the `-c` form. Inherits the resolved environment. Same exit-code
  propagation as today.
- **State sync**: unchanged — clone `Ansible` + `TerraformState`, copy
  state in, run user command, copy state out, commit + push.
  *(Superseded: replaced by the `terraform-backend-git` http backend —
  clone only `Ansible`, state flows through the backend; see
  `docs/runbooks/iac-agent.md`.)*

### D. `secrets.example.yaml` rewrite

Update `pvginkel/IaCAgent/etc/iac/secrets.example.yaml`:

- Required literal `env:` entries: `OPENBAO_URL`, `OPENBAO_ROLE_ID`,
  `OPENBAO_SECRET_ID`, `GIT_API_TOKEN`. Comment each as part of the
  "irreducible literal set" — never moves to OpenBao.
- Every other secret as a `!bao` ref with a comment showing the
  intended KV path.
- One `files:` entry example using `content: !bao …` (the ed25519
  Ansible SSH key is the natural candidate).

### E. Cold-boot runbook

`/work/Ansible/docs/runbooks/iac-cold-boot.md` (the runbook lives in
the Ansible repo so it sits alongside the wife runbook and the
step-ca-bootstrap runbook):

- **When to use**: OpenBao is not yet up, or recovery from a whole-
  cluster loss before OpenBao is restored.
- **Procedure**: Roboform inventory of refs to look up; produce a fully-
  literal `secrets.yaml`; run `iac`; bring the fleet + OpenBao back;
  re-encrypt the OpenBao seal key arrival; restore refs; restart the
  IaC container.
- Cross-links from the wife runbook so the operator (or their proxy)
  can find it without prior context.

## Verification

- **Steady state**: `iac` against a refs-heavy `secrets.yaml` starts,
  resolves every ref against OpenBao, and runs `terraform plan` end-to-
  end with no visible behaviour difference from the literal-only era.
  Time-to-ready should be ≲ 2 s longer than today (single OpenBao
  round-trip per ref, batched if `hvac` permits).
- **Missing-ref hard-fail**: introduce a typo in a `!bao` path; run
  `iac`; expect a non-zero exit *before* the clone step with a clear
  diagnostic naming the bad ref.
- **OpenBao-down hard-fail**: stop OpenBao; run `iac`; expect non-zero
  exit at AppRole login with a network error.
- **Override behaviour**: replace one `!bao` ref with a literal of the
  same key; run `iac`; the literal value wins (no OpenBao call for
  that key).
- **AppRole rotation**: in OpenBao, generate a fresh `secret_id`; verify
  the running iac config keeps working until next container restart;
  verify next start fails fast; paste new `secret_id`; verify recovery.

## Caveats

- **OpenBao becomes a hard runtime dependency of `iac`.** Pre-rewrite,
  `iac` ran as long as `secrets.yaml` was materialised. Post-rewrite,
  every `iac` invocation makes an OpenBao round trip before doing
  anything. Mitigated by hard-fail clarity and the cold-boot runbook —
  but worth flagging because it changes the failure surface of every
  automation that calls `iac` (Jenkins post-stages, ad-hoc operator
  runs, scheduled drift).
- **The irreducible literal set is the new bootstrap-tier secret
  inventory**: `OPENBAO_ROLE_ID`, `OPENBAO_SECRET_ID`, `GIT_API_TOKEN`,
  plus the JWK provisioner password handled by the step-ca slice.
  These never move into OpenBao — they gate the path that fetches
  every other secret. Captured in decisions.md alongside the seal key
  and ansible-vault passphrase.
- **Card #11 ("Auth + policies + audit + hardening") shrinks.**
  Ansible-via-iac-impl does not need its own AppRole — it consumes the
  env + files materialised by `iac-impl` before it ever runs. Jenkins
  (for pipeline secrets) and ESO (for in-cluster secret sync) still
  need their own AppRoles in card #11; "Ansible" comes off the list.
- **Cross-repo coupling lights up.** Adding a new `!bao` ref involves
  (1) `pvginkel/IaCAgent` if `secrets.example.yaml` changes, (2)
  `pvginkel/Ansible` if Python deps change *or* if the `openbao`
  role's policy needs widening to cover a new KV path, (3) an operator
  hand-edit of the live `secrets.yaml` on `srviac`. Worth a one-
  paragraph "adding a new secret" section in the iac-agent runbook
  once the dust settles.
- **`secret_id` rotation is operator-driven**, not scheduled. Fine for
  a homelab; capture a quarterly reminder in the wife runbook if a
  cadence is desired.
- **The AppRole policy lists every KV path explicitly.** Drift between
  `secrets.yaml` and the policy is a real failure mode (resolver
  hard-fails on miss). Worth a small CI check or `ansible-playbook
  --check` task that compares the two and flags divergence.

## Commits

1. **Ansible**: `pyproject.toml` + `poetry.lock` add `hvac` (and any
   small helpers). Separate from the consumer rewrite so the image
   rebuild window is clean.
2. **Ansible**: `openbao` role gains the AppRole + policy + role
   provisioning task block at the tail of role-apply. Idempotent.
3. **Ansible**: `docs/runbooks/iac-cold-boot.md`.
4. **IaCAgent**: full Python rewrite of `bin/iac-impl`, with the `!bao`
   constructor + AppRole client + materialiser. `secrets.example.yaml`
   updated in the same commit so the schema change lands atomically.
