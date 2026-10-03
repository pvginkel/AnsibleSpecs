# P2 code review — round 1

PrometheusDeploy `915ceeb..017c71f` (`phase/040-P2`). Gate green on `017c71f` (taken as given).

**Readiness.** The pod and node rules meet D2. Their windows are grounded in history, and the
tests walk each edge they claim. I checked this against live series shapes: KSM's
`namespace`/`service`/`node` labels win over the scrape's target labels. Running Prometheus
3.14 uses left-open ranges, which the edge timings depend on. The KubeCoder exemption through
the KSM label allow-list is correct and asserted in the render. One gap remains in the
LoadBalancer rule, and it blocks. The rule treats "no `metallb_speaker_announced` series at
all" as a metrics gap. But a speaker that is scraped and up and announces nothing exports no
series either. MetalLB withdrawing every Service, which is the worst case of R1's "the DHCP
failure itself", therefore raises no critical alert, only a warning that routes silently. The
other two findings are advisory.

## F1 — Major · blocking · anchor: repro-trace · confidence: high

**MetalLB withdrawing every Service, with all speakers scraped and up, raises no critical alert.**

`config/prd/values.yaml:462` guards `LoadBalancerNotAnnounced` with `and on ()
metallb_speaker_announced`. The comment at `:439-444` treats "no announcement at all" as a
scrape gap. On a live speaker, though, withdrawing a Service deletes its series, so it does not
read 0. Live on 2026-10-03, `metallb_speaker_announced == 0` returns nothing while 42 Services
are unannounced. A speaker that is up and announces nothing therefore exports no series. The
guard cannot tell "Prometheus cannot see the speakers" from "the speakers see nothing to
announce". In the second case every LoadBalancer is down, DHCP included, and the only signal is
`MetalLBAnnouncementsBlind`. That is `severity: warning` (`:482`), routed to the silent
`telegram-warning` receiver (`:528`). Its own description (`:488-490`) names this case.

Repro (promtool, witnessed, against the rendered rules). Inputs:

- `up{job="kubernetes-pods", namespace="metallb-system", component="speaker"}` is 1 throughout.
- `kube_service_spec_type{namespace="dnsmasq-prd", service="dhcp", type="LoadBalancer"}` is 1
  throughout.
- The only `metallb_speaker_announced` series, for `dnsmasq-prd/dhcp`, reads `1x4 stale`.

At 30 m, the expected `LoadBalancerNotAnnounced{namespace="dnsmasq-prd", service="dhcp",
severity="critical"}` comes back `got:[]`.

This contradicts Ruling D3 and V01: a LoadBalancer Service that MetalLB does not announce is
critical, on every LoadBalancer Service except KubeCoder environments'. The plan's constraint
(`plan.md` P2, "A gap in MetalLB's own metrics must not read as every Service unannounced")
covers a gap in the metrics. It does not cover MetalLB failing while its metrics are present.
Live, the speakers' `up` series are a separate signal for whether the speakers are being
scraped.

How likely it is: the trigger is a MetalLB-wide fault, such as a broken L2Advertisement or
IPAddressPool, or an upgrade or config regression. The P3 DHCP and OIDC probes would partly
cover it once they land. The rule this phase adds still stays silent in the case where every
LoadBalancer is down.

## F2 — Minor · advisory · anchor: none · confidence: high

**The `> 0` filter in `LoadBalancerNotAnnounced` is not pinned by any test, and the done-record
says it is.**

I deleted `> 0` from `config/prd/values.yaml:459`
(`max by (service) (metallb_speaker_announced) > 0` became `max by (service)
(metallb_speaker_announced)`) and ran `tests/alert-rules.sh`. All seven test files passed.
`tests/alert-rules/loadbalancers.yml` never feeds a zero-valued announcement, so the filter can
go without a red test. `plan.md:307` says "Rule test mutations (look-back, reason set, guard,
label, `> 0`) each fail a test". That is false for `> 0`. The code is right today: live
speakers delete the series rather than writing 0, so the filter is defensive.

## F3 — Minor · advisory · anchor: none · confidence: high

**`PodStuckInBackOff` fires on a loop that held about 11 minutes, under D2's 15.**

The 5 m `max_over_time` (`config/prd/values.yaml:390,392`) keeps a pod pending for 5 m after
its last wait. The test pins this: `tests/alert-rules/pods.yml:119`. There,
`iot-support-validation-141`, which waits 0–11 m and then clears, fires at 15 m and resolves at
16 m. The result is a warning and a "resolved" one minute later, for a pod that was never stuck
for 15 minutes. Ruling D2 says "after the condition holds 15 minutes". The executor names this
as an accepted cost in the done-record (`plan.md:297-299`) and in the rule's comment
(`:381-383`), and gives the reason: bridging running spells of up to 4 m. The deviation from
the ruling is the operator's to accept. It routes silently.
