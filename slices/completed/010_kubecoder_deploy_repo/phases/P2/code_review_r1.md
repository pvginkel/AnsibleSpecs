# P2 code review — round 1

Range: HelmCharts `65ca9dbe..869e19b` (`phase/010-P2`), one commit.

**Readiness.** P2 delivers settled item 6 and meets acceptance criterion V20. `desired_state()` now reads each entry's `reconciler:` the same way `read_reconciler` does (`tools/chart_tools/audit_prd_orphans.py:153`). A non-`jenkins` entry goes into `owned_elsewhere` and never into `helm_releases` or `disabled`, while its namespace and `_shared/*.tf` storage stay desired (`:149`, `:164-177`). So a healthy Argo app is not reported missing. `cmd_diff` removes owned-elsewhere names from the live Helm releases before the orphan diff and lists them separately (`:373-384`). The guard keys on ownership, not on a release name, as `plan.md:314` requires.

What I checked:
- **Real tree:** `desired_state` on the real tree gives `owned_elsewhere == {argocd-prd}`. `argocd-prd` is still a desired namespace and is not a desired Helm release.
- **Live name:** on prd, Argo's Deployments carry `meta.helm.sh/release-name: argocd-prd` in namespace `argocd-prd`, so the guard's name matches the live bootstrap release.
- **Tests run:** the gate log records only the command's OK line, with no per-test counts, so I ran `tests/test_audit_prd_orphans.py` on its own: 4 passed.
- **Mutations** (applied in memory, no files touched):
  - Dropping the diff guard fails the orphan test.
  - Making `desired_state` ignore `reconciler:` fails all four tests.

  The tests are not vacuous.
- **New comments:** they are accurate. The "stdlib + pyyaml only" reason matches HelmCharts `CLAUDE.md:87`, and `resolve_helm_args` imports `requests`/`semver` (`resolve_helm_args.py:5-6`).

One advisory finding, below.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**The suite does not pin that the uninstall guard keys on ownership rather than on the name `argocd-prd`.**

- The only test of the diff guard uses an Argo-owned entry named `argocd/prd` with a live release `argocd-prd` (`tests/test_audit_prd_orphans.py:68-79`).
- The other test that goes through `cmd_diff` has no live release for its Argo-owned entry (`:58-65`).
- Mutation: I changed `audit_prd_orphans.py:374` to subtract `{"argocd-prd"}` instead of `desired["owned_elsewhere"]`. All four tests still pass.

The shipped code is correct. `plan.md:310-314` names the case this leaves open: slice 012's cutover puts live `kubecoder-<stage>` releases under an Argo-owned entry. If a later edit narrows the guard to the one name, the suite stays green and those releases would be listed as orphans to uninstall. V20's named case (`argocd-prd`) is covered, so this is advisory.
