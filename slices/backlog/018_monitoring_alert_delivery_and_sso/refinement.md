# Slice 018 — refinement

## D1 — Alert delivery is Alertmanager's own Telegram integration on production; the SMTP gateway stays out of this slice

**Context.** Production Alertmanager still runs the chart's stock single receiver with no delivery configuration of any kind; nothing in the repo ever overrode it, and there is no heartbeat alert either. The delivery plan you had written in the DockerImages repo on 2026-08-12 is unimplemented, and triage listed it as related, not in this slice. Its first half is pure configuration: Alertmanager routes to its native Telegram integration, bot token and chat id from OpenBao, loud delivery for critical and silent for warning. Its second half is a new always-on service — an SMTP gateway image that accepts mail from devices that can only send mail (Proxmox disk SMART warnings, say) and posts it into Alertmanager as alerts. The plan leaves open the chat type, a recipient allowlist, whether the Alertmanager UI is exposed, and a dead-man's switch.

**The ask.** The card's complaint is that two Prometheus alerts fired for days and nobody heard: a path from Alertmanager to you.

**Background.** OpenBao holds two Telegram bot tokens today — Jenkins's bot and the Telegram MCP's — and no infra-alerts bot; no mail service exists anywhere in the estate.

**Why yours.** You own the plan that includes the gateway and could want it built whole now.

**Recommendation.** Implement the configuration half only: Telegram receivers in the production Prometheus release, critical loud and warning silent, secret from OpenBao. The gateway stays with the plan for a slice of its own. Trade-off: alerts that exist only as mail — the Proxmox SMART warnings — still reach nobody after this slice; acceptable because the card's complaint is Prometheus alerts, and the gateway is a new always-on service with its own design questions still open.

**The other way.** Build the gateway here too: about two more phases (a new image in DockerImages, a new chart and release), the slice reaches about seven phases — the size you called the sweet spot — and you run one more service.

**If this is wrong.** One more slice later; nothing lost or broken.

**Operator.** Fine.

## D2 — The two stall alerts also require a corroborating memory signal, and a new warning says when a node's stall counter looks wedged

**Context.** The critical and warning node memory-stall alerts were added after the 2026-08-02 srvk8s1 memory-starvation incident; they read the kernel's memory-stall counter. The card had srvk8s3's counter pinned at exactly 1.0 for days. That premise changed shape but holds: all four nodes were rebooted on 2026-09-13 and srvk8s3 is clear, but srvk8s2 ran the same wedge from 2026-09-07 until that reboot — nearly six days, both alerts firing throughout — with about 11 GiB available memory and near-zero major faults, and a stall rate wandering between 0.32 and 0.92, so "exactly 1.0" is no fingerprint. Two wedges in about a month, each days long, each cleared only by a reboot; nothing is firing on production today. Once alerts are delivered, a false alert is a Telegram message.

**The ask.** Alert rules that no longer trust a counter that can wedge — the card's other facet.

**Background.** In the incident, srvk8s1's stall rate rose from 0.012 to 0.175 while major faults ran at 670–770 per second and available memory sat at 0.6–0.9 GiB for the 90 minutes before the kills: stall pressure was the signal that moved, but the other two were already extreme. The wedges showed 5.3 GiB and 2.2 faults per second on srvk8s3, 11 GiB and none on srvk8s2. Not verified: the cause. An upstream kernel report — a stall counter that fails to decrement when a cgroup is deleted mid-stall, on the kernel series these nodes run — fits, but has not been confirmed.

**Why yours.** It trades detection sensitivity against false pages on alerts you built after the incident.

**Recommendation.** Each stall alert fires only when available memory is low or major faults are high as well (thresholds the planner sets from the incident record). A new warning-level alert fires when the stall rate is high while memory is plentiful and faults are near zero for a sustained period, saying the stall alerts on that node are blind until it is rebooted. Trade-off: a genuine node stall that moves neither available memory nor major faults would no longer alert — the one recorded incident moved both — and a single pod thrashing against its own memory limit on an otherwise roomy node no longer raises the node-level alert.

**The other way.** Leave the stall alerts as they are and add only the wedge warning, which mutes them through Alertmanager inhibition once the counter has been stuck for some hours: full sensitivity kept, but every wedge first delivers a false critical to Telegram, and wedges have come about monthly.

**If this is wrong.** A real memory starvation could go unannounced — the failure these alerts exist for; mitigated by the recorded incident having moved both corroborating signals.

**Operator.** I don't know. I have to follow your recommendation. Just implement best practice. If I want it changed, I'll raise a card.

## D3 — Admin rights come from your own account, named in each app's configuration; no Keycloak group

**Context.** Six apps already sign in against the homelab realm; none of them maps a Keycloak group or role to elevated in-app rights, and the realm emits no group claim today — Argo CD's setup had to stop asking for one because requesting it fails the login. The clients this slice hand-makes are to be imported, never recreated, by the later Keycloak-as-code slice. Grafana runs the plain upstream chart with no auth configuration and a stock local admin. pgAdmin runs the repo's own chart: a local admin created from a configured email and password, with one registered Postgres server loaded into that account from a file on every start.

**The ask.** The card's own open question: per app, map a Keycloak group to the elevated role (Grafana Admin, pgAdmin admin), or keep everyone at base and manage rights in-app?

**Background.** Verified in pgAdmin's source: a Keycloak sign-in is keyed by user name and login source, so it creates a separate pgAdmin account — non-admin, empty server list — unless that account is pre-created; the command-line setup can pre-create an external-login account as admin and load the server list into it; and pgAdmin has no way to derive admin rights from token claims. Grafana can derive its role from the token.

**Why yours.** It decides where admin membership is managed — in Keycloak, or in two apps' values.

**Recommendation.** No group and no realm change. Grafana derives the role from the token: your account gets Grafana Admin, any other realm account gets Viewer. pgAdmin pre-creates your Keycloak account as admin at startup, the way the chart already creates its local admin, with the same server list; automatic account creation is off, so no other realm account gets into the database console at all. Trade-off: your identity is written into two apps' values, and adding a second admin is a values change rather than a group membership.

**The other way.** A Keycloak admin group and a group claim on both clients, mapped in Grafana — but pgAdmin cannot use it either way, the realm first needs a group claim that does not break logins, and all of it is more for the Keycloak-as-code slice to import.

**If this is wrong.** Small rework in values; nothing lost.

**Operator.** I do want to ensure that not everyone can login. I see role mappings for my user. I think that's how I've done this. I think that's what I used to even grant a user access to some app. ModernAppTemplate has the logic for this. I don't know if this translates to other apps. Is it maybe smarter if I create a separate realm for infrastructure stuff so that I don't have to worry about this at all?
Ruled in chat, 2026-09-14, after a Keycloak investigation — "do we now just do the planned work and you create an Operator Actions card to decide on the long term changes?", then "Agree" to: Grafana and pgAdmin each require a role on their own Keycloak client to sign in, so an account without it cannot log in; Grafana's admin comes from that role; pgAdmin's client gets a mapper exposing the role, and your account is pre-created as admin with the server list. This replaces the recommendation above. The separate-realm question moved to an Operator Actions card. Also agreed in chat: the Keycloak upgrade (26.5.1 to 26.7.3) joins this slice, with a database backup before it deploys.

## D4 — Each app keeps its local admin and login form as break-glass beside the Keycloak button

**Context.** Both apps are reachable on internal hostnames only. The estate has precedent both ways: open-webui hid its local login form on production once Keycloak worked; Argo CD kept its local admin as break-glass. Keycloak itself is deployed from HelmCharts onto the production cluster — the cluster Grafana and pgAdmin are used to debug — and a values change reaches production through Jenkins, which also runs there.

**The ask.** The card's second open question: once Keycloak sign-in is verified, does each app keep its local admin as fallback?

**Background.** Not verified: that the public sign-in hostname is served by that production release — the recommendation assumes a production-cluster outage takes Keycloak with it.

**Why yours.** A security-posture preference, with precedent on both sides.

**Recommendation.** Keep both local admins and their login forms; Keycloak is an extra login button, no automatic redirect. Trade-off: a password-based way in remains on both apps — acceptable because Keycloak runs on the same production cluster these tools exist to debug, and Grafana is what you open when that cluster misbehaves.

**The other way.** Hide the local login once Keycloak sign-in is verified, as open-webui did: one way in, but a Keycloak outage locks you out of Grafana exactly then, and getting back in is a values change deployed through Jenkins, itself on the cluster.

**If this is wrong.** Reversible with a values change; no data at stake.

**Operator.** Agreed.

## D5 — The Keycloak chart stops the old pod before starting the new one, on every rollout from now on

**Context.** Since the first round you ruled that the Keycloak upgrade, 26.5.1 to 26.7.3, joins this slice as two small phases before the Grafana and pgAdmin work, with a database backup before it deploys. The plan now has six phases — the stall alerts, Telegram delivery, the 26.7.3 image, the Keycloak rollout, Grafana on Keycloak, pgAdmin on Keycloak — and stopped on how that rollout happens. Today the Keycloak chart rolls out by starting the new pod beside the old one and stopping the old one once the new one is ready; and before every node drain, the hand-off playbook restarts Keycloak if its pod is on that node, precisely so the move costs no sign-in outage.

**The ask.** Deploy 26.7.3 to production without running it beside 26.5.1.

**Background.** Keycloak's upgrading guide says the 26.6 migration adds a column older versions do not fill and requires downtime — do not run 26.6 alongside an older version during or after it; rolling updates without downtime are supported only between patch releases of one minor version, and the same release moves the embedded cache to a new major version. As agreed, the rollout would run both versions against the same database while the new pod starts and migrates; the backup makes a failure recoverable, not impossible. Keycloak took about 30 seconds from start to ready at its last production restart. Keycloak's database already stops then starts during the same hand-off, with a documented outage of about that length, so sign-in already blinks when the database's node is drained. Minor releases come several times a year, each a stop-start by upstream's rule.

**Why yours.** It trades a short sign-in outage on every Keycloak rollout, node updates included, against a manual step at push time — a procedure and an availability property you set deliberately.

**Recommendation.** From now on the chart stops the old Keycloak pod before starting the new one, on every rollout: no keystroke at push time, the run stays autonomous, and every later minor upgrade is covered. Trade-off: every Keycloak rollout — a deploy, an image rebuild, the node-update hand-off — becomes a sign-in outage of roughly 30 seconds; apps with a session keep working, but new sign-ins and token fetches in that window fail. The hand-off's zero-downtime move of Keycloak is lost, though sign-in already blinks for the database during node updates.

**The other way.** Keep today's rolling start and make this upgrade a one-off manual stop — immediately before the push that deploys 26.7.3 you scale Keycloak to zero and the deploy brings it back on the new version. The run then cannot push HelmCharts on its own, so its live checks of the alerting, Grafana and pgAdmin work wait for your push, and the next minor upgrade needs the same manual step.

**If this is wrong.** An outage of about 30 seconds per node update that you would rather not have — reversible by switching the chart back; nothing lost.

**Operator.** Agreed

## D6 — The dev-cluster copies of Grafana and pgAdmin stay on their local login; only production moves to Keycloak

**Context.** The first round settled that Grafana and pgAdmin move to Keycloak on both clusters, the dev copies on the dev Keycloak's dev realm with internal hostnames as their sign-in return addresses — four clients and four secrets. The plan is drafted on that: its pre-run checklist's two dev return addresses and the dev Grafana's fixed address wait on the answer here. The dev copies have no internal hostname. Dev-cluster services are reached on addresses handed out from the dev network pool, and the dev copies of the apps already on Keycloak register exactly that bare address; those addresses are not pinned — only the database and the DNS service pin theirs.

**The ask.** The address each dev copy registers with Keycloak — or whether they register at all.

**Background.** Grafana needs its address fixed in its settings to build the sign-in return address; pgAdmin works it out from the request. The dev cluster's VM is not running today, so the two addresses cannot be read, and nothing in the run can verify a dev-cluster change: production deploys go through Jenkins, and the dev cluster is not in that path. The dev cluster is for chart development and is disposable by design. The dev realm is separate from the production realm your friend is in; not verified: that he has no dev-realm account.

**Why yours.** It reverses a settled item you saw, and turns on how far you want the dev cluster to mirror production.

**Recommendation.** The dev copies keep their local login; only production's Grafana and pgAdmin move to Keycloak — two clients and two secrets instead of four, and no addresses to find. Trade-off: the dev copies no longer exercise the Keycloak sign-in path, so a chart change to it is first seen working on production.

**The other way.** Keep the dev copies on the dev realm at their current pool addresses, which you look up once the dev VM is running and give before the run; the addresses can change on reinstall, and dev sign-in then breaks until the client and settings are updated. Pinning the addresses instead adds work to two phases.

**If this is wrong.** The dev copies can be moved to Keycloak later in a small change; nothing lost.

**Operator.** Agree

## Open facts — questions only you can answer

**F1.** Besides you, who has an account in the homelab realm, and should any of them reach Grafana or pgAdmin? (Settles whether D3's "others get Viewer, nobody else reaches pgAdmin" matters.)

**Operator.** A friend. He should not have access to infrastructure stuff.

**F2.** Which Telegram bot should deliver the alerts, and into which chat? OpenBao holds Jenkins's and the Telegram MCP's bot tokens today and no alerts bot. (Settles your keystrokes before the run and the secret delivery reads.)

**Operator.** A new one.

**F3.** Is the dev cluster's VM off on purpose, and does it stay off for now? (Settles whether D6's alternative is workable before the run, and whether anything dev-side can be checked at all.)

**Operator.** It is because of memory conservation. Additional memory is in the mail :). You can (request to) turn it on if you need it.

## Settled

- Delivery covers the production cluster's Alertmanager only; the dev cluster's Prometheus does not carry these alert rules and stays undelivered.
- No dead-man's switch in this slice — a heartbeat that says the alert path itself is dead needs something outside the cluster to watch it, and the delivery plan leaves it open.
- The suspected kernel bug is not chased here — no kernel change; the wedge warning names the node to reboot.
- Grafana and pgAdmin move to Keycloak on both clusters, like the six apps, with the dev-cluster copies on the dev Keycloak's own realm — four clients and four OpenBao secrets, not two.
- Your keystrokes come before the run starts, from a list the plan spells out exactly — the Telegram bot and chat and their OpenBao secret, the four Keycloak clients with internal hostnames as redirect addresses, the four client secrets in OpenBao — because a release whose external secret points at a path that does not exist yet fails to start when the run's push deploys it.
- Size: about five phases, all in HelmCharts — Telegram delivery, the stall-alert change, Grafana on Keycloak, pgAdmin on Keycloak, and possibly a doctrine note in AnsibleSpecs; the gateway would make it about seven and add DockerImages plus a new chart and release.
