# Telegram IaC bot — cluster messaging hub, dead-man's switch, report rendering

**One line:** A new, dedicated Telegram bot container ("the IaC bot") that becomes the
single notification/health funnel for the whole estate: in-cluster message API, dead-man's
switch (only this bot calls out to healthchecks.io), rendered-report delivery, and the
retirement of `send_message.py`.

Triage source: 2026-07 IaC review finding S1 (`../../reviews/2026-07-iac-review/
findings.md`) + operator's spec in chat, 2026-07-03. Nothing like this exists today.

## Operator's spec (verbatim intent)

- Dedicated namespace.
- An API that allows apps in the cluster to send messages. Best case: a **Terraform
  resource allocates credentials** (HomelabTerraformProvider pattern, like
  `homelab_backup_credential`).
- Messages can contain **text, an image, or a URL to render an image from** (the bot
  renders the URL — headless browser — and sends the screenshot/PNG; Telegram displays
  photos inline, HTML attachments are dead weight on a phone).
- **Dead-man's-switch mechanism**: jobs/backups register a heartbeat; if the ping doesn't
  arrive, the bot alerts. The bot itself is the only component that calls out to
  **healthchecks.io** — it is the health ping for the whole cluster; everything else
  funnels through this container. A dead-man switch registration is a candidate TF
  resource.
- Possibly **scheduled triggers** that send daily reports or alerts.
- Possibly integrated with **Prometheus Alertmanager** as a notification channel.
- Push model first (broadcast this report); a pull model (interval + on-demand "give me
  the current version of dashboard X" via bot command) is a possible later evolution —
  in chat the operator and Claude agreed v1 is push-only, on-demand comes when a second
  subscriber exists.

## What it replaces / relates to

- **Replaces `send_message.py`** (IaCAgent → Home Assistant push). Operator: "I need to
  get rid of send_message.py. I want this moved into a Telegram bot." Alerting then still
  originates in-cluster — k8s prd dying still means silence from in-cluster senders — the
  operator explicitly accepts that ("Yes, alerting then still comes from the cluster. I
  can live with that."). The healthchecks.io dead-man leg is what covers the
  platform-down case: silence toward healthchecks.io becomes the alarm.
- **The Jenkins-chart telegram bot is a different thing**: Jenkins-specific, informative
  only, not load-bearing. The IaC bot could *eventually* replace it (then only sending
  failed jobs), but that is not v1 scope.
- **Consumers queued in other bundles**: trivy scan reports (`../ci_quality_gates/`),
  update-train run reports (`../update_train_system/`), non-rotatable-secret instruction
  messages (`../secrets_remediation/`), and the review's suggestion of a
  "destroys > 0" plan notification (`../tf_safety_rails/`).
- **Existing context**: the operator has an ePaper desk dashboard (high-level cluster
  status + recent failed Jenkins pipelines and k8s jobs) and an IoT-support rotation
  dashboard for device keys that is "nice" but never looked at — the lesson driving this
  design: dashboards you must visit don't get visited; reports that arrive in Telegram do.
  If URL-render-to-Telegram works here, the rotation dashboard becomes a second feed.

## Review finding S1 (abstract)

Both current notification paths depend on the platform they report on: `send_message.py`
fires from Jenkins post-stages (Jenkins runs on k8s prd) via Home Assistant; the telegram
sidecar lives inside the Jenkins chart. k8s prd dying is indistinguishable from "nothing
happened". `Jenkinsfile.iac-image` and the architecture pipelines have no failure
notification at all. The review recommended an external dead-man's switch pinged on
*success* by the scheduled jobs (drift, update, backups) so absence alerts out-of-band —
the operator's answer is this bot as the funnel, with healthchecks.io as the only external
leg. (The two S1 sub-items the operator dispositioned separately: cron schedules stay
Jenkins-managed — parked on Later; the Scheduled-Update failure streak — parked on Later.)

## Q&A / notes for the slice writer

- Repo landing spots: bot image in DockerImages; chart in HelmCharts (dedicated
  namespace); credential/dead-man TF resources in HomelabTerraformProvider;
  `send_message.py` retirement touches IaCAgent + the `Jenkinsfile.iac-*` post stages in
  Ansible. Ansible-led (cross-repo).
- URL-render needs headless Chromium in the container (or a sidecar) — the render-service
  is a generically useful primitive; keep it inside this bot rather than a separate
  service until a second consumer demands otherwise.
- Telegram bot-token + healthchecks.io credentials via OpenBao + ESO, per estate pattern.
