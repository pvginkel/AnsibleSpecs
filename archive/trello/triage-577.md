# Jenkins OIDC login via oic-auth (in-app, no chart change)

## 📋 List: Operator Actions

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `yellow` Chore

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Operator task in the running Jenkins, filed here so it is not forgotten — move it to Operator Actions if you would rather work it there.

The Jenkins chart has no JCasC / security-realm surface (no casc or jenkins.yaml anywhere in it), so there is no comfortable chart-side path and we deliberately do not want a half-JCasC config bolted in for this. The natural route is in-app:

1. Install the `oic-auth` plugin.
2. Configure the OIDC security realm against the `homelab` realm (https://auth.ginbov.nl/realms/homelab), client `jenkins`, via the well-known config endpoint.
3. Keep an in-process emergency admin until the realm is verified.

Needs a `jenkins` confidential client in the realm and its secret, same convention as the other apps.

If we ever add a proper JCasC surface to the chart, fold the realm in then — separate decision.

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/6/2026, 9:28:33 AM
Done 2026-09-06. oic-auth 4.718 installed, OIDC security realm configured well-known against https://auth.ginbov.nl/realms/homelab with the `jenkins` confidential client; operator logged in and verified.

Two things that cost time, for whoever hits this next:

- Keycloak advertises `authorization_response_iss_parameter_supported`, so pac4j enforces RFC 9207 on the callback. Until the OIDC field mappings were set the login failed with `OidcIssuerMismatchException: received issuer: 'null'` (and before that `error=invalid_scope`). Fixed by setting the field names — `preferred_username` / `name` / `email`.
- Step 3's emergency admin is oic-auth's own **escape hatch**, now configured on the realm (username `admin`, secret in the operator's password manager). Log in at `/login` with those when Keycloak is unavailable; without it a Keycloak outage locks the UI out entirely, since `denyAnonymousReadAccess` is on and the token-expiry check kills live sessions too.

Automation is unaffected by an IdP outage: `jenkins-mcp` and the telegram bot authenticate as the local `admin` user, which has no `OicCredentials`, so `allowTokenAccessWithoutOicSession=false` does not apply to it.

No repo change, as filed. Archiving.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:32:20 AM
Triaged 2026-08-16: Chore — outside the rubric, so no severity label. Every step is hand-work in the running Jenkins and the Keycloak realm, with no repo change to plan: install the oic-auth plugin, configure the OIDC security realm, keep an emergency admin, and create the `jenkins` confidential client and its secret.

Operator ruling: "Agreed." Moved to Operator Actions, as the card itself proposed.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/AEO1suJp/577-jenkins-oidc-login-via-oic-auth-in-app-no-chart-change
- **Short URL**: https://trello.com/c/AEO1suJp

---
*Last Activity: 9/6/2026, 9:28:51 AM*
*Card ID: 6a7e03b481d58d8fe9be344f*
