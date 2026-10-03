---
issue: ANS-193
---

# 042 — HelmCharts leftovers: KitchenDisplay's deploy key, the openbao role's changed reporting

Two residues of slice 029's HelmCharts decommission: KitchenDisplay still clones the archived
HelmCharts repo for its deploy key (ANS-144), and the Ansible openbao role's unconditional writes
always report ok, so a changed AppRole or OIDC config shows `changed=0` (ANS-160).

Source: triage 2026-10-02 of the ANS intake queue. Cards: ANS-144, ANS-160. The phase count
triage guessed (~4) is a guess from the cards alone.

## Requirements

1. **ANS-144 — KitchenDisplay's key becomes a Jenkins SSH credential.** "Fix: store the key as a
   Jenkins SSH credential, rework `rsync`/`ssh` to use it (or rehome them out of the `helmCharts`
   var), drop KitchenDisplay's HelmCharts clone. Needs the operator to create the credential."
2. **ANS-160 — the openbao role's unconditional writes report changed honestly.** The card:
   "ansible/roles/openbao/tasks/approle.yml and oidc.yml issue uri POSTs with no when and no
   changed_when, so they run on every pass and never report changed, whether or not the state
   differed. [...] Reporting these three honestly needs a read-and-compare first." The close-out
   note: "the drift job runs `--check`, where these uri POSTs are skipped outright, so AppRole/OIDC
   drift never shows there; a real run silently re-imposes it. The fix follows the policy tasks'
   GET-and-compare, but the reads return values in a different shape than the writes send (TTLs
   normalised, the OIDC client secret omitted), so the comparison needs care."

## Operator rulings and Q&A

- No ruling at triage on either card. ANS-144 needs the operator to create the Jenkins SSH
  credential (the card's words). ANS-160's proof needs a run against the live secret store (the
  nightly card pass: "can only be proven by a run against the live secret store. The drift job's
  --check skips these tasks."); playbook runs are the operator's.
- No standing-decision collision found at triage for either card.
- Triage grouped these two by provenance (both are slice 029 residue) — the planner may split
  them.

## Source material

The cards as read at triage on 2026-10-02, verbatim (headings demoted one level). A card's
diagnosis, cause or line reference is the card's claim, not verified at triage.

### ANS-144 — Move KitchenDisplay's deploy key out of HelmCharts into a Jenkins SSH credential

- Reporter: jeeves · Created: 2026-09-26 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-27
- Links: Relates: ANS-119

#### Description

KitchenDisplay's Jenkinsfile (main) clones HelmCharts and deploys with JenkinsPipelineUtils' `helmCharts.ssh` (x2) and `helmCharts.rsync`, which read `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key`. Slice 029 kept those two helpers for that reason (operator ruling 2026-09-26), so after the archive KitchenDisplay still clones the archived repo for its key.

Fix: store the key as a Jenkins SSH credential, rework `rsync`/`ssh` to use it (or rehome them out of the `helmCharts` var), drop KitchenDisplay's HelmCharts clone. Needs the operator to create the credential.

#### Comments

Comment 1/1 · 7-5141 · jeeves · 2026-09-27 01:01Z

Card pass 2026-09-27: outside the lane — no boundary crossed: it needs a new Jenkins SSH credential, which the card says the operator creates.

### ANS-160 — Ansible openbao role: the unconditional writes (Write AppRoles, Write the OIDC config, Write the OIDC admin role) always report ok

- Reporter: jeeves · Created: 2026-09-29 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-30
- Links: Relates: ANS-119

#### Description

ansible/roles/openbao/tasks/approle.yml and oidc.yml issue uri POSTs with no when and no changed_when, so they run on every pass and never report changed, whether or not the state differed. The six gated writes were fixed to report changed in Ansible c94ae95 after a run that rewrote the iac-agent policy recapped changed=0. Reporting these three honestly needs a read-and-compare first.

**Consequence:** A run that changes an AppRole's settings or the OIDC config shows changed=0, so neither the operator nor the drift job can see it happened.

**Provenance:** witnessed, the operator's session after the registry switch, 2026-09-28; Ansible c94ae95

Close-out note (2026-09-29): the drift job runs `--check`, where these uri POSTs are skipped outright, so AppRole/OIDC drift never shows there; a real run silently re-imposes it. The fix follows the policy tasks' GET-and-compare, but the reads return values in a different shape than the writes send (TTLs normalised, the OIDC client secret omitted), so the comparison needs care.

Report: AnsibleSpecs slices/completed/029_helmcharts_decommission/close-out.md (B6)

#### Comments

Comment 1/1 · 7-5249 · jeeves · 2026-09-30 01:01Z

Card pass 2026-09-30: outside the lane — a gate would catch it: the read-and-compare against OpenBao's normalised reads (TTLs, the omitted OIDC client secret) can only be proven by a run against the live secret store. The drift job's --check skips these tasks.
