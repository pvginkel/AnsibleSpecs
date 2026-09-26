# Close-out — slice 031 image_pins_by_tag_and_tracking_label

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

### ~~A1 — Check RegistryDeploy out in the environment that will run this slice, before the run~~ — resolved at planning: operator (2026-09-26) 'You dont have to restart to get the repo. Just clone it.' — RegistryDeploy cloned to /work/RegistryDeploy and declared in Ansible .kubecoder/config.yaml (Ansible 7154030); struck by plan-slice session, review r1

P7 targets `../RegistryDeploy`, and no environment clones that repo today: it is not in Ansible's `.kubecoder/config.yaml`. Before the run, add `- url: https://github.com/pvginkel/RegistryDeploy` to that file's `repos:` list in the environment that will run the slice, then `kc env restart`. Until then `run_loop.py run … --dry-run` reports P7's Target as "not an existing directory". The plan-writer did not make the edit. The Ansible checkout is per environment, and slice 029's run was active in another environment's checkout at planning time.

**Consequence:** Until this is done the run cannot start. P7 has no Target, so the cleanup job stays suspended and the slice cannot lift the pause.

**Provenance:** witnessed — plan-writer, planning, r1, plan.md P7 and run_loop.py --dry-run
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — KubeCoder prd's tunnel-reclaim pin is refreshed only by promotion, so a long gap between promotions can put it past the keep-newest cap

After P2 and P6, DockerImages' builds write the tunnel-reclaim pin on KubeCoderDeploy's `main`. prd picks it up only when KubeCoder is promoted (Settled). The image's bare build numbers are in `latest`'s series, capped at the newest 10, and it rebuilds about weekly: the registry held tags 2475 to 2531 on 2026-09-26. About ten tunnel-reclaim builds without a promotion put prd's pinned build over the cap. R1 assumes the continuous rebuilds keep every pin fresh, but this pin also depends on how often KubeCoder is promoted. A nightly dry-run list would show it before any deleting run. The plan changes nothing here; Settled routes the pin through promotion.

**Consequence:** Once dry-run is off, if KubeCoder prd goes about ten weeks without a promotion, cleanup deletes its tunnel-reclaim image. The kubecoder-prd controller pod then cannot start again after a reschedule; the chart says a missing one takes the controller down.

**Provenance:** read — plan-writer, planning, r1, KubeCoderDeploy chart/values.yaml:13-18 and the live registry's tag list
**Disposition:**

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — argo-migrate would write registry image digests, and the old comment, into a future migration's values

`compose_values` (`Ansible/support/argo-migrate/argo_migrate.py:466-493`) copies what HelmCharts' deploy CLI passed, including the release's resolved image digests, into `config/<stage>/values.yaml`. It writes them under the comment that P7 and P10a–P10b correct. The only stages left to migrate are the parked ones: design-assistant ×4, open-webui and shell. DesignAssistant's images are in our registry. The plan leaves the tool alone, because R2 names the deploy repos and the comment, and slice 029's P7 is changing the same tool. A fix would have the tool pin the build tag, in the image's label series, that points at the release's digest, and stop when no tag does.

**Consequence:** Migrating a parked app whose images are in our registry creates a digest pin again. Once dry-run is off, the nightly garbage collection can delete the image behind that pin, which is how Keycloak lost its image.

**Provenance:** read — plan-writer, planning, r1, argo_migrate.py:466-493
**Disposition:**
