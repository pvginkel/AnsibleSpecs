# P1 code review — round 1

**Range:** `bf11aa5..1a5117a` (branch `phase/019-P1`). **Gate:** green on `1a5117a` (`gate_r1.log`), taken as given.

**Readiness.** P1 meets its outcome and can merge. The staged role_id and secret_id are proven with an AppRole login at `openbao_admin_api_addr` (`ansible/roles/openbao/tasks/backup.yml:54-69`). That login runs under `--check` too (`check_mode: false`), with `no_log`.

The result is handled as the Done record states:
- **200:** the proving token is revoked through `revoke-self` (:106-129), which `backup-policy.hcl.j2:13-15` now grants.
- **400:** the run fails, naming `-e openbao_rotate_secret_ids=true` (:82-92).
- **403 `["permission denied"]`:** the secret_id is reported not delivered, and the generic skip message is suppressed (:75-80, :142-163).
- **Anything else:** the run fails with the status and the error text (:94-104).

Delivery now requires a proven secret_id (:192). Readiness requires a proven secret_id or one already on the node (:136-140).

I checked three things the premise depends on:
- **The 403 case cannot hide a dead secret_id.** The AppRole write sets no CIDR bindings (`approle.yml`, "Write AppRoles"), so a mounted AppRole answers bad credentials with 400.
- **The bootstrap host goes first.** It is always the sorted-first host (`elect-bootstrap.yml:12-14`), so on the serialized apply a rotation re-stages the secret_id before any node proves it.
- **Step 3 has no AppRole mount.** The pre-restore converge in `docs/runbooks/openbao.md` §3 step 3 passes no admin token, so the cluster has no AppRole mount and step 3 takes the 403 path.

No finding is blocking. Two are advisory: one is about the rotation remedy's dry run, the other about a planning fact that bears on rollout.

## F1 — Minor · advisory · anchor: repro-trace · confidence: high

**The remedy the rejection names has no working dry run. On the non-bootstrap nodes, P1 adds a failure whose message contradicts the invocation.**

This happens on a `site-openbao.yml --check -e openbao_rotate_secret_ids=true` run from a checkout whose staged backup secret_id is dead.

- The mint is a `uri` task with no `check_mode:` override (`approle.yml:329-347`), so `--check` skips it. The staged file is never replaced.
- Under `--check` the converge play is not serialized (`playbooks/site-openbao.yml:171`), so every node runs `backup.yml`.
- On srvvault2 and srvvault3 the proving login gets 400. The run fails at `backup.yml:82-92` with "Mint and stage a fresh one with a site-openbao.yml run with -e openbao_rotate_secret_ids=true", the flag the run already carries. The apply of the same command succeeds.
- The bootstrap host fails earlier, and this predates P1. Under `--check` with the rotation flag, `approle.yml:384-395` renders `.json.data.secret_id` from the skipped mint's results and errors out. I witnessed this with a playbook in the `iac` sidecar that mirrors both tasks: "Error while resolving value for 'content': object of type 'dict' has no attribute 'json'".

This is not a regression of a working check, because the dry run was already red on the bootstrap host. The consequence stands, though. The operator applies the rotation run with no preview, and that run mints never-expiring secret_ids for all six AppRoles (plan ruling F6). The `--check` output they get tells them to pass a flag they already passed. Entered in the close-out as a Bug.

## F2 — Minor · advisory · anchor: none · confidence: high

**The plan's staging-dir grounding is wrong about this checkout, and that matters for the policy-grant rollout (close-out N1).**

`plan.md:51` says that on 2026-09-14 `/work/Ansible/tmp` held no secret_id file. It holds `openbao-backup-secret-id`, dated 2026-08-13 20:37, next to the role_id and the `openbao-credentials/` files from the same run (listing only; no contents read).

So the pre-apply failure N1 describes is certain, not hypothetical, for the operator's own checkout. The first `--check` or `--tags openbao_backup` run of `site-openbao.yml` from `/work/Ansible` after merge proves that file:
- if it is live, the run fails with 403 at `backup.yml:120-129` until an apply writes the policy grant;
- if it is dead, the run fails at the rejection.

Recorded as a note on N1 in the close-out.
