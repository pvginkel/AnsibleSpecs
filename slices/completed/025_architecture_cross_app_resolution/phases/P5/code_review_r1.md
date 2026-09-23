# P5 code review — round 1

**Readiness: ready to merge. No findings.** The phase delivers its outcome and meets V14. D55, at
`argo-cd/decisions.md:646-662`, sits directly after D50 in "Migration and endgame". The register
places entries by section, not by number: D46 and D49 are already out of numeric order. D55 is the
next free number, and nothing else in AnsibleSpecs indexes the register's numbers. It covers all
three required points:

- the in-cluster interfaces linked to their serving instances by `Association`, init containers
  excluded (:647-651);
- resolution through the published set, filtered as in-process resolution filters, with the edge
  staying instance → instance and keeping its id (:654-657);
- an unresolved host stays fatal, and a new app's bootstrap is done by hand (:659-661).

I checked each code-facing claim against the landed generators:

- The host form `<svc>.<ns>.svc` in `stats.url`, the `Association` from non-init instances only,
  and the links on both the in-cluster and the `appif.` interfaces match ArgoCDTools
  `aac-tools/image/gen_architecture.py:1357-1387`.
- The three-entry hint table matches `:140-144` and HelmCharts `tools/chart_tools/gen_architecture.py:127-131`.
  OpenBao sitting outside Kubernetes matches `/work/AnsibleSpecs/decisions.md:28`.

The provenance quote is a verbatim extract of D1's operator line (plan.md:27-28). The entry
narrates no history. All added lines fit in 100 columns.

**Gate: unverified.** This commit has no recorded gate. The specs repo has no lint, so the
100-column check above is the only mechanical check there is.

**Considered and not raised.** "each in-cluster Service they render" (:648-649) is wider than the
code, which publishes only Services with a non-empty backing set (`gen_architecture.py:658-659`).
A Service with nothing behind it cannot be a provider, so the gap has no consequence. The one live
case, dnsmasq's pod-name selector, is already close-out B2.
