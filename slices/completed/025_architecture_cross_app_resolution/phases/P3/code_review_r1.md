# P3 code review — round 1

ArgoCDTools `7806d46..ce5efb9` (`phase/025-P3`), gate green on `ce5efb9`.

**Readiness: ready to merge.** The check now scopes an app by its `<app>-<environment>-` namespace
hint plus the interfaces its instances link or its own services are assigned, and splits touching
relations into the target's own, cross-stage, and "drawn by <producer>". I tested both rules
against real data rather than only the fixtures. Over every `configs/prd` app × {prd, dev}, on the
live set (`/tmp/p3-dataset.yaml`) and on the snapshot with the local HelmCharts render
(`/tmp/p3-snapshot.yaml`):

- No element is claimed by two apps.
- Every helm-charts element that carries `environment` belongs to some app. The one exception is
  in F1.
- Every relation the check assigns to the app is in HelmCharts' render (`/tmp/p3-hc-render.yaml`),
  and every relation it lists as `drawn by helm-charts` is too. Across both datasets there are 0
  misattributions.

On the live set, youtrack's prd target holds no youtrack-mcp element, elasticsearch's holds
`if:kibana`, and keycloak lists exactly the 21 bare-UUID relations under `iotsupport-app`. That
covers V09 and V10. The Q2 extension (a non-Serving relation is drawn by its source's producer)
matches every relation-drawing site in `gen_architecture.py` (:944-970, :1161-1177, :1259, :1287,
:1365, :1520, :1595, :1692, :1725), so the rule is right, not only convenient. The 11 fixture
tests are discovered and pass (`python3 -m unittest -v tests.test_handover_equality` in `iac`).
They cover scoping, the prefix fix, ownership and the cross-stage exclusion order. That satisfies
Ruling A1 and V15's check clause.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**An exposed interface that no app instance links, and that is assigned only to a shared
DockerImages service, is in no app's scope, so losing it passes the check silently.**

`app_elements` reaches an interface through only two paths (`handover_equality.py:179-186`):

- an Association from one of the app's own instances or services;
- an Assignment into one of the app's own services.

An in-house app's exposed interface is assigned to DockerImages' `svc:` (`gen_architecture.py:1227-1228`,
`:1259`), which fails the second path. So it is scoped only if the published set carries its P2
instance link. Two cases follow:

- **Live set, before HelmCharts publishes.** 17 helm-charts interfaces fall into no app. They
  include `if:jenkins-mcp(-home)`, `if:telegram-mcp(-home)`, `if:trello-mcp(-home, -ginbov-nl)`
  and `if:youtrack-mcp(-home)`, which the old prefix scope did compare. If a deploy repo dropped
  one of them, nothing reports it: neither the element nor its `-exposes` Assignment touches the
  target. The P3 done-record ("come out as additions rather than being compared") describes the
  case where the interface is still generated, not the case where it is lost.
- **Permanently.** The same applies to any future in-house Service the provider index cannot
  place (close-out B2's class). Its exposed interface is linked to nothing, so it is never in scope.

The fixture `through_shared` in `test_an_interface_is_the_apps_through_a_link_or_its_own_service_alone`
(`tests/test_handover_equality.py:172-179`) pins this exclusion as intended.

No product consequence under the plan's ordering: the held apps are gated only on the snapshot
(test phase) or after the HelmCharts push (Ruling Q1). In the snapshot, every helm-charts
interface belongs to exactly one app. The risk is an `arch` run against the live set in the window
before that push, or the hypothetical B2-class Service above.
