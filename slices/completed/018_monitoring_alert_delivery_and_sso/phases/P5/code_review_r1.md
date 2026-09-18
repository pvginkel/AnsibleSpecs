# P5 code review — round 1

**Readiness.** P5 can merge. I found one advisory issue and nothing blocking. The diff (HelmCharts `01532e9..aa875f7`) delivers what the phase set out to do. Production Grafana gets a generic-OAuth "Keycloak" button against the `homelab` realm, and the local form stays: there is no `auto_login` and no `disable_login_form`. Only an access token whose `resource_access.grafana.roles` holds `admin` produces a role, and that role is Grafana Admin. With `role_attribute_strict` on, every other account is refused. The client id and secret reach Grafana only as `GF_AUTH_GENERIC_OAUTH_*` values from a new `grafana-oidc` ExternalSecret (`eso/prd/grafana/prd/oidc`). The dev release is untouched.

I checked the design's central claim against Grafana 12.3.1's source, which is the image running live (`docker.io/grafana/grafana:12.3.1`, chart `grafana-10.5.15`):
- `collectUserInfoData` reads the ID token, then userinfo, then the access token (`pkg/login/social/connectors/generic_oauth.go:275-289`).
- `extractRoleAndOrgs` only logs a warning when one source yields no role (`:333-342`).
- `postProcessUserInfo` refuses the login under strict mode when no source maps a role (`:374-378`).

So the role-less ID token and userinfo produce the expected warnings, and the gate rests on the access token as the plan says.

`poetry run deploy template prd/grafana` renders `envFrom: secretRef: grafana-oidc` and the `[auth.generic_oauth]` / `[server] root_url` ini as intended. The ExternalSecret matches the live shape: namespace `grafana-prd`, store `openbao-prd`, key format as in the live `dnsmasq-oidc`. The deploy CLI runs `helm upgrade` without `--wait` and applies `manifests.yaml` afterwards (`tools/deploy/deploy_cli/helmops.py:196-203`). On the first deploy, the new pod therefore waits on the Secret, not the deploy on the pod. Under the chart's RollingUpdate, the old pod keeps serving until then.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high
**Keycloak sign-in started on the `grafana` short name fails on the first try.**

The release still serves Grafana as both `grafana.home` and `grafana`. `configs/prd/grafana/prd/values.yaml:6` sets `server-name: grafana.home, grafana`, and `charts/grafana/architecture.yaml:7-10` lists both as entrypoints. But `values.yaml:22` pins `root_url: http://grafana.home/`, and Grafana builds the OAuth `redirect_uri` from that.

The failure happens like this:
1. Grafana saves the OAuth state in a host-only `oauth_state` cookie (Grafana 12.3.1 `pkg/middleware/cookies/cookies.go` sets no `Domain`).
2. A user who opens `http://grafana/` and clicks Keycloak gets that cookie on host `grafana`.
3. Keycloak then returns the user to `grafana.home`.
4. At the callback there is no state cookie, so the login fails with "Missing saved oauth state" (`pkg/services/authn/clients/oauth.go:115-117`).

A retry from `grafana.home` works. This edge case is outside the plan, which names `grafana.home` as the registered address. The local login form still works on both names.

## Not findings (checked)

- The test pins the exact role path, the strict flag, `allow_assign_grafana_admin`, no auto-login and no disabled login form. It also pins `root_url`, the ExternalSecret-to-`envFromSecret` wiring and the untouched dev release. That covers the phase's static share of V02, V09, V11 and V12; the live parts of those criteria belong to the test phase.
- `use_pkce`, `use_refresh_token`, `scopes` and `login_attribute_path` are not pinned. None of them is an acceptance criterion.
- No other OIDC app's `architecture.yaml` models a Keycloak dependency, so leaving `charts/grafana/architecture.yaml` alone is consistent with the others.
