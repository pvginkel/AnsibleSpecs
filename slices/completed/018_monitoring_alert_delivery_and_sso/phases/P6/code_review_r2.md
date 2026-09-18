# P6 code review — round 2

HelmCharts `2af8b69..0b35392` (`phase/018-P6`). The fix round changes only
`tests/test_pgadmin_keycloak_login.py`, and it resolves round 1's only blocking finding. The
phase is ready to merge, and the round adds no new findings.

## F1 (round 1) — resolved

`test_the_operators_keycloak_account_is_pre_created_as_admin_with_the_servers` now pins both
sides of the join between a Keycloak sign-in and the pre-created admin account:

- **Login side.** `tests/test_pgadmin_keycloak_login.py:113-114` asserts
  `OAUTH2_USERNAME_CLAIM == "email"`. It reads the value from the executed `config_local.py`,
  through the same fixture the other config tests use.
- **Init-container side.** The existing assertions still cover it: `add-external-user
  "$PGADMIN_EMAIL"` at `:119-122`, and `PGADMIN_EMAIL` from `.Values.pgadmin.defaultEmail` at
  `:126-127`.

I ran mutations on a scratch copy of the chart and test, with only that test file run each time:

| Mutation | Result |
|---|---|
| None (baseline) | 9 passed |
| `OAUTH2_USERNAME_CLAIM` → `'preferred_username'` | the test fails |
| `OAUTH2_USERNAME_CLAIM` → `'sub'` | the test fails |
| `OAUTH2_USERNAME_CLAIM` line deleted | the test fails |
| init container's `add-external-user "$PGADMIN_EMAIL"` → `"$PGADMIN_USER"` | the test fails |

The new comment at `:111-112` matches the code. Round 1's F2 (advisory) was left unfixed on
purpose. It is already in the close-out report as S4.
