# Close-out — slice 023 backup_freshness_alerting

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

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — HelmCharts CLAUDE.md states Prometheus retains ~2 days (retentionSize 2GB); prd values set 7d / 10GB · nit

HelmCharts CLAUDE.md (recommend-resources entry) says 'Prometheus retains ~2 (`retentionSize: 2GB`), so runs measure roughly the last two days'. configs/prd/prometheus/prd/values.yaml:3-4 sets retention: 7d and retentionSize: 10GB. Not touched by this slice.

**Consequence:** A reader sizing recommend-resources runs underestimates the history Prometheus actually holds.

**Provenance:** read — plan-writer, planning, r1, HelmCharts CLAUDE.md vs configs/prd/prometheus/prd/values.yaml
**Disposition:**

### B2 — HelmCharts postgres-pas comments say only prd has a backup-server; a dev storage release carrying backup-server exists · nit

HelmCharts charts/postgres-pas/values.yaml:93-95 says 'only the prd cluster has a backup-server (the storage release isn't deployed on dev)', and configs/prd/postgres-pas/prd/values.yaml:51 says '(prd has one; dev does not)'. HelmCharts configs/dev/storage/prd/{values.yaml,manifests.yaml} is a dev storage release that carries backup-server's age-key ConfigMap, and the slice's refinement settled that backup-server runs on the dev cluster too. The live dev cluster was not checked (srvk8sdev is off). Not touched by this slice.

**Consequence:** A reader of the postgres-pas chart believes dev has no backup-server, so they overlook the dev copy when changing backup-server or testing uploads there.

**Provenance:** read — plan-reviewer, planning, r1, HelmCharts charts/postgres-pas/values.yaml vs configs/dev/storage/prd/
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

### S1 — DockerImages declares no kc project components, so the run loop has no deterministic gate for backup-server phases · minor

run_loop.py --dry-run reports P1 and P2 (Target ../DockerImages) as '(no deterministic gate)'; `kc project list` in /work/DockerImages exits 1. backup-server's Go suite (`go test ./...` from backup-server/src, in the `go` tool container) runs only when the executor runs it by hand. The plan names that command in P1; declaring the component would make it the driver's gate.

**Consequence:** A red backup-server suite in a DockerImages phase is not caught by the driver's gate; it rests on the executor and reviewer running it.

**Provenance:** witnessed — plan-writer, planning, r1, run_loop.py --dry-run output
**Disposition:**
