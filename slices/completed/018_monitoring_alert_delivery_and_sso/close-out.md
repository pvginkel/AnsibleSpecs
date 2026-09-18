# Close-out — slice 018 monitoring_alert_delivery_and_sso

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-18 12:45 → 15:06 · 6 phases · 0 bail-outs · 1 test round · doc phase done · $88.63
(planner 37 %, research 4 %, rework 1 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 018 made production alerting both believable and delivered, upgraded Keycloak, and put
production Grafana and pgAdmin behind Keycloak. In HelmCharts, the two memory-stall alerts now fire
only when the node is also short of memory or taking heavy major faults. A new warning,
`NodeMemoryStallCounterWedged`, names the node whose PSI counter has wedged, and Alertmanager
mutes that node's stall alerts while it fires. Alertmanager now sends alerts through a dedicated
Telegram bot: critical alerts with sound, everything else silent. Every Keycloak release runs
26.7.3 (DockerImages, HelmCharts), and the chart now rolls out with `Recreate`. Production Grafana
and pgAdmin show a Keycloak button beside their local login, and only an account holding the
client's `admin` role can sign in with it. The dev-cluster copies are unchanged. The doc phase
updated Ansible's runbooks and playbook comments for the `Recreate` rollout, and the Argo CD
runbook for Telegram delivery.

## Outstanding actions

Focus: Reboot srvk8s1 (A1): its stall alerts are blind until you do. A2's push has already happened
(N5). What remains of A2 is two credentialed sign-ins at grafana.home and at pgadmin.home: one with
your granted account, one with an account that has no role, which must be refused (V09/V10/V14).

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### ~~A1 — srvk8s1's memory PSI counter has been wedged since 2026-09-16 ~06:00 UTC; reboot srvk8s1 · major~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

Production Prometheus, 2026-09-18 ~11:00 UTC: srvk8s1's node_pressure_memory_stalled_seconds_total rate has read 0.71-0.97 s/s since 2026-09-16 ~06:00 (booted 2026-09-15 ~17:00), with MemAvailable at 33% of MemTotal and 1.7 major faults/s over the hour. The pre-P1 rules fire NodeMemoryStalled (critical) and NodeMemoryStallElevated on it right now, undelivered. Once P1 deploys, neither stall alert fires on srvk8s1 and NodeMemoryStallCounterWedged fires there within the hour (a replay over the retained week puts its qualifying condition on srvk8s1 from 09-16 06:36 to now, and on srvk8s2 through its recorded wedge, nowhere else). That warning firing is the rule working (review advisory A1), not a V06 failure. A reboot resets the counter and resolves it; until then P2's inhibition blinds srvk8s1's stall alerts.

test-agent, test phase round 1, 2026-09-18 — P1/P2 are now live on production (test phase r1 pushed and deployed them, IaC/HelmCharts build #6524). Live query confirms: NodeMemoryStallCounterWedged is alertstate=pending for node=srvk8s1 right now, exactly as predicted here — it will cross into firing within the hour of this note and, once it does, P2's inhibition mutes srvk8s1's two stall alerts as designed. The reboot this entry asks for is still outstanding.

**Consequence:** A real memory stall on srvk8s1, the node of the 2026-08-02 starvation, goes unannounced until it is rebooted.

**Provenance:** witnessed — code-writer, P1, r1, live production Prometheus queries 2026-09-18
**Disposition:** Is it necessary to do this now? Sunday morning there'll be a scheduled update. Then: "Yes, string the rest and close the card."

</details>

### ~~A2 — Push the rest of HelmCharts to move auth.ginbov.nl to 26.7.3 and turn on Grafana/pgAdmin Keycloak sign-in · major~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

Test phase r1 executed plan.md's two-stage HelmCharts push under the devlock's pre-authorization: DockerImages 02e19be (26.7.3 image, built and published by DockerImages build #2523) and HelmCharts 7a8944e (the 'rolling dev' stage — P1's corroborated stall alerts, P2's Telegram delivery, and P4's first commit, which moved keycloak-dev.home to 26.7.3 under the new Recreate strategy) are both live on production; IaC/HelmCharts build #6524 deployed them clean (0 errors). Local HelmCharts main is now 5 commits ahead of origin (d53b4e3 'keycloak: every release runs 26.7.3', de4c8eb 'grafana: prd signs in through Keycloak', bff7adb 'pgadmin: prd signs in through Keycloak', f5092ef, 2ceff0c) — this is the second push plan.md orders, held back per the devlock boundary ('prd stays operator-gated'): it moves auth.ginbov.nl itself to 26.7.3 (no pre-upgrade database backup — waived, N3) and turns on Grafana's and pgAdmin's Keycloak sign-in for the first time in production. Command: cd /work/HelmCharts && git push origin main. After it lands, IaC/HelmCharts will deploy keycloak-prd, grafana-prd and pgadmin-prd; verification.json V02/V03/V09/V10/V11/V14 settle by then re-checking (a granted and an ungranted homelab-realm sign-in at grafana.home and pgadmin.home settles V09/V10/F1 specifically).

test-agent, test phase round 1, 2026-09-18 — Pushed (cd /work/HelmCharts && git push origin main, 2ceff0c). IaC/HelmCharts build #6526 (SUCCESS, 370s, 0 errors) deployed keycloak-prd (now 26.7.3, migration clean, 'Bootstrap completed in 8.3s'), grafana-prd and pgadmin-prd. Live checks confirm both apps' Keycloak sign-in is wired end to end in production: grafana.home/login serves the Keycloak button and its OAuth redirect reaches auth.ginbov.nl's real authorize endpoint with the correct client_id/redirect_uri/PKCE parameters; pgadmin.home/login serves both auth sources and its keycloak-admin init container has pre-created the operator's oauth2 admin account with the server list loaded. What is still owed to the operator is narrower than this entry stated: not the push, but the two credentialed sign-ins themselves (verification.json V09/V10/V14) — signing in at grafana.home and pgadmin.home as the granted homelab account (and confirming an ungranted account is refused, F1) needs real Keycloak credentials this test phase does not hold.

**Consequence:** Until this lands: auth.ginbov.nl keeps running Keycloak 26.5.1 (only keycloak-dev.home is on 26.7.3, so R3/U1 is half-done), and Grafana and pgAdmin still only accept their local admin login — R2/#575 is coded and gated but not live for any real user.

**Provenance:** witnessed — test-agent, test phase, round 1, IaC/HelmCharts build #6524 (SUCCESS) and live kubectl/curl checks against keycloak-dev, keycloak-prd, prometheus-prd this pass
**Disposition:** All three verified. Thank you, great work!

</details>

## Notable events

Focus: All six phases merged in order. Only P6 needed a second review round, for a missing test on
the username claim, and one completion consult cleared B4. The surprise was at push time: the test
phase held back HelmCharts' second stage (auth.ginbov.nl, Grafana, pgAdmin) until the driver caught
it (N4, N5). Keycloak's one-way migration ran with no pre-upgrade dump, as waived (N3).

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### ~~N1 — srvk8s4 ran at 5% MemAvailable and up to 842 major faults/s during 2026-09-07 → 09-14, without memory stall · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

Replay for P1's thresholds: min(MemAvailable/MemTotal) 0.050 and max rate(node_vmstat_pgmajfault[5m]) 842/s on srvk8s4 (20 GiB node), p99 faults ~258–317/s, while its stall rate never exceeded 0.007. The other three nodes stayed above 17% available and under 192 faults/s. No alert covers this by design (the mixin's standalone memory alerts are out of scope).

plan-writer r3, 2026-09-14 — Replayed at the rules' one-minute evaluation over 2026-09-07 09:45 → 09-14: srvk8s4's MemAvailable floor was 3.7% of MemTotal, and srvk8s1 and srvk8s4 sat at or under 25% MemAvailable for 62% and 64% of the week, up to 47 h and 43 h at a stretch. srvk8s1 is memory-tight too, not only srvk8s4.

**Consequence:** srvk8s4 runs close to its memory ceiling with no alert on it; a capacity look may be due.

**Provenance:** witnessed, plan-writer, planning r1, live production Prometheus queries 2026-09-14
**Disposition:** Really? I just gave it a ton more memory a few days ago. Then: "Yes, string the rest and close the card."

</details>

### ~~N2 — HelmCharts: the grafana releases track a deprecated chart repo, frozen at chart 10.5.15 / Grafana 12.3.1 · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

configs/{prd,dev}/grafana/prd/release.yaml pull grafana/grafana from https://grafana.github.io/helm-charts, unpinned. That chart is marked deprecated: true (helm template warns "this chart is deprecated"); its README says updates moved to grafana-community/helm-charts after 2026-01-30. Its newest version, 10.5.15 (appVersion 12.3.1), is what production runs, so the unpinned release gets no further Grafana versions or security fixes. Not moved here — out of P5's scope.

**Consequence:** Grafana stays on 12.3.1 with no upstream fixes until the releases point at the grafana-community chart repository.

**Provenance:** witnessed, code-writer, P5, r1, helm pull grafana/grafana (Chart.yaml deprecated: true, README Chart Migration)
**Disposition:** I'm going to update all this stuff, but not now. Then: "Yes, string the rest and close the card."

</details>

### ~~N3 — Keycloak 26.7.3 deploys with no pre-upgrade database dump: the operator waived checklist step 6 on 2026-09-18, so V03's backup clause is waived, not met · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

Plan ruling 2026-09-18 (pre-run): "Don't worry about the backup. The window of data loss is minimal." No keycloak_prd_db dump is taken before the push that deploys 26.7.3 and none is set aside outside the postgres-pas backup scope's 90-object pruning, so V03's backup clause and review advisory A2 are superseded by that ruling. The same pre-run pass left two checklist items unverified: step 3's role assignment on both clients (403 on role-member and group queries with the read-only service account), and step 5's checks on homelab-dev (that token is rejected by the keycloak-dev server). The test phase's live V09/V10 sign-ins are the first check of step 3.

**Consequence:** Keycloak's 26.6 migration is one-way; if it damages keycloak_prd_db, recovery falls back to the latest nightly postgres-pas dump, losing realm changes made since then.

**Provenance:** read — completion consult 1, plan.md 'Rulings (2026-09-18, pre-run)' and verification.json V03
**Disposition:** Ok.

</details>

### ~~N4 — Test phase r1 pushed DockerImages and HelmCharts's first stage; both deployed clean · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

Per plan.md's own 'Push order (the test phase's)' and the driver's devlock pre-authorization ('pushing and rolling dev... pre-authorized; prd stays operator-gated'), the test phase pushed: DockerImages (rebased cce00ff..02e19be onto a diverged origin/main, disjoint files, no conflicts) — build #2523 SUCCESS in 254s, published registry:5000/keycloak:26.7.3-postgres-health-ispn. Then HelmCharts's first stage (rebased 6e5baa1..7a8944e onto a diverged origin/main via dev:rebase-agent, disjoint files except tests/conftest.py which merged cleanly with both sides' intent preserved, kc project test green) — IaC/HelmCharts build #6524 SUCCESS in 197s, 0 errors, deployed prometheus-prd (P1+P2), keycloak-dev (26.7.3) and keycloak-prd (still 26.5.1, Recreate-rolled only). Live checks post-deploy: all three node-memory-pressure rules health=ok; Alertmanager's live config matches values.yaml verbatim (route, inhibit rule, both Telegram receivers); NodeMemoryStallCounterWedged is pending on srvk8s1 exactly as close-out A1 predicted; both keycloak Deployments report {"type":"Recreate"} live, and keycloak-prd's rollout events show the old pod deleted before the new one was created. HelmCharts's second push (auth.ginbov.nl, Grafana, pgAdmin) was deliberately not pushed this pass — see the new Outstanding actions entry.

**Consequence:** none — this is the record of what the test phase itself did, not a defect

**Provenance:** witnessed — test-agent, test phase, round 1, this session's push+deploy+live-check trail (IaC/HelmCharts build #6524, DockerImages build #2523, live kubectl/curl evidence cited in verification.json V01/V04-V08/V13/V15)
**Disposition:** Ok.

</details>

### ~~N5 — Test phase r1 pushed HelmCharts's second stage (auth.ginbov.nl to 26.7.3, Grafana/pgAdmin Keycloak sign-in) after the driver caught it unpushed · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

This test phase's first pass left HelmCharts' remaining 5 commits (d53b4e3, de4c8eb, bff7adb, f5092ef, 2ceff0c) unpushed, reasoning the devlock's 'prd stays operator-gated' boundary meant to hold back auth.ginbov.nl's cutover. The driver corrected this: 'work this slice committed is not on origin... a reviewed-but-unpushed commit never reaches the deploy it was meant for' — so the whole slice, not just the first stage, was owed. Pushed HelmCharts main (2ceff0c); IaC/HelmCharts build #6526 (SUCCESS, 370s, 0 errors in 1008 log lines) deployed keycloak-prd (26.7.3, every realm — kensho-prd/tst/dev/uat, master, homelab — migrated cleanly through 26.6.1/26.6.2/26.7.0, 'Bootstrap completed', no error), grafana-prd and pgadmin-prd. Re-verified every live check the push invalidated: keycloak-prd's Deployment reports Recreate and rolled the old pod out before the new one in (same as keycloak-dev's earlier rollout); grafana.home/login now live-serves the Keycloak button and its OAuth redirect reaches auth.ginbov.nl's real authorize endpoint with the correct client_id/PKCE/redirect_uri; pgadmin.home/login live-serves both auth sources and its keycloak-admin init container has pre-created the operator's oauth2 admin account with the server list loaded. Every HelmCharts commit this slice produced is now on origin and deployed; verification.json V02/V03/V11/V13 moved from owed to verified on this evidence, V09/V10/V14 stay owed only for the credentialed sign-in itself (real Keycloak credentials this test phase does not hold).

**Consequence:** none — this is the record of what the test phase's correction did, not a defect

**Provenance:** witnessed — test-agent, test phase, round 1, IaC/HelmCharts build #6526 and live kubectl/curl evidence cited in verification.json V02/V03/V09-V11/V13/V14
**Disposition:** Ok.

</details>

## Bugs

Focus: B5 comes first, and it is the only fully witnessed bug: a loud stall alert that fires before
its node's wedge warning can sit in the chat without a `[RESOLVED]` notice. B1 is read only and
predates the slice, but it is serious: a live OpenAI key sits in HelmCharts history. B7 (partly
witnessed) and B6 break Keycloak sign-in only from the short host names. Every bug is in HelmCharts
except B8, a stale Ansible comment.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — HelmCharts: an OpenAI API key is committed in plaintext in configs/dev/electronics-inventory/prd/values.yaml:15 · major

The file's header accepts inline dev secrets because the dev cluster is isolated, but an OpenAI project key (sk-proj-…) is a third-party credential usable from anywhere — the isolation argument does not cover it. Seen while surveying dev-cluster OIDC precedent for slice 018; nothing in this slice touches that release.

**Consequence:** A working OpenAI key sits in HelmCharts' git history for anyone with repo read access; rotating it and materialising it from OpenBao is owed.

**Provenance:** read, plan-writer, planning r1, HelmCharts configs/dev/electronics-inventory/prd/values.yaml
**Disposition:** Raise. — Triage #1048 https://trello.com/c/jVRKg7Ml

### ~~B2 — HelmCharts CLAUDE.md: says prd Prometheus retains ~2 days (retentionSize: 2GB); the release sets 7d / 10GB · minor~~ — resolved — HelmCharts 73560d9, fixed by the operator's ruling 2026-09-18

<details><summary>struck — body kept for the record</summary>

HelmCharts CLAUDE.md (recommend-resources) states the window is nominally 5 days but Prometheus retains ~2 (retentionSize: 2GB). configs/prd/prometheus/prd/values.yaml:3-4 sets retention: 7d, retentionSize: 10GB, and a 7-day range query answered with a full week of data on 2026-09-14.

**Consequence:** recommend-resources' documented measurement window is wrong; a reader sizing resources or an investigation trusts a 2-day window that is really 5.

**Provenance:** read, plan-writer, planning r1, HelmCharts CLAUDE.md + live Prometheus query
**Disposition:** Fix inline. — HelmCharts 73560d9 (CLAUDE.md: recommend-resources reads 7 days, NUM_DAYS, and prd Prometheus keeps 7d/10GB; the stated 5-day window was wrong too); not pushed

</details>

### ~~B3 — Ansible docs: k8s-rebuild.md and pre-drain-handoff.yml still name keycloak-db as a pre-drain opt-in that no longer exists · minor~~ — resolved — Ansible 568419f dropped the retired keycloak-db opt-in: docs/runbooks/k8s-rebuild.md:36 and ansible/playbooks/tasks/pre-drain-handoff.yml:22 now name keycloak only (checked 2026-09-14); struck by plan-writer r3

<details><summary>struck — body kept for the record</summary>

docs/runbooks/k8s-rebuild.md:35 describes a keycloak-db Deployment (Recreate, ~30 s outage) handed off before every drain, and ansible/playbooks/tasks/pre-drain-handoff.yml:22 lists 'keycloak, keycloak-db (HelmCharts)'. In HelmCharts only charts/keycloak/templates/keycloak-deployment.yaml:7,22 carries iac.webathome.org/pre-drain, and the live keycloak-prd namespace runs a single keycloak Deployment (Keycloak's database is postgres-pas, charts/keycloak/values.yaml:9).

**Consequence:** An operator reading the runbook before a node drain expects a keycloak-db hand-off and outage that no longer happens; the stale line can survive when slice 018's doc phase rewrites keycloak's entry for the stop-before-start rollout.

**Provenance:** read, plan-writer, planning r2, plan.md P4
**Disposition:**

</details>

### ~~B4 — HelmCharts: the wedge alert's look-back comment and test cite for-grace-period as the restart bound, which does not apply to firing alerts · minor~~ — resolved by consult 1 (HelmCharts 3987dee): values.yaml's hold comment and the test's comment now give the real bound, restart downtime plus a couple of evaluations; the FOR_GRACE_MINUTES < look-back assertion stays as a conservative floor; kc project test re-run green. plan.md's P1 Record (the 10m for-grace-period sentence) still repeats the old reason; struck by consult 1

<details><summary>struck — body kept for the record</summary>

configs/prd/prometheus/prd/values.yaml:127-130 and tests/test_prometheus_node_memory_alerts.py:37,:133 say the 30m ALERTS look-back must exceed restart downtime plus the 10m rules.alert.for-grace-period, because a restored alert stays pending that long. Prometheus applies the grace period only to alerts that were still pending. A restored alert that was already firing fires again on the first evaluation after restore: witnessed with Prometheus 3.5.0, for 60s and grace 30s, firing again 12s after restart. The real bound is downtime plus about two evaluation intervals, and 30m meets it.

**Consequence:** none — 30m meets the real bound too; only the stated reason, and the test assertion built on it, are wrong

**Provenance:** witnessed, code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:**

</details>

### ~~B5 — HelmCharts: a stall alert delivered before its node's wedge warning fires never gets a [RESOLVED] notice once the wedge inhibits it · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

The prd Alertmanager inhibit rule (configs/prd/prometheus/prd/values.yaml:281-284) mutes a target's resolve as well as its firing, and Alertmanager drops the resolved alert after that muted flush. A corroborated NodeMemoryStalled delivered loud during a wedged node's first-detection window (P1: ~44 h on average on srvk8s1) is therefore never closed in the chat, even after the wedge warning resolves. Witnessed on a local Alertmanager 0.34.1 on this config: stall firing, wedge firing, stall resolved, wedge resolved sent no resolve for the stall alert.

code-reviewer P2 r1, 2026-09-18 — Line citation correction: the inhibit rule is configs/prd/prometheus/prd/values.yaml:278-281, not 281-284.

**Consequence:** The Telegram chat can hold a loud critical NodeMemoryStalled that never resolves, which reads as an ongoing stall; unlikely, since P1's replay found no corroborated stall minute in the retained week.

**Provenance:** witnessed — code-reviewer, P2 r1, phases/P2/code_review_r1.md F1
**Disposition:** Close.

</details>

### ~~B6 — HelmCharts: prd Grafana's Keycloak sign-in fails on the first try when started from the http://grafana/ short name · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

configs/prd/grafana/prd/values.yaml pins root_url http://grafana.home/, so the OAuth redirect always goes to grafana.home. The release still serves the short name grafana (values.yaml:6, charts/grafana/architecture.yaml). Grafana keeps its OAuth state in a host-only cookie, so a sign-in started at http://grafana/ comes back to grafana.home with no state and fails with 'Missing saved oauth state' (Grafana 12.3.1 authn/clients/oauth.go:115-117). A retry from grafana.home works, and the local login form works on both names.

**Consequence:** Opening http://grafana/ and clicking Keycloak shows a login error once, until the user retries from grafana.home.

**Provenance:** read, code-reviewer, P5, r1, phases/P5/code_review_r1.md F1
**Disposition:** Close.

</details>

### ~~B7 — HelmCharts: prd pgAdmin's Keycloak sign-in is refused by Keycloak when started from the http://pgadmin/ short name · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

pgAdmin builds its OAuth redirect URI from the request's Host header (Flask url_for(_external=True); the nginx proxy passes Host $host, pgAdmin sets no fixed root URL). The pgadmin service answers both pgadmin.home and pgadmin (configs/prd/pgadmin/prd/values.yaml serverName), but the pgadmin Keycloak client registers only http://pgadmin.home/oauth2/authorize (pre-run checklist step 2). Started from http://pgadmin/, the Keycloak button sends redirect_uri=http://pgadmin/oauth2/authorize, which Keycloak rejects. Fix on the Keycloak side: add http://pgadmin/oauth2/authorize as a valid redirect URI on the pgadmin client (and record it in the plan's client table for keycloak-tf). Sibling of B6 (Grafana).

**Consequence:** Opening http://pgadmin/ and clicking Keycloak shows Keycloak's invalid redirect_uri error instead of signing in; signing in from pgadmin.home works.

**Provenance:** read — code-writer, P6, r1: pgAdmin 9.18 web/pgadmin/authenticate/oauth2.py authenticate() url_for(OAUTH2_AUTHORIZE, _external=True); witness pod redirect_uri followed the Host header
**Disposition:** Close.

</details>

### ~~B8 — Ansible: update-k8s.yml comments still size drain timeouts by keycloak-db's 600s preStop, and that workload no longer exists · nit~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

ansible/playbooks/update-k8s.yml ~164 ("The slowest legitimate shutdown here is keycloak-db's 600s preStop") and ~419 ("keycloak-db's 600s preStop + tGPS") justify the pre-drain sweep's grace headroom and the drain timeout by a Deployment that was retired before this slice (Keycloak's database is the CNPG postgres-pas cluster). This predates slice 018. The doc phase found it while reconciling the keycloak comments in the same file and left it: fixing it means re-deriving why those values were chosen, and that is not a doc edit. Only the comments are stale; the timeout values stay as they are.

**Consequence:** Anyone retuning the drain timeouts works from a slow-shutdown workload that is gone. Nothing changes at run time.

**Provenance:** read — doc-writer, doc phase, r1: ansible/playbooks/update-k8s.yml, docs/runbooks/k8s-rebuild.md:36
**Disposition:** Close.

</details>

## Open questions and rulings

Focus: None open. Every question this slice raised was ruled on before or during the run.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: S1 feeds the keycloak-tf slice: it needs the hand-made client table before this slice is
compressed. S5 affects whoever builds the SMTP gateway from DockerImages' plan. S3 is an
architecture-model edit. S2 (witnessed) and S4 are HelmCharts test-coverage gaps.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S2 — Put promtool in the iac toolchain so HelmCharts' suite can unit-test alert rules · minor

The iac sidecar has helm/poetry/ruff but no promtool, so tests/test_prometheus_node_memory_alerts.py pins each memory-stall rule's whole expression and thresholds by regex but evaluates no PromQL. P1 ran promtool 3.5.0 (downloaded to /tmp, not committed) over scenario series: the starvation fires both stall alerts, a srvk8s2-shaped wedge fires only the wedge warning and holds through a 60-minute memory dip, a reboot resolves it, a healthy memory-tight node stays quiet, overlapping helm_sh_chart series evaluate to one alert per node, and a 90m look-back mutation re-fires the warning after a reboot — the suite could carry that as a promtool test file.

**Consequence:** A PromQL precedence or matching mistake in an alert rule passes the gate and first shows once Prometheus loads or evaluates it.

**Provenance:** witnessed — code-writer, P1, r1
**Disposition:** File. — Triage #1049 https://trello.com/c/3Qx3bSby

### S3 — Model Alertmanager's new dependency on the Telegram Bot API in the architecture · minor

P2 makes production Alertmanager (ss:alertmanager in HelmCharts charts/prometheus/architecture.yaml) send to api.telegram.org. The generated architecture has a svc:telegram-bot-api serving edge for jenkins-telegram-bot (DockerImages jenkins-telegram-bot/architecture.yaml:30-32) but nothing declares one for Alertmanager, so the model does not show that alert delivery depends on Telegram.

**Consequence:** The architecture model omits that alert delivery depends on Telegram, so a Telegram outage or bot revocation does not show up as affecting alerting.

**Provenance:** read, code-writer, P2, r1, HelmCharts charts/prometheus/architecture.yaml
**Disposition:** File with an additional Architecture label please. — Triage #1050 https://trello.com/c/6xMv13Cu (Ansible + Architecture labels)

### ~~S1 — Point the keycloak-tf placeholder at slice 018's hand-made client table · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

The #575 forward constraint says keycloak-tf must import these clients, never recreate them; the record of the four clients (ids, redirect URIs, admin roles, the pgadmin_roles mapper) lives in slice 018's plan.md pre-run checklist. Slice documents are compressed at close (design-philosophy.md), and change_requests/keycloak_tf/keycloak-tf.md does not reference it.

plan-reviewer r1, 2026-09-14 — Since ruling D6 the plan's pre-run checklist records two hand-made clients (grafana, pgadmin — production homelab realm only), not four; the keycloak-tf pointer should name those two.

**Consequence:** The keycloak-tf slice may not find the client inventory it must import once slice 018 is compressed.

**Provenance:** read, plan-writer, planning r1, AnsibleSpecs change_requests/keycloak_tf/keycloak-tf.md
**Disposition:** Close.

</details>

### ~~S4 — HelmCharts: cover pgadmin's fresh-storage bootstrap (keycloak-admin's setup-db step and setup-log mount) in test_pgadmin_keycloak_login.py · minor~~ — closed by the operator, 2026-09-18

<details><summary>struck — body kept for the record</summary>

The keycloak-admin init container's setup-db step (charts/pgadmin/templates/pgadmin-deployment.yaml:71-73) and its /var/log/pgadmin emptyDir mount (:92-93, :146-147) only run on a volume with no pgadmin4.db. The image has no /var/log/pgadmin and runs as uid 5050. Removing either one still passes all 9 tests. Production's PVC already holds the database, so neither runs there today.

**Consequence:** If a later edit drops either line, the suite stays green, and pgAdmin fails to start the next time its PVC is rebuilt or restored empty.

**Provenance:** read — code-reviewer, P6, r1, phases/P6/code_review_r1.md F2 (mutations run)
**Disposition:** Close.

</details>

### ~~S5 — DockerImages: docs/alert-manager/plan.md still calls its Alertmanager Telegram half unimplemented, and gives a different secret path and receiver set from what slice 018 shipped · minor~~ — resolved — DockerImages 69b2c85, fixed by the operator's ruling 2026-09-18

<details><summary>struck — body kept for the record</summary>

The plan's header reads "not yet implemented", and Part A (A1-A4) is written as future operator work: the bot token and chat id at OpenBao kv/shared/prd/telegram-infra-alerts, the Secret mounted at /etc/alertmanager/secrets/telegram, and four receivers ({metrics, events} x {critical, warning}). The live production config is HelmCharts configs/prd/prometheus/prd/: the leaf eso/prd/prometheus/prd/telegram, a mount at /etc/secrets/telegram (outside the config ConfigMap's /etc/alertmanager), and two receivers (telegram-critical, telegram-warning: the metrics row only, since the SMTP gateway was not built). The doc phase left it alone because the page is in DockerImages, which is not a surface in Ansible's slice-doc-plan, and is not on the doc branch. Owed: mark Part A done, point it at the shipped config, and restate the events row as what the gateway work adds.

**Consequence:** Anyone building the SMTP gateway from this plan redoes Part A against a config that already exists: a second OpenBao leaf for the same bot and a four-receiver route tree that replaces the live one.

**Provenance:** read — doc-writer, doc phase, r1: DockerImages docs/alert-manager/plan.md lines 1-4 and 237-330 against HelmCharts.diff P2
**Disposition:** Fix inline. — DockerImages 69b2c85 (header, D10, scope item 1, Part A rewritten to the shipped config plus the events row the gateway adds, E1); not pushed

</details>
