# Close-out — slice 018 monitoring_alert_delivery_and_sso

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — srvk8s4 ran at 5% MemAvailable and up to 842 major faults/s during 2026-09-07 → 09-14, without memory stall · minor

Replay for P1's thresholds: min(MemAvailable/MemTotal) 0.050 and max rate(node_vmstat_pgmajfault[5m]) 842/s on srvk8s4 (20 GiB node), p99 faults ~258–317/s, while its stall rate never exceeded 0.007. The other three nodes stayed above 17% available and under 192 faults/s. No alert covers this by design (the mixin's standalone memory alerts are out of scope).

**Consequence:** srvk8s4 runs close to its memory ceiling with no alert on it; a capacity look may be due.

**Provenance:** witnessed, plan-writer, planning r1, live production Prometheus queries 2026-09-14
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — HelmCharts: an OpenAI API key is committed in plaintext in configs/dev/electronics-inventory/prd/values.yaml:15 · major

The file's header accepts inline dev secrets because the dev cluster is isolated, but an OpenAI project key (sk-proj-…) is a third-party credential usable from anywhere — the isolation argument does not cover it. Seen while surveying dev-cluster OIDC precedent for slice 018; nothing in this slice touches that release.

**Consequence:** A working OpenAI key sits in HelmCharts' git history for anyone with repo read access; rotating it and materialising it from OpenBao is owed.

**Provenance:** read, plan-writer, planning r1, HelmCharts configs/dev/electronics-inventory/prd/values.yaml
**Disposition:**

### B2 — HelmCharts CLAUDE.md: says prd Prometheus retains ~2 days (retentionSize: 2GB); the release sets 7d / 10GB · minor

HelmCharts CLAUDE.md (recommend-resources) states the window is nominally 5 days but Prometheus retains ~2 (retentionSize: 2GB). configs/prd/prometheus/prd/values.yaml:3-4 sets retention: 7d, retentionSize: 10GB, and a 7-day range query answered with a full week of data on 2026-09-14.

**Consequence:** recommend-resources' documented measurement window is wrong; a reader sizing resources or an investigation trusts a 2-day window that is really 5.

**Provenance:** read, plan-writer, planning r1, HelmCharts CLAUDE.md + live Prometheus query
**Disposition:**

### B3 — Ansible docs: k8s-rebuild.md and pre-drain-handoff.yml still name keycloak-db as a pre-drain opt-in that no longer exists · minor

docs/runbooks/k8s-rebuild.md:35 describes a keycloak-db Deployment (Recreate, ~30 s outage) handed off before every drain, and ansible/playbooks/tasks/pre-drain-handoff.yml:22 lists 'keycloak, keycloak-db (HelmCharts)'. In HelmCharts only charts/keycloak/templates/keycloak-deployment.yaml:7,22 carries iac.webathome.org/pre-drain, and the live keycloak-prd namespace runs a single keycloak Deployment (Keycloak's database is postgres-pas, charts/keycloak/values.yaml:9).

**Consequence:** An operator reading the runbook before a node drain expects a keycloak-db hand-off and outage that no longer happens; the stale line can survive when slice 018's doc phase rewrites keycloak's entry for the stop-before-start rollout.

**Provenance:** read, plan-writer, planning r2, plan.md P4
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — Point the keycloak-tf placeholder at slice 018's hand-made client table · minor

The #575 forward constraint says keycloak-tf must import these clients, never recreate them; the record of the four clients (ids, redirect URIs, admin roles, the pgadmin_roles mapper) lives in slice 018's plan.md pre-run checklist. Slice documents are compressed at close (design-philosophy.md), and change_requests/keycloak_tf/keycloak-tf.md does not reference it.

plan-reviewer r1, 2026-09-14 — Since ruling D6 the plan's pre-run checklist records two hand-made clients (grafana, pgadmin — production homelab realm only), not four; the keycloak-tf pointer should name those two.

**Consequence:** The keycloak-tf slice may not find the client inventory it must import once slice 018 is compressed.

**Provenance:** read, plan-writer, planning r1, AnsibleSpecs change_requests/keycloak_tf/keycloak-tf.md
**Disposition:**
