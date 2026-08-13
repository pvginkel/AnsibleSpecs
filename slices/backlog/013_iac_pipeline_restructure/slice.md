# 013 — IaC pipeline restructure: iac-image rebuild scoping + IaCAgent merge

Stop the `iac` image rebuilding on every Ansible push, and fold the `IaCAgent` repo into Ansible
so the `iac_agent` role stops depending on a sibling checkout.

## What is being requested, and why

The IaC build/deploy pipelines grew organically across four repos (`Ansible`, `IaCAgent`,
`HomelabTerraformProvider`, `HelmCharts`). A 2026-07 diagnosis found two pipeline problems and one
repo boundary that no longer earns its keep. The diagnosis is written up in the attached change
request, parked since then and never implemented.

The write-up opened with three pillars. **The first (P1, the provider-bump race) has already
shipped** as the `tf-provider-registry` slice — the change request records the hand-off itself:

> **P1 (the provider bump race) has been handed off to
> [tf-provider-registry](completed/tf-provider-registry.md)** — a private registry removes the
> lock-push and the single-version mirror entirely, which is a better fix than the job-sequencing
> this slice originally proposed. The two surviving pillars are the iac-image rebuild scoping (P2)
> and the IaCAgent→Ansible merge.

This slice is those two surviving pillars. The change request calls them independent — "the two
pillars are independent; do either first" — and they are filed together because the origin card
asks for them together, not because they must land together.

## Requirements

Numbered from the origin card and the attached change request. Quotes are the source's words;
anything in my own phrasing is marked **(triage)**.

### Pillar A — scope the `iac-image` rebuild (the change request's "P2")

**R1.** Stop `iac-image` rebuilding on pushes that cannot change the image.

> **P2 — the rebuild flood.** `iac-image` rebuilds on *every* Ansible push, but its real inputs
> change on a tiny fraction of them: `support/iac-image/**`, the root `pyproject.toml`/`poetry.lock`
> baked into the image, `ansible/roles/baseline/files/homelab-root.crt`,
> `ansible/files/known_hosts.d/homelab`, and the provider binary. Everything else (roles,
> playbooks, host_vars, Terraform `.tf`) rebuilds the image for nothing.

**R2.** Gate inside the pipeline rather than changing the job's trigger.

> 1. **Scope `iac-image` to its inputs** (P2). Add the `hasChanges` gate; leave the push trigger
>    but make the build a no-op when no image input changed. Verify an unrelated Ansible push
>    skips the image build.

The change request names the pattern to follow:

> - trigger only when image inputs changed — gate inside the pipeline with the same
>   `utils.hasChanges(...)` / `markStageSkippedForConditional` pattern HelmCharts already uses
>   (`HelmCharts/Jenkinsfile`, `changed()`), watching `support/iac-image/**`, the root
>   `pyproject.toml`/`poetry.lock`, the baseline cert
>   (`ansible/roles/baseline/files/homelab-root.crt`), and the committed `known_hosts`
>   (`ansible/files/known_hosts.d/homelab`). Everything else → skip. P2 gone.

**(triage)** The input list above was written before `tf-provider-registry` landed. The change
request predicted the set would shrink when it did:

> Note the input set **shrinks** once [tf-provider-registry](completed/tf-provider-registry.md)
> lands: the provider binary leaves the image entirely (no more `filesystem_mirror` bake, no
> `copyArtifacts` from the provider build), so a provider release no longer rebuilds the `iac`
> image at all.

That slice is in `slices/completed/`. Establishing the current input set from the Dockerfile as it
stands is planning work — the list above is the source's, not a verified inventory.

### Pillar B — merge `IaCAgent` into `Ansible`

**R3.** Fold the IaCAgent tree into the Ansible repo and make the `iac_agent` role read it in
place.

> **✅ Merge IaCAgent → Ansible.** The Jenkinsfiles already moved out of IaCAgent into Ansible
> (`IaCAgent/README.md` says so). What remains (`bin/`, `systemd/`, `install.sh`) is srviac
> host-glue that the `iac_agent` role **already rsyncs from a sibling checkout**
> (`ansible/roles/iac_agent/defaults/main.yml`:
> `iac_agent_local_checkout: {{ playbook_dir }}/../../../IaCAgent`). The split costs: a separate
> repo + push for any helper edit; a sibling-checkout requirement a CI `iac` clone doesn't satisfy
> (so `iac_agent` is effectively operator-apply-only — `iac-on-push` excludes it); and doc drift
> (README still says `iac` runs `modern-app-dev`, but `bin/iac` runs `registry:5000/iac:latest`).
> Fold the tree under `ansible/roles/iac_agent/files/` (or a top-level `iac/`), repoint
> `iac_agent_local_checkout` at the in-repo path, and the role becomes CI-applyable and
> single-source.

**(triage)** The change request's "`iac-on-push` excludes it" was written before the on-push job
was split; the exclusion now lives in `Jenkinsfile.iac-apply`. The claim is the source's and is
recorded as attributed, not verified.

**R4.** Do the surrounding edits the move implies.

> Move the tree under the `iac_agent` role's `files/` (or top-level `iac/`); repoint
> `iac_agent_local_checkout`; fix the README drift; update install/sync paths.

**R5.** Preserve the IaCAgent commit history in the move — operator decision, see Q&A Q3. The
change request accepts the coupling but did not say how:

> - Folding IaCAgent in **couples the srviac host glue's history to the Ansible repo**.
>   Acceptable: they are already one deployment unit and already share the Jenkinsfiles.

**R6.** Prove parity, then retire the repo.

> Apply `iac_agent` once from the operator workstation to prove parity, then archive
> `pvginkel/IaCAgent`.

**R7.** Follow the removed repo boundary through the docs and the model.

> 3. **Update [decisions.md](../decisions.md)** if the IaCAgent location becomes doctrine, and
>    nudge the `update-architecture` agent (removed repo boundary).

## Explicitly not in scope

**N1. Do not remove `--limit "!iac_agent"` from `Jenkinsfile.iac-apply`.** The merge makes CI
application of the role *possible*; the operator does not want it done. Operator, 2026-08-13:

> I don't want to remove the --limit argument. I appreciate it makes it possible, but I don't
> like it.

**N2. Two repo merges were considered and rejected** — settled, not to be reopened:

> **✅ Keep HomelabTerraformProvider separate.** A TF provider is its own Go module with its own
> release cadence; the problem is *ordering*, not *co-location*. Merging it into Ansible would
> make the "build pushes to its own repo → triggers its own deploy" loop worse.
>
> **✅ Keep HelmCharts separate.** Different deployment unit (Jenkins-driven Helm/k8s workloads,
> own deploy CLI, own architecture producer); it only shares the `iac` harness as a runtime. No
> merge case.

**N3. The change request's own out-of-scope list:**

> - The `site*.yml` playbook layout — that's [site-yml-layout](site-yml-layout.md).
> - Provider version resolution (lock vs. mirror, raw `terraform plan`) — owned by
>   [tf-provider-registry](completed/tf-provider-registry.md).
> - The destroy-guard/prevent_destroy/apply-the-checked-plan fixes in the same Jenkinsfiles —
>   urgent and narrow, split out to [tf_safety_rails](../tf_safety_rails/change_request.md)
>   (2026-07 review C1). Coordinate to avoid colliding edits; the safety rails land first.

`site-yml-layout` is Triage **#69**; `tf_safety_rails` is Triage **#127** and its change request
still lives at `change_requests/tf_safety_rails/`. Both remain in the intake queue.

## Known collisions

**(triage)** Two intake-queue cards edit files inside the IaCAgent tree this slice relocates. The
operator's decision (Q4) is to leave both queued and rebase them onto the new paths afterwards —
they are not requirements of this slice:

- **#327** — "iac shim: `--pull=always` turns a registry blip into a failed build" (`bin/iac`).
- **#506** — "Remove the `/var/lock/iac.lock` flock from `bin/iac`".

`tf_safety_rails` (#127) touches the same Jenkinsfiles; its own change request records the
interlock, and the change request above says the safety rails land first.

## Provenance

> Note (2026-07-03 triage): the 2026-07 IaC review independently recommended the IaCAgent→Ansible
> merge (finding S5) — the operator confirmed; this bundle remains its home.

## Interview Q&A (2026-08-13)

**Q1 — one slice or two?** The origin card is one bundle; the change request calls the pillars
independent. Two slices would let the Jenkinsfile gate land without waiting on the merge's design
work.
**A:** One slice. (Triage had argued both ways; the operator chose the single bundle.)

**Q2 — does the merge include un-excluding `iac_agent` from CI?**
**A:** No — see N1 above. The exclusion stays.

**Q3 — history-preserving move, or plain copy?**
**A:** Preserve history. Recorded as R5.

**Q4 — absorb #327 and #506, which edit the tree being relocated?**
**A:** Leave them queued; they rebase after this lands. Recorded under Known collisions.

**Q5 — the card's closing instruction, "Run /write-slice on the folder when ready".**
**A (triage, not asked):** stale command name only — `/write-slice` no longer exists; the route is
`/dev:triage` → `/dev:plan-slice` → `/dev:run-slice`. No requirement lost.

## Attachment

`iac-pipeline-restructure.md` — the 2026-07 change request, moved into this folder from
`change_requests/iac_pipeline_restructure/`. Prior diagnosis and proposal, carried in unvalidated:
its file references, line citations and claims about current pipeline behaviour predate both the
`tf-provider-registry` slice and the `iac-on-push`/`iac-apply` split, and are the author's, not
triage's. Its internal relative links (`completed/…`, `../decisions.md`, `site-yml-layout.md`,
`../tf_safety_rails/…`) were written for its old location and no longer resolve.

## Subsumes

Triage card **#70** — "IaC pipeline restructure — iac-image rebuild scoping + IaCAgent merge".
