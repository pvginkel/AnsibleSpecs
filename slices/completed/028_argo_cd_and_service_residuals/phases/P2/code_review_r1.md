# Code review r1: slice 028, P2 (ArgoCDDeploy `bcedb86..23ecda8`)

**Readiness: ready to merge.** The phase delivers everything it set out to do.

- **Metrics Service.** `argocd-prd-application-controller-metrics` renders on port 8082 → `metrics` and selects the controller pod. It carries `prometheus.io/scrape: "true"`. The live `kubernetes-service-endpoints` job keeps a Service on that annotation alone: it uses endpointslice SD with `honor_labels: true`, keeps on `__meta_kubernetes_service_annotation_prometheus_io_scrape`, and labelmaps the Service labels (read from the `prometheus-prd-server` ConfigMap). So P3 owes no scrape.
- **Network access.** Prometheus's namespace has no NetworkPolicy. The chart's controller NetworkPolicy admits `metrics` from `namespaceSelector: {}`.
- **SyncError flag.** `--metrics-application-conditions=SyncError` reaches the controller args. The flag name and form match upstream v3.5.1 (`cmd/argocd-application-controller/commands/argocd_application_controller.go:286`, `StringSliceVar`). The series labels the done-record lists match `controller/metrics/metrics.go:60,65-69,177-183`.
- **Short-host login.** argocd-cm keeps `url: https://argocd.home` and gains `additionalUrls: ["https://argocd"]`. Upstream accepts a `return_url` against that list (`util/oidc/oidc.go:387-426,449`). It picks the callback from `r.Host` (`util/settings/settings.go:2301-2323`), and nginx forwards `Host $host` (`NginxDeploy/chart/files/snippets/proxy.conf:3`). So a login at `https://argocd/` gets the `https://argocd/auth/callback` redirect.
- **Comments and templates.** The D7 comment is rewritten and accurate. The event templates and triggers are untouched.
- **The gate's new assertions are not vacuous.** 22 mutations were run against a scratch copy: 14 of values, 8 of the render. Every one that should fail the gate did: removed or wrong condition, missing annotation, metrics disabled, wrong port or path annotation, missing/http/sub-path/scalar `additionalUrls`, a moved `domain`, a new vhost alias, a NetworkPolicy that refuses the metrics port, a wrong Service selector or targetPort, and a missing `--metrics-port`. Three passed:
  - the split `--flag value` arg form, correctly;
  - NetworkPolicies turned off, correctly;
  - a Service with no ports, which Kubernetes would reject anyway.
- **Lint.** `kc project lint` is green on `23ecda8`.

What remains are two advisory inaccuracies in the done-record.

## F1: Minor · advisory · anchor: none · confidence: high

**The done-record understates when SyncError is set.** It tells P3 that "the controller sets it only on the auto-sync path, once the operation has completed failed (retries spent) and it declines to re-sync that revision" (`plan.md`, P2 `Later phases:`). Upstream v3.5.1 also sets `SyncError` on the auto-sync path in two more cases, with no failed sync behind either:

- **The prune guard** (`controller/appcontroller.go:2431-2441`, "auto-sync will wipe out all resources"). It is active for every generated app: `chart/templates/applicationsets.yaml:51` sets `prune: true`, and no `allowEmpty` is set.
- **A failed `SetAppOperation`** (`controller/appcontroller.go:2458-2460`).

In both cases the app stays OutOfSync with no operation running, so P3's standing failed-sync alert will fire on them. That is arguably right, since both are stuck apps. But alert text written from the record ("retries spent", "failed sync") would misdescribe them. The fact is recorded under P2's Record for P3.

## F2: Minor · advisory · anchor: none · confidence: high

**The done-record says "the architecture artifact is unchanged", and it did change.** The artifact is regenerated at base `bcedb86` and at `23ecda8`. The HEAD version gains `if:argocd-prd-application-controller-metrics-argocd-prd-svc` and its `rel:…-behind-…-metrics-argocd-prd-svc` relation. There is no product consequence:

- the artifact is gitignored build output (`.gitignore:5`);
- `architecture.yaml` needs no change;
- `arch-validate` passes.
