# Slice 020 — plan questions, round 1

Both questions come from checking the refinement's "the chart gate lands green today" against the real charts on 2026-09-15: helm v4.3.0 lint and render of every prd release with its `configs/prd/<chart>/prd/values.yaml` and `global.environment=prd` (without post-renderers or digest `--set`s), then kubeconform v0.8.0 against the 1.35.0 schemas, missing schemas ignored. Each "A" answer overturns part of the settled line "no prd release is redeployed just to satisfy the gate", so they are yours to rule on. P4 carries both as open. The rest of the plan does not depend on them.

## Q1 — `storage` fails `helm lint` with its prd values too: fix its template, or leave it?

**At stake.** The refinement settled that the `media`, `mosquitto` and `storage` lint failures only happen with chart defaults and are left alone. `media` and `mosquitto` do pass lint with their prd values. `storage` does not:
`templates/storage-cronjobs.yaml: unable to parse YAML: invalid Yaml document separator: apiVersion: batch/v1`.
Values have nothing to do with it. The `range` in `charts/storage/templates/storage-cronjobs.yaml:1-56` emits `---`, and whitespace trimming joins the next CronJob's `apiVersion` onto that separator line. `helm template`/`upgrade` split that leniently, which is why it deploys. `helm lint` rejects it.

The gate hits `storage` whenever the build is about to deploy it:
- when its chart or config changes;
- when the shared Terraform surface changes: `terraform-modules/` or `_providers/` selects every release (`HelmCharts/Jenkinsfile:94-101`);
- when the live digest of any of its four DockerImages images moves (`debian`, `rclone-backup`, `samba`, `backup-server`; `charts/storage/values.yaml:53-57`; `Jenkinsfile:74`). Those images carry the 7-day rebuild stamp that version-poller acts on (`JenkinsPipelineUtils/vars/helmCharts.groovy:90`).

**Options.**
- **A. Fix the separator in P4.** The rendered objects don't change, but the push redeploys `storage` in prd once. The chart stamps a render-time `deployment` annotation (`charts/shared/_helpers.tpl:1-3`) into `storage-deployment.yaml` and `backup-server-deployment.yaml`, so their pods restart, as they do on every storage deploy.
- **B. Leave `storage` alone.** The gate goes red the first time a build is about to deploy `storage`, most likely on the next rebuild of one of its images. A red gate fails the whole build, so that build deploys nothing, including every other release it selected. It stays red until someone fixes the template.

**Recommendation: A.** B doesn't avoid the storage redeploy; it only moves it to an unattended build, where it also blocks every other deploy. A takes the same one-time pod restart at a push the run is watching.

## Q2 — kubeconform in strict mode (rejects unknown fields and duplicate keys), or default mode?

**At stake.** The ruling pins kubeconform to Kubernetes 1.35 but says nothing about strictness. That choice decides whether the gate lands green without touching another chart.
- **Default mode:** all 43 rendered prd releases pass (341 resources valid, 96 custom resources skipped).
- **Strict mode:** one fails. `homeassistant-mcp`'s Deployment sets `command:` twice (`charts/homeassistant-mcp/templates/app-deployment.yaml:21-22`). The live container (namespace `homeassistant-mcp-prd`, read from prd) runs the second one, `["ha-mcp-web"]`.

**Options.**
- **A. Strict, and delete the dead first `command:` line in P4.** The gate then also rejects Kubernetes fields a template misspells or puts at the wrong level: the wrong-key class, caught in rendered manifests instead of values. The live command stays the same. The push redeploys `homeassistant-mcp` once, and its pod restarts because it stamps the same render-time annotation.
- **B. Default mode.** Lands green with no chart change. The gate does not flag a misspelled or misplaced Kubernetes field in a template.

**Recommendation: A.** You wanted the chart gate to catch wrong keys before prd, and strict mode is what does that for rendered manifests. The cost is one restart of an MCP server whose effective config doesn't change.
