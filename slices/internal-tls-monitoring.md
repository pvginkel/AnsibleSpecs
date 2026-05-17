# Internal TLS via step-ca — cert-expiry monitoring (§J)

The §J monitoring deliverables that live **outside the Ansible repo**.
The VM-side metric already ships in the `internal_tls` role; this doc
covers the two operator-delivered pieces:

1. the **Prometheus alert rule** — HelmCharts `prometheus`;
2. the **in-cluster cert-expiry metric** — DockerImages
   `nginx-configurator` + HelmCharts `nginx`.

Parent slice: [`internal-tls-step-ca.md`](internal-tls-step-ca.md) §J.
In-cluster cert mechanics:
[`internal-tls-nginx-configurator.md`](internal-tls-nginx-configurator.md).

## The metric — `internal_tls_cert_not_after_seconds`

A Prometheus gauge: the leaf's **absolute not-after time**, in unix
seconds. One series per managed certificate. Labels: `common_name`
(the leaf's CN / first SAN) and `cert_path`. Same metric name and
semantics on both issuance paths, so a single alert rule covers
everything.

**Absolute timestamp, not "seconds remaining"** — the value is correct
without being continuously rewritten. Prometheus derives remaining
validity at query time as `internal_tls_cert_not_after_seconds - time()`.
A "seconds remaining" value, by contrast, would freeze at the moment it
was written and never approach the alert threshold — the textfile/metric
is only refreshed when the producer runs, not on every scrape.

### VM side — done

The `internal_tls` role (`tasks/metric.yml`) writes
`/var/lib/prometheus/node-exporter/internal_tls_<cn>.prom` on every run,
one file per cert. It is scraped by the existing `homelab-nodes` job in
`configs/prd/prometheus-values.yaml` (node-exporter `:9100` on
pve/pve1/pve2/srviac/wrkdev). No HelmCharts change is needed for the VM
metric to appear — only the alert rule below.

## Piece 1 — Prometheus alert rule (HelmCharts)

Add a `serverFiles` alerting rule to `configs/prd/prometheus-values.yaml`
(the prometheus-community chart loads `serverFiles."alerting_rules.yml"`
into Prometheus's `rule_files`):

```yaml
serverFiles:
  alerting_rules.yml:
    groups:
      - name: internal-tls
        rules:
          - alert: InternalTLSCertExpiringSoon
            expr: internal_tls_cert_not_after_seconds - time() < 10 * 86400
            for: 1h
            labels:
              severity: warning
            annotations:
              summary: >-
                Homelab TLS leaf {{ $labels.common_name }} expires in
                under 10 days
              description: >-
                {{ $labels.cert_path }} on {{ $labels.instance }} has
                {{ $value | humanizeDuration }} of validity left. The
                renewer (internal_tls role for VMs, certificate-renewer
                CronJob in-cluster) has not re-issued it.
```

**Threshold — 10 days.** Below the role's 14-day VM renewal threshold
*and* below the in-cluster monthly path's ~17-day steady-state floor, so
a healthy renewer on either path never trips it; it fires only on a
genuinely stalled renewer, with ~10 days of runway left. An earlier
draft used `< 17 * 86400`; 17 > 14 would put the alert in a permanent
3-day flap every VM renewal cycle.

`for: 1h` rides out a transient scrape gap or a momentarily unreadable
textfile — the underlying condition is monotonic once true, so the
duration is only glitch-suppression.

**Values files are not Go-templated by Helm**, so the Prometheus `{{ }}`
label refs above are safe as-is. If the HelmCharts deploy harness does
any `{{ }}` preprocessing on values files, escape them accordingly.

Mirror into `configs/dev/prometheus-values.yaml` only if dev symmetry is
wanted — the `homelab-nodes` job is prd-only, so on dev the rule would
match in-cluster series alone.

## Piece 2 — in-cluster cert-expiry metric

In-cluster leaves are certbot files at
`<SSL_CERTIFICATES_TARGET>/<name>/fullchain.pem`, re-issued by the
monthly `certificate-renewer`. No node-exporter textfile collector
reaches them, so emit the metric from **`nginx-configurator`** — it
already mounts the cert directory and already tracks every managed
entry (`self.entries` + `self.external_services`).

### nginx-configurator change (DockerImages)

In `nginx-configurator/app/`:

- Start a small **metrics HTTP server on a background thread** (e.g.
  `:9090`, path `/metrics`) alongside the existing watch loop.
- On each scrape, for every entry with `is_public` or `enable_ssl`:
  read `<SSL_CERTIFICATES_TARGET>/<server_names[0]>/fullchain.pem`,
  parse `notAfter`, emit
  `internal_tls_cert_not_after_seconds{common_name=…,cert_path=…}`.
  **Skip** entries whose cert file does not exist yet (not-yet-issued)
  rather than emitting `0` — a `0` would read as "expired" and alert.
- Parse with the `cryptography` library
  (`load_pem_x509_certificate(...).not_valid_after_utc.timestamp()`);
  add `cryptography` to the image's `pip install` (today: `kubernetes
  jinja2 requests`). Use `prometheus_client` for the endpoint, or
  hand-roll the exposition text — it is a single gauge.
- Reading at scrape time means the value tracks the monthly renewals
  with no extra plumbing — the configurator does not need to be
  notified when `certificate-renewer` rotates a leaf.

**Scope.** Internal (`enable_ssl`) certs are the §J requirement.
Emitting for public (`is_public`) certs as well is the same code path
and free — it gives Let's Encrypt expiry coverage too. Operator's call;
not required by §J.

### nginx chart change (HelmCharts `charts/nginx`)

- Expose the metrics port on the nginx-configurator (`nginxmanager`)
  Deployment + Service.
- Annotate the `nginxmanager` pod so Prometheus's built-in
  `kubernetes-pods` scrape job picks it up:
  `prometheus.io/scrape: "true"`, `prometheus.io/port: "9090"`,
  `prometheus.io/path: "/metrics"`. The prometheus-community chart ships
  that job by default and honours these annotations — no
  `extraScrapeConfigs` entry is needed.

### Alert

The `InternalTLSCertExpiringSoon` rule from Piece 1 already covers the
in-cluster series — identical metric name, and 10 days is below the
monthly path's ~17-day floor. **No second rule.** The `instance` label
distinguishes a node (VM path) from the configurator pod (in-cluster)
in alert output.

If `certificate-renewer` stays monthly: one fully-missed run leaves
~17 days, the alert then fires ~7 days later with ~10 days of runway —
adequate, but tight. The nginx-configurator design doc already flags
moving that CronJob to fortnightly; if it moves, the floor rises and the
10-day threshold gains margin.

## Verification

- **VM**: `curl -s pve.home:9100/metrics | grep internal_tls_cert` —
  one series per pveproxy leaf, value ~47 days in the future.
- **In-cluster**: `curl` the nginx-configurator metrics endpoint — one
  series per `enable-ssl` service.
- **Alert**: in the Prometheus UI, `internal_tls_cert_not_after_seconds
  - time()` reads ~4e6 (≈47 d) and `InternalTLSCertExpiringSoon` is not
  firing. Temporarily raise the threshold (e.g. `< 60 * 86400`) to
  confirm it can fire and clears when reverted.

## Out of scope

- **Alertmanager delivery.** `prometheus-values.yaml` configures
  Alertmanager persistence but no receiver/routing — the alert is
  visible in the Prometheus/Alertmanager UI but is not delivered
  anywhere until a receiver is added. Separate follow-up.
- **Public-cert expiry** — covered for free if the operator opts to emit
  `is_public` entries (above), but not a §J requirement.
