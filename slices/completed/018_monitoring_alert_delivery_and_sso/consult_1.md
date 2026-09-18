# Completion consult 1: complete

## AC → implementing work

| AC | Delivered by |
|---|---|
| V01 (R1, both facets) | P1 (corroborated stall alerts, wedge warning) + P2 (Telegram delivery) |
| V02 (R2) | P5 (Grafana) + P6 (pgAdmin); secrets are operator checklist steps 2–4 |
| V03 (R3 upgrade) | P3 (DockerImages 33412e2) + P4 (HelmCharts 3d3e883, 01532e9). Backup clause waived by the 2026-09-18 pre-run ruling (close-out N3) |
| V04, V05 | P1 (cd51a9c) |
| V06 | P1; the live check is the test phase's (advisory A1: srvk8s1's current wedge firing the warning is correct) |
| V07, V08, V15 | P2 (e9820f9) |
| V09 | P5 (aa875f7) |
| V10 | P6 (2af8b69, 0b35392) |
| V11 | P5 + P6 (login form kept, no auto-redirect) |
| V12 | P5 (dev Grafana untouched) + P6 (dev pgAdmin renders without OIDC) |
| V13 | P4 (Recreate strategy; keycloak-dev goes first in its own commit) |
| V14 | P4; post-upgrade live check, test phase |

No phase depends on something nothing produced. Every ruling (D1–D6, U1, F1–F3, A1, A2) has a
phase or a checklist step behind it. A2 and step 6 were superseded by the 2026-09-18 waiver.

## Left to the test/doc phases (not appended)

- Live verification: V01, V06, V07, V09–V11, V13, V14, in the push order from Ordering
  constraints.
- Doc phase: P4's note that Ansible `docs/runbooks/k8s-rebuild.md:34` and
  `docs/runbooks/k8s-upgrade.md:211-212` still describe Keycloak as RollingUpdate with a
  two-pod window.
- Push-time context: HelmCharts `main` is 2 commits behind `origin/main`, including
  `ba7804c` "Chart gate: lint, render and kubeconform every release before any deploys".
  The rebase before the push runs that new gate over this slice's releases for the first
  time.

## Close-out reconciliation

- B4 was comment-only residue. It is fixed in HelmCharts `3987dee`: the values.yaml hold
  comment and the test comment now give the real restart bound. The assertion itself is
  unchanged and is now documented as a conservative floor. `kc project test` is green.
  B4 is struck.
- N3 added: Keycloak deploys with no pre-upgrade dump (operator waiver). This also records
  that the role assignment (step 3) and homelab-dev's step-5 checks were not verified before
  the run.
- Nothing else was struck or absorbed. A1, N1, N2, B1, B2, B5–B7 and S1–S4 stand as the
  operator's to triage.
