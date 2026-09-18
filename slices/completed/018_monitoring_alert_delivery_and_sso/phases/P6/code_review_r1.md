# P6 code review — round 1

HelmCharts `aa875f7..2af8b69` (`phase/018-P6`). The chart change delivers the phase's outcome. I
checked the claims that carry it against the pgAdmin 9.18 source, read from the live
`dpage/pgadmin4:latest` image in a throwaway pod in the prd `development` namespace:

- `config_local.py` is imported from `/pgadmin4` (`pgadmin/evaluate_config.py:75`).
- `OAUTH2_ADDITIONAL_CLAIMS` is a list-aware match on top-level claims, ID token first, then
  userinfo (`authenticate/oauth2.py` `__is_any_claim_valid`). It refuses before auto-create.
- An OAuth2 session's crypt key is its access token, and saving passwords is disabled
  (`utils/master_password.py:32-37`, `browser/__init__.py:424-426`). An internal login's key is
  its form password (`pgadmin/__init__.py:764-768`).
- `setup.py add-external-user` exits 0 on `User already exists.`, so the init container can
  re-run.
- The storage dir is keyed on the username alone (`utils/paths.py:73`), so the oauth2 account
  finds `build-pgpass`'s pgpassfile.
- On a fresh volume, the entrypoint's `elif PGADMIN_REPLACE_SERVERS_ON_STARTUP` branch still loads
  the local admin's servers once the init container has created the database.

`poetry run deploy template prd/pgadmin` renders:

- a valid `config_local.py` in the ConfigMap;
- the `keycloak-admin` init container;
- the OIDC env vars from `pgadmin-oidc`;
- the ExternalSecret `pgadmin-oidc` ← `eso/prd/pgadmin/prd/oidc`.

`dev/pgadmin` renders with no OIDC, `config_local` or Keycloak trace. No secret is in a committed
file.

The one blocking gap is in the new test. It does not pin the username claim, and that claim is
what joins a Keycloak sign-in to the pre-created admin account.

## F1 — The test leaves the Keycloak-login ↔ pre-created-account join unpinned (Major · blocking · coverage-gap · confidence high)

The operator becomes an admin on their first Keycloak sign-in only if two usernames match:

- **The username pgAdmin resolves at login.** `OAUTH2_USERNAME_CLAIM: 'email'`
  (`charts/pgadmin/files/config_local.py:24`).
- **The username the init container pre-creates.** `add-external-user "$PGADMIN_EMAIL"`
  (`charts/pgadmin/templates/pgadmin-deployment.yaml:74`).

`test_the_operators_keycloak_account_is_pre_created_as_admin_with_the_servers`
(`tests/test_pgadmin_keycloak_login.py:108-131`) asserts only the init-container side. No test
reads `OAUTH2_USERNAME_CLAIM`: the `config_local` tests at `:63-89` assert name, display name, the
two URLs, scope, additional claims, `MASTER_PASSWORD_REQUIRED` and client id/secret, but not this
setting.

Mutation run: I changed `'OAUTH2_USERNAME_CLAIM': 'email'` to `'preferred_username'` in a scratch
copy of the chart. All 9 tests still passed.

What that mutation does in production:

1. pgAdmin 9.18 takes the configured claim from the ID token (`oauth2.py` `_resolve_username`).
2. It then looks for `(username, 'oauth2')`, and on no match `__auto_create_user` creates a new
   account: non-admin, with no servers (plan Grounding, pgAdmin).
3. So the operator's Keycloak sign-in lands in a fresh non-admin account, separate from the
   pre-created `pvginkel@gmail.com` admin.
4. It does not list `postgres-pas`.

This breaks V10 ("signs in … as a pgAdmin administrator that already lists and can connect to the
chart's postgres-pas server"). `sub`, a UUID, breaks it the same way. `preferred_username` breaks
it unless the realm uses the email as the username.

The test named for this behaviour covers only half of the join. The half it skips is the one a
future edit to `config_local.py` is most likely to touch.

## F2 — The fresh-storage bootstrap in `keycloak-admin` is untested (Minor · advisory · anchor none · confidence high)

Two lines of `keycloak-admin` exist only for a volume that has no configuration database yet:

- the `setup-db` step (`pgadmin-deployment.yaml:71-73`);
- the `setup-log` mount on `/var/log/pgadmin` (`:92-93`, volume `:146-147`).

The image has no `/var/log/pgadmin` and runs as uid 5050. Outside CLI mode, `create_app` creates
the log directory and opens its log file there (pgAdmin `config.py:324-327`,
`pgadmin/__init__.py:258-266`). The executor's record says `setup-db` needs that directory.

Mutations run: removing the `setup-log` mount passed all 9 tests, and so did removing the
`setup-db` step.

Production is not affected: its PVC already holds `pgadmin4.db`, so neither line runs there.

- A rebuilt or restored-empty PVC would exercise both lines.
- Without either line, `keycloak-admin` fails and pgAdmin does not start.
- Nothing in the suite would have flagged the removal.
