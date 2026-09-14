# Slice 018 — plan review, round 1

Verdict: **questions**. The plan matches slice.md and the rulings, and the code facts it cites
hold. One finding touches ruling D2's own design and wording, so only the operator can settle it.
A second shows that ruling D5 was weighed against a premise that is false. Two advisories follow.

## Operator-decidable

### Q1 — On a wedged node the corroborated stall alerts do not go blind: they fire on the corroborating signal alone, and the wedge warning tells the operator the opposite

**Problem.** Under D2, the two stall alerts require the stall rate *and* a corroborating signal
(MemAvailable under 10% of MemTotal, or major faults above 500/s) (P1, `plan.md:312-318`; V04). On a
wedged node the stall term is always true: srvk8s2 ran at 0.32–0.92 s/s against thresholds of
0.05 and 0.02. Both alerts then reduce to the corroborating signals alone. P1 leaves exactly those
signals out of scope as standalone alerts, because "on their own they would have fired on srvk8s4
in an ordinary week" (`plan.md:447-449`). Meanwhile the new wedge warning says "the stall alerts on
that node are blind until it is rebooted". That wording is ruling D2's (`plan.md:55-57`), repeated
in P1 and V05. P1's "Neither signal alerts alone" (`plan.md:317-318`) holds only on a node whose
counter works.

**Evidence.** I replayed this independently on production Prometheus over 2026-09-07 → 09-14. The
corroborating condition held on srvk8s4 alone, in 17 five-minute buckets. At least one stretch held
continuously for 10 minutes (peak 842 faults/s). That is long enough for `NodeMemoryStalled`'s
`for: 10m`. srvk8s4's stall rate stayed under 0.007, so today nothing fires. Had srvk8s4's counter
been wedged that week, the critical alert would have paged. Wedges are not rare: srvk8s3 from about
08-13, then srvk8s2 from 09-07 to 09-13, each lasting days.

The plan's own figures otherwise reproduce:
- The wedge expression holds on srvk8s2 for 1645 buckets of its wedge (plan: 1641) and on no other node.
- The corroborated rules match no bucket all week.
- Every node carried two series in that week (one today).

**Impact.**
- A wedged node plus an ordinary memory dip delivers a loud critical to Telegram. That is the class
  of false page D2 exists to remove.
- The "blind" message primes the operator to dismiss any stall alert on that node. Yet while the
  node is wedged, those alerts fire on real low-memory or thrashing signals.
- D2's "If this is wrong" in refinement.md never weighed this state. The wording and behaviour
  come from the operator's ruling, so they are the operator's to confirm or change.

### Q2 — Ruling D5's trade-off leaned on a Keycloak database outage that does not exist, and the plan still presents it as verified

**Problem.** The plan's Grounding is headed "verified 2026-09-14". Its D5 bullet ends
"`keycloak-db` there is already `Recreate` with a ~30 s outage" (`plan.md:224-226`). Refinement's D5
used that as live fact twice:
- in Background: "Keycloak's database already stops then starts during the same hand-off … so
  sign-in already blinks when the database's node is drained"
- in the recommendation's trade-off: "sign-in already blinks for the database during node updates"

**Evidence.**
- No `keycloak-db` Deployment or StatefulSet exists on production. Only `keycloak` runs, in
  `keycloak-prd` and `keycloak-dev`.
- Keycloak's database is the CNPG `postgres-pas` cluster: `postgres-1/2/3` on three nodes, plus two
  pooler replicas (`charts/keycloak/values.yaml:9`).
- The keycloak-db line survives only in `docs/runbooks/k8s-rebuild.md:35` and
  `pre-drain-handoff.yml:22`. The plan-writer's own close-out B3 already calls it stale, but the
  Grounding line was left standing.

**Impact.**
- The cost the ruling states is still correct: about 30 s of sign-in outage per Keycloak rollout,
  node-update hand-off included. But the comfort the operator weighed it against is false. Today a
  node update costs Keycloak sign-in nothing beyond a possible CNPG switchover. After P4 it costs a
  30 s outage whenever Keycloak's pod sits on the drained node.
- The operator chose A over B (a one-off manual stop) partly on that comfort.
- The doc phase takes the rulings section as its only steering. When it rewrites the runbook's
  Keycloak hand-off entry for the stop-before-start rollout, it reads the keycloak-db outage there as
  verified fact.

## Advisory

### A1 — V06 turns on node state no phase controls, and its overlap clause stops being checkable after a week

**Problem.** V06 requires that "none of the node-memory-pressure alerts fires on production's nodes
as they stand after deploy". That set includes P1's new wedge warning, which is built to fire when a
counter wedges. So a wedge before the test phase checks would fail V06 while the rules behave
correctly. V06 also requires clean evaluation "while a node-exporter chart upgrade leaves overlapping
series per node".

**Evidence.**
- Two wedges in about a month (Grounding).
- The overlap is in retention now: at most 2 series per node over the last 7 days, 1 today.
- Retention is `7d` (`configs/prd/prometheus/prd/values.yaml:3`), and the prometheus release pins no
  chart version.

**Impact.**
- A wedge in the run window means a failing criterion, then an appended-phase round, over correct
  rules.
- Once the overlap leaves retention, a test phase can no longer check the overlap clause against
  data, only by reading the rules.

### A2 — The pre-upgrade Keycloak backup is pruned by count alongside every other database's nightly dump; its name lives only on the Job

**Problem.** Checklist step 6 frames the backup as a named, one-off safeguard
(`postgres-backup-pre-keycloak-26-7`, `plan.md:272-275`). U1 wants it because the migration "cannot
be downgraded". But the dumps the Job uploads carry no trace of that name, and they are pruned by
count alongside every nightly dump.

**Evidence.**
- `backup.py` uploads each database as `<db>.dump`.
- backup-server stores each upload as `<timestamp>_<db>.dump.age` under the one scope `postgres-pas`
  (`backup-server/src/internal/pipeline/upload.go:52-58`).
- After every upload it deletes everything in that scope past the token's `retention` count
  (`pipeline/prune.go:14-26`).
- The nightly run (00:00 UTC) uploads 9 databases (2026-09-14 job log).

**Impact.** Once the push deploys 26.7.3, the last pre-migration `keycloak_prd_db` dump survives
roughly retention ÷ 9 nightly runs. The plan never states that retention. The checklist's evidence
(the Job log ending "all databases backed up") says nothing about how long the copy lasts.

## Checked and holding

- **Acceptance criteria.** R1, R2 and R3 map 1:1 to V01–V03 in the operator's words.
  - Each narrowing has its ruling: local logins kept (D4), production only (D6).
  - Every ruling, fact and settled item with an outcome has a criterion: D1–D6, F1, F2, U1, settled
    items 1 and 6.
  - No criterion is handed to the doc phase, and none is a doc-truth universal.
- **Task shape.** `cross-cutting` is right. slice.md settles no mechanism: #625 gives no thresholds or
  delivery design, #575 leaves its questions to refinement, and the work spans the prometheus,
  grafana and pgadmin releases.
- **Targets.** Every `Target:` is an existing sibling repo, and each is where its phase's work lands.
- **Phases.** Six PR-sized phases, producers first (P3 image before P4 tag). No end-to-end or
  auto-doc phase, and no attachments.
- **Design citations checked against source.**
  - Alertmanager v0.34 reads `BotTokenFile` and `ChatIDFile` (`notify/telegram/telegram.go:143-161`).
    The alertmanager subchart has `extraSecretMounts` and renders `config` with plain `toYaml`.
  - The deploy CLI runs `helm upgrade --install` without `--wait` and applies `manifests.yaml`
    immediately after (`tools/deploy/deploy_cli/helmops.py:196-203`), so the ExternalSecrets in P2
    and P5 are fine on first deploy.
  - Grafana's generic OAuth reads the role from the access token too (`collectUserInfoData`,
    `extractFromAccessToken`), and `role_attribute_strict` refuses a login with no role.
  - pgAdmin checks `OAUTH2_ADDITIONAL_CLAIMS` against the ID token, then userinfo, and refuses on no
    match (`oauth2.py:603-662`). It uses the email as username. Its redirect is `/oauth2/authorize`.
    `setup.py` has `add-external-user --admin` and `load-servers` with an auth source.
  - The pre-drain hand-off waits on the Deployment's observed, updated, ready and available counts
    (`pre-drain-handoff.yml:123-157`), so a stop-before-start rollout needs no change there.
  - On the live Keycloak Deployment, helm's apply owns `spec.strategy.rollingUpdate`, so the
    server-side-apply trap P4 names does not apply as it stands.
  - ESO's OpenBao policy already grants `eso/prd/*`.
  - Nothing under `configs/prd` outside keycloak uses `homelab-dev`.
  - The backup CronJob exists.
  - The incident citations (`02-measurements.md:136`, `06-eviction.md:73`) say what P1 quotes.
