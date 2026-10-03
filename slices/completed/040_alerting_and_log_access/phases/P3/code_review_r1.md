# P3 code review — round 1

Range `6199854..245ee38` on `phase/040-P3`, PrometheusDeploy. Gate green on `245ee38` (taken as given).

**Readiness: ready to merge.** The phase meets its outcome. A blackbox exporter rides the companion
chart and probes the homelab realm's discovery document. Its module passes only a 200 over TLS
whose body carries the realm's `issuer`. I re-checked live that the cert is Let's Encrypt and that
the body opens `{"issuer":"https://auth.ginbov.nl/realms/homelab",…`. `OIDCDiscoveryFailing` is
critical. `OIDCDiscoveryUnprobed` means an exporter that is down, or a scrape that fails, never
reads as a pass (V03). The `dhcp` group puts critical on no OFFER and warning on a result that is
stale or missing, over P1's series (V02's alert half). The two pairs never fire at the same time.
The image has its `images:` entry, and the product sits in the judgment layer's `products:`. The
gate's `gen-architecture`/`arch-validate` reported no gap. The routing test covers the new rules
unchanged (V12).

I checked the tests for vacuity by hand against mutations of the thresholds:
- `> 15*60` → `14*60`: the 18 m case catches it.
- `[15m]` → `[10m]`: the 28 m case catches it.
- Unprobed `for: 10m` → `9m`: the 10 m gap case catches it.
- Hold without `unless`: the resolve case catches it.

The executor's own mutations cover the rest. One advisory edge remains.

## Findings

### F1 — Minor · advisory · anchor: repro-trace · confidence: high

**`DHCPNotAnswering` pages critical when one failed probe is followed by a lost srviac scrape,
with no further evidence that DHCP is down.**

The hold branch (`config/prd/values.yaml:572-575`) sums `ALERTS{alertname="DHCPNotAnswering"}`
over every `alertstate`, so it keeps a *pending* alert alive, not just a firing one. The pending
clock keeps running while no `dhcp_probe_success` is scraped. So a single 0 starts a 12 m clock,
and srviac going unscraped for the rest of that window ends it critical.

The comment at `:554-556` says the hold is there so the alert "resolves only on a probe that got
an OFFER". That reason covers a firing alert. Holding a pending one turns a missing result into a
critical. The plan grades a missing result a warning: `plan.md:331-332`, "It is a warning when the
result is stale or missing: srviac down, … or node-exporter not scraped".

A single 0 is ordinary: the rule's own comment says a rollout gives up to ~10 m of them. The page
then claims "has not answered a DISCOVER for 12m" (`:578`), but only one probe failed.

Witnessed with promtool against the rendered rules:
- Input: `dhcp_probe_success` reads `1x4 0 stale _x20`, and the timestamp goes stale at the same point.
- Result: `DHCPNotAnswering{instance="srviac.home:9100",server="10.2.1.10",severity="critical"}` fires at 18 m.

`tests/alert-rules/dhcp.yml` case 3 pins the same behaviour after 10 failing scrapes, so this is
by design. The argocd group's holds (`:328`, `:356`) carry the same pending-hold shape.

Why it is advisory: it needs two things together, a probe failure and srviac unscraped for ≥ 12 m
straight after. `DHCPProbeStale` fires beside it and points the operator at srviac.
