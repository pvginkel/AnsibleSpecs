# Turn on Keycloak OIDC login for the apps that can take it

**Slice 004.** Scope agreed with the operator: **Grafana, pgAdmin, Headlamp,
Jenkins** (LibreChat and Terminus dropped). Live status tracks on the Kanban
`[004]` card.

## Goal

Put the remaining web UIs behind the homelab Keycloak (`homelab` realm at
`https://auth.ginbov.nl/realms/homelab`) instead of their app-local logins,
the way `dnsmasq` / `electronics-inventory` / `iot` / `guacamole` /
`open-webui` / `zigbee2mqtt` / `design-assistant` / `calendar-support` already
are. Same conventions as those: per-app confidential Keycloak client, secret
in OpenBao at `eso/<cluster>/<app>/<stage>/oidc` (`client_id` + `client_secret`),
materialised into the namespace by ESO, OIDC config in the chart/release values.

**Constraint the operator set:** only enable an app where the configuration sits
**comfortably in the chart/release values**. Where the natural path is in-app or
cluster-side, *say so and stop* — don't force a chart-side hack. Two of the four
land that way; see per-app notes.

## Scope

Four apps, in two tiers:

### Clean chart-side wins

- **Grafana** (`charts/grafana`, upstream `grafana/grafana`). Native
  `auth.generic_oauth`.
- **pgAdmin** (`charts/pgadmin`, in-repo, `dpage/pgadmin4`). Native OAuth2 via a
  `config_local.py`.

### Enable, but the real work is *not* chart-side (the "make a note" items)

- **Headlamp** (`charts/headlamp`, upstream `headlamp/headlamp`). The chart can
  set the OIDC flags, **but** Headlamp forwards the id_token straight to the
  kube-apiserver — so it only authorises if **microk8s' apiserver trusts the
  Keycloak issuer** (`--oidc-issuer-url` + `--oidc-client-id`, RBAC mapped to a
  Keycloak group/claim). That is an AnsibleSpecs/microk8s change, not a chart
  change. Today Headlamp logs in with a static `admin-user` ServiceAccount token
  pasted into the form (see `configs/{dev,prd}/headlamp/.../values.yaml`).
- **Jenkins** (`charts/jenkins`, in-repo `jenkins:lts-jdk21`). The chart has **no
  JCasC / security-realm surface** (no `casc`/`jenkins.yaml` anywhere in it), so
  there is no comfortable chart-side path. The natural way is **in-app**: install
  the `oic-auth` plugin and configure the OIDC security realm under *Manage
  Jenkins → Security*, pointed at the `homelab` realm. **Note to self: do Jenkins
  in-app via `oic-auth`** — do not bolt a half-JCasC config into the chart for
  this. (If we ever add a proper JCasC config surface to the Jenkins chart, fold
  the realm in then; that's a separate decision, not this slice.)

### Explicitly out of scope

- **LibreChat** — dropped by the operator.
- **Terminus** — in-house Rails app (`registry:5000/terminus`); OIDC there is an
  app-code change in `../DockerImages`, not config here. Dropped.
- **Prometheus** — upstream, no native login; would need an `oauth2-proxy`
  sidecar (different shape of work).
- **phpmyadmin** — no usable OIDC.

## Per-app design

### Grafana — `configs/<cluster>/grafana/<stage>/values.yaml`

Pure values passthrough into the upstream chart:

```yaml
grafana.ini:
  server:
    root_url: https://grafana.home/      # exact value of the exposed host; drives the redirect URI
  auth.generic_oauth:
    enabled: true
    name: Keycloak
    client_id: grafana
    client_secret: $__file{/etc/secrets/oidc/client_secret}
    scopes: openid profile email
    auth_url:  https://auth.ginbov.nl/realms/homelab/protocol/openid-connect/auth
    token_url: https://auth.ginbov.nl/realms/homelab/protocol/openid-connect/token
    api_url:   https://auth.ginbov.nl/realms/homelab/protocol/openid-connect/userinfo
    # role_attribute_path / allowed groups: decide whether to map a Keycloak
    # group to Grafana Admin or leave everyone Viewer (operator call).

extraSecretMounts:
  - name: grafana-oidc
    secretName: grafana-oidc
    mountPath: /etc/secrets/oidc
    readOnly: true
```

Secret: Grafana is an **upstream chart with no in-repo templates**, so the
`ExternalSecret` that creates `grafana-oidc` is added through the release's
`manifests.yaml` (the harness applies it right after `helm upgrade`), not a
chart template. Mirror the ESO shape the in-repo charts use.

### pgAdmin — `charts/pgadmin` (chart change) + release values

pgAdmin reads `config_local.py` on startup. Add `charts/pgadmin/files/config_local.py`
(picked up by the existing `files/**` glob ConfigMap) and mount it at
`/pgadmin4/config_local.py` (subPath, exactly like `servers.json` is mounted
today in `pgadmin-deployment.yaml`):

```python
import os
AUTHENTICATION_SOURCES = ['oauth2', 'internal']
OAUTH2_AUTO_CREATE_USER = True
OAUTH2_CONFIG = [{
    'OAUTH2_NAME': 'keycloak',
    'OAUTH2_DISPLAY_NAME': 'Keycloak',
    'OAUTH2_CLIENT_ID': 'pgadmin',
    'OAUTH2_CLIENT_SECRET': os.environ['OAUTH2_CLIENT_SECRET'],
    'OAUTH2_SERVER_METADATA_URL':
        'https://auth.ginbov.nl/realms/homelab/.well-known/openid-configuration',
    'OAUTH2_SCOPE': 'openid email profile',
    'OAUTH2_ICON': 'fa-key',
    'OAUTH2_BUTTON_COLOR': '#3253a8',
}]
```

The client secret stays out of the (non-secret) ConfigMap: add an `oidc`
entry to the chart's `externalSecrets.secrets` (shared `shared.externalsecrets`
helper, already wired) and inject it into the `pgadmin-app` container as
`OAUTH2_CLIENT_SECRET` via `secretKeyRef`. `config_local.py` reads it from the
environment. This keeps everything chart-side and comfortable.

### Headlamp — chart values *plus* an apiserver prerequisite

Chart side (upstream chart values, `config.oidc`):

```yaml
config:
  oidc:
    clientID: headlamp
    issuerURL: https://auth.ginbov.nl/realms/homelab
    scopes: openid,profile,email
    secret: headlamp-oidc        # existing Secret with client_id/client_secret, via manifests.yaml ExternalSecret
```

**But this does nothing useful until** the microk8s apiserver trusts the issuer
(`--oidc-issuer-url=https://auth.ginbov.nl/realms/homelab`, `--oidc-client-id=headlamp`,
a username/groups claim) and RBAC binds the mapped Keycloak group. That flag +
RBAC work is an AnsibleSpecs/microk8s change and is the real gate here — do it
there first, then flip the chart values. If we don't want to touch the
apiserver, **leave Headlamp on its current static-token login** and close it out
of this slice.

### Jenkins — in-app, not chart (see Scope note)

No chart change. Operator task in the running Jenkins:
1. Install the `oic-auth` plugin.
2. Configure the OIDC security realm against the `homelab` realm
   (`https://auth.ginbov.nl/realms/homelab`), client `jenkins`, with the
   well-known config endpoint.
3. Keep an in-process emergency admin until the realm is verified.

Tracked here so it isn't forgotten; the chart stays untouched.

## Shared prerequisites (per app, until [keycloak-tf](keycloak-tf.md) lands)

Keycloak clients are still created **by hand** (`keycloak-tf` is a placeholder).
For each app, before deploying:

1. Create a confidential client in the `homelab` realm (and `homelab-dev` on the
   dev cluster), client id = app name (`grafana`, `pgadmin`, `headlamp`,
   `jenkins`). Redirect URIs use the app's existing **internal `.home` host**
   (these four are all `nginx.webathome.org/is-public: 'false'`), e.g.
   `https://grafana.home/login/generic_oauth`,
   `https://pgadmin.home/oauth2/authorize`, etc. — exact callback path per app.
2. Put `client_id` + `client_secret` in OpenBao at `eso/<cluster>/<app>/<stage>/oidc`.
3. Wire ESO: in-repo charts (pgAdmin) via `externalSecrets.secrets` values;
   upstream charts (Grafana, Headlamp) via the release's `manifests.yaml`
   `ExternalSecret`.

## Depends on

- [`helm-tf-deploy-harness`](completed/helm-tf-deploy-harness.md) — the
  release `values.yaml` / `manifests.yaml` mechanism and ESO wiring (done).
- [`keycloak-tf`](keycloak-tf.md) — *not* a hard dependency; this slice creates
  the clients by hand. When `keycloak-tf` lands it should adopt these four
  clients (import, never recreate) so they stop being hand-managed.

## Open questions

- **Role mapping.** For each app, do we map a Keycloak group to an elevated role
  (Grafana Admin, pgAdmin admin) or keep everyone at a base role and manage
  in-app? Decide per app before enabling.
- **Headlamp:** are we willing to put OIDC on the microk8s apiserver? If not,
  Headlamp drops from the slice.
- **Local-login fallback.** Keep each app's local admin enabled (Grafana admin,
  pgAdmin `PGADMIN_DEFAULT_EMAIL`, Jenkins emergency admin) until the OIDC path
  is verified, then decide whether to disable it.

## Verification

Per app, after enabling: the login page offers the Keycloak button, a homelab
account completes the round-trip and lands authenticated, and the local-login
fallback still works. For Headlamp specifically, confirm the forwarded token is
*accepted by the apiserver* (not just that Headlamp's UI logs in) before
declaring it done.

## Caveats

- Two of the four (Headlamp, Jenkins) are **not chart-only** — that's by design,
  recorded so the chart doesn't get a forced-fit config. Grafana and pgAdmin are
  the genuine chart-side wins.
- Clients are hand-created until `keycloak-tf`; track them so that slice can
  import rather than recreate.
- Redirect URIs are the **internal `.home` hostnames**, even though the IdP is
  the public `auth.ginbov.nl` — register those exact hosts on each client.
