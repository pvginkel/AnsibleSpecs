# P6 code review — round 1

Range `cd2f50d..31e86b5` (branch `phase/019-P6`): one commit, `docs/runbooks/openbao.md` only.

**Readiness: ready to merge, no findings.** §3 of the runbook now runs converge (3), restore (4),
converge again (5), verify (6). Step 5 says why it exists and names the cost of the rotation run,
which meets P6's outcome and V18. I checked each concrete claim against the code it describes and
found none contradicted:

- **Step 3 prints "not delivered" or the skip message.** `init.yml` hands no root token onward. On
  an empty cluster the admin AppRole login is tolerated and `_openbao_token` ends up empty
  (`auth-token.yml:44-47,74-77`), so `approle.yml:35-36` skips. `backup.yml:75-80,142-163` then
  prints one of the two quoted messages. `openbao_config_dir` is `/etc/openbao` on the replaced
  root disk (`defaults/main.yml:16`), so `_openbao_backup_ready` is false.
- **Step 5 authenticates with the admin AppRole and re-stages the role_id before proving.** It
  falls back to the vault'd admin AppRole (`auth-token.yml:26-57`). `main.yml:145` runs
  `approle.yml` before `backup.yml` at `:165`, on the bootstrap host only. The role_id is
  re-staged at `approle.yml:371-382`, and the revoke-self policy grant is rewritten at `:194-211`
  before any node proves.
- **The three outcomes match the code.** The step-5 bullets quote `Refuse a staged backup
  secret_id the backup AppRole rejects` and `OpenBao backup pipeline not configured`, which match
  `backup.yml:82,155`. Timer enabled matches `:223-228`. The upload token comes from Play 0
  (`site-openbao.yml:109-133`).
- **The rotation run's cost is stated correctly.** It mints for all six roles
  (`approle.yml:329-347`) with no `secret_id_ttl` set (`:258-270`) and revokes nothing. The
  closing message prints `shred -u` (`:486`).
- **Step 6's expected journal line is real.** `log()` prefixes `openbao-backup:`
  (`openbao-backup.sh.j2:28`) before `backup uploaded (…)` (`:166`). The oneshot unit
  (`openbao-backup.service.j2`) makes `systemctl start` block until the backup exits.

Nothing else cites §3's steps by number, so renumbering verify to step 6 breaks no reference. I
made no targeted runs: the phase is prose only, and every claim can be checked by reading the
code. The gate (`root: no test statements — skipped`) is taken as given.
