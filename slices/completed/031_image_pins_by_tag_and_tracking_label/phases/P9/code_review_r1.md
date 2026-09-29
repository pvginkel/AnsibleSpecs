# P9 code review — round 1

Range `0cf4a3f..HEAD` on `phase/031-P9` (AnsibleSpecs `14308f1`, `2639c26`).

**Ready to merge.** The diff only inserts lines. D53 gains one dated amendment
(`argo-cd/decisions.md:854-870`), placed after its last bullet and before D54, and the plan gains
P9's done-record. No D53 sentence changed. The amendment delivers the plan's three points
(`plan.md:699-701`):

- An image from `registry:5000` is pinned to a per-build tag, never a digest.
- A matrix build pushes `<tag>-<n>`, and the pin stage writes it wherever a pin list exists, today
  only keycloak's. This matches R3 and P6.
- The relay pin lives in ArgoCDDeploy's prd stage values and is written by relay builds, which
  leaves `argocd-prd` out of sync. This matches Ruling D3, P3 and P6.

It also leaves upstream digest pins to ANS-139, satisfying V07. It follows the register's
amendment style: dated to the ruling (2026-09-26), with the operator's "Go" and the slice/card
reference, as at `:59` and `:228`. Its factual claims check out:

- The 2026-09-25 GC deletion of KeycloakDeploy's pinned digest is in `slice.md:7-8`.
- Its "(D3)" for `argocd-prd` being synced by hand matches the register's own use at `:80` and
  `:297`.
- It says what RegistryDeploy's corrected comment (`dca461d`, `config/prd/values.yaml`) cites
  D53 for: "pinned to a per-build tag, never to a digest: no build pushes that tag again". So
  the string the test phase copies estate-wide (Ruling R1-Q3) now has its backing.

The done-record's line references are exact: `:854-870`, and homelab `decisions.md:610`. No test
gate is recorded for this commit. AnsibleSpecs has no configured gate
(`kc project info`: no `.kubecoder/project.yaml`), and this prose-only change leaves nothing for
a gate to exercise, so the unverified state bears on no finding.

## Findings

None.
