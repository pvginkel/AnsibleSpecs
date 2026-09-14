# P2 code review — round 1

Range `1a5117ac..d305510` (one commit, `ansible/roles/openbao/templates/openbao-backup.sh.j2`).

**Readiness: ready to merge.** P2 meets its outcome. Every HTTP call in the wrapper goes through `request` (`openbao-backup.sh.j2:37-49`); OpenBao calls also go through `bao_check` (:61-71). That covers:
- the leader check (:76)
- the login (:86)
- the snapshot (:96)
- the policy LIST and reads (:100, :104)
- the KV LIST and reads (:117-121, :128)
- `sys/auth` and `sys/mounts` (:138, :140)
- the upload (:156-164)

A failure logs the call's name, then the HTTP status or curl's exit code. For OpenBao calls it also logs the `errors` strings, and nothing else from the body. Nothing is logged on success. Every helper runs in the main shell, never inside `$(…)`, so its `exit 1` ends the script. `kv_walk` copies the listed keys into a local before it recurses (:122), so the shared `${resp}` file does not break the walk. A follower still exits 0 (:78-81).

Checks run for this review:
- **shellcheck.** v0.10.0 on a rendered copy of the template: clean. `bash -n`: clean.
- **KV walk, old vs new.** Both walks were run against OpenBao 2.5.4 `bao server -dev` in the iac sidecar. They produce the same `kv` tree for a two-level store.

The gate was green on d305510 and was not re-run. The one finding below is advisory: the behaviour predates this phase.

## Findings

### F1 — Minor · advisory · anchor: repro-trace · confidence: high

**A soft-deleted KV-v2 secret fails every leader backup, now with a named line.** The walk treats 404 as "no keys here" only for the metadata LIST (`openbao-backup.sh.j2:118-120`). A data read goes through `bao_api` (:128), where any non-2xx ends the run.

OpenBao keeps listing a soft-deleted key. It answers the key's data read with 404 and `{"data":{"data":null,"metadata":{…"deletion_time":…}}}`.

Repro, OpenBao 2.5.4 dev server:
1. `kv/a`, `kv/b` and `kv/d/c` written, then `bao kv delete kv/a` (the default soft delete).
2. `LIST kv/metadata/` → 200, keys `["a","b"]`.
3. `GET kv/data/a` → 404.
4. The new walk exits 1 with `openbao-backup: GET kv/data/a failed: HTTP 404`.

This is not a regression. The pre-change walk, run the same way, also exits 1: three `jq: invalid JSON text passed to --argjson` lines, then `KV walk failed`.

What remains is that one routine `bao kv delete` on any path stops every nightly backup. Nothing alerts on it until slice 023. P2 changes only how clearly the journal names the cause. Entered in close-out Bugs.
