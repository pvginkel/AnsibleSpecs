# P3 code review — round 1

Range: DockerImages `d58ad42..33412e2` (`phase/018-P3`), one commit, one line.

**Readiness: ready to merge, no findings.** The phase's outcome is that `keycloak/build-matrix.json`
builds 26.7.3 as `registry:5000/keycloak:26.7.3-postgres-health-ispn`, with the image's build options
unchanged. The diff changes only `KEYCLOAK_VERSION` 26.5.1 → 26.7.3 (`keycloak/build-matrix.json:5`).
The Dockerfile is untouched, so `KC_DB=postgres`, `KC_HEALTH_ENABLED=true`, `KC_CACHE=ispn` and
`start --optimized` carry over as they were. I checked the change in four ways:

- **Tag resolution.** A targeted run of `tools/collect-internal-dependencies.py` on the branch gives the
  variant `{'image': 'keycloak', 'matrix': True, 'tag': '26.7.3-postgres-health-ispn', 'args':
  {'KEYCLOAK_VERSION': '26.7.3'}}` with no descendants. The Jenkinsfile's matrix branch
  (`Jenkinsfile:88-94`) pushes exactly `registry:5000/keycloak:<tag>`, which is the name P4 and the
  push order depend on.
- **Build trigger.** The Jenkinsfile's `utils.hasChanges("${img}/.*")` (`Jenkinsfile:46`) matches
  `keycloak/build-matrix.json`, so the image rebuilds when the commit reaches `main`.
- **Upgrade notes.** I spot-checked the plan's claim against Keycloak's upgrading guide for 26.5.2–26.7.3.
  It records no change to the `db`, `health-enabled` or `cache` options, the management port, or
  `kc.sh build` / `--optimized` handling, and it states no new PostgreSQL minimum. The one related change
  is the socket and query timeouts that 26.7.0 adds at runtime, and those are not a build option.
- **Leftover pins.** The remaining `26.5.1-postgres-health-ispn` strings in the repo
  (`docs/registry-management/version-poller-redesign.md:150,158` and
  `version-poller/tests/test_poller.py:20`) are sample tags for the tag classifier, not version pins.

Gate state: no deterministic gate is recorded for this commit. For a one-line JSON change, the collector
parsing the file is the relevant check, and it passed. The executor reported a kaniko `--no-push`
build; I did not re-run it.

## Findings

None.
