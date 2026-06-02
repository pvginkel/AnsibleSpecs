# Cloud-init is first-boot only; decouple from VM lifecycle

**Status: complete (2026-06-02).** Landed: the `managed-vm` module
pins `lifecycle.ignore_changes = [initialization[0].user_data_file_id]`
— narrowed to just the user-data file so `ip_config` changes still
propagate — and the prd `cloud-init.yaml.tftpl` was stripped of its
editorial comments so a template edit no longer triggers a spurious
plan. Pick up a deliberate template change via
`terraform apply -replace=<vm>`. The decision is recorded in
`decisions.md` ("cloud-init is a first-boot artefact").

## Symptom

A one-line comment edit to `terraform/prd/cloud-init.yaml.tftpl`
(during the wrkdevk8s rebuild on 2026-05-07) cascaded into bpg
planning a destroy+create of every from-scratch VM. Mechanism:

1. Template change → every rendered snippet's `source_raw.data`
   differs from state.
2. bpg's `proxmox_virtual_environment_file.source_raw.data` is
   ForceNew → each `proxmox_virtual_environment_file.cloud_init[<vm>]`
   plans destroy+create.
3. `proxmox_virtual_environment_vm.this.initialization.user_data_file_id`
   references the recreated snippet → bpg cascades replacement onto
   each VM.

Caught at plan time and the comment edit was reverted, but the
underlying coupling is wrong: cloud-init runs once per VM lifetime
(first boot). Re-rendering its snippet for a running VM accomplishes
nothing operational; the rendered snippet on disk in
`/var/lib/vz/snippets/` is fossil after `cloud-init` has run. Anything
we'd want a running VM to converge to is Ansible's job to enforce.

## Goal

Two changes that together make cloud-init template edits cheap:

1. **Pin VM lifecycle to be independent of cloud-init snippet
   content.** A snippet content change recreates the file (harmless —
   the snippet on PVE is just rewritten); the VM resource stays.
2. **Strip the cloud-init template of explanatory comments** so
   casual edits to "the why" don't churn snippet state at all. Move
   the rationale next door — adjacent to the resource in
   `terraform/prd/main.tf`, or a sibling docs file.

## Decisions taken with the operator

- **Doctrine**: cloud-init is a first-boot artefact. Its scope is to
  get the VM into a state where the `bootstrap` + `baseline` Ansible
  roles can take over — ansible user with pubkey, pinned ed25519 host
  key, qemu-guest-agent, and (for bring-up-tier hosts) the initial
  netplan. After first boot, Ansible owns drift detection and
  convergence on these surfaces.
- **Fix**: `lifecycle.ignore_changes = [initialization]` on
  `proxmox_virtual_environment_vm.this` in the `managed-vm` module.
  Stops the cascade at the VM level. The snippet still recreates on
  content drift (cheap and harmless).
- **Comments out of the rendered template.** The current template
  carries five block comments explaining the why of each cloud-init
  section. Move them to either:
  - A block comment above the
    `resource "proxmox_virtual_environment_file" "cloud_init"` in
    `terraform/prd/main.tf` (adjacent to the resource), or
  - `terraform/prd/CLOUD-INIT.md` (sibling docs file).
  Operator's pick at implementation time. The rationale is preserved
  verbatim — none of it goes away, just moves out of the path that
  triggers state diffs.

## Implementation notes

### Module change (`terraform/modules/managed-vm/main.tf`)

Extend the existing `lifecycle.ignore_changes`:

```hcl
lifecycle {
  ignore_changes = [
    disk[0].file_id,
    initialization,
  ]
}
```

Broader form (`initialization` rather than
`initialization[0].user_data_file_id`) is the right call: all
sub-fields (`datastore_id`, `ip_config`, `user_data_file_id`) are
stable per VM, and any deliberate change to them is an operator
event covered by `terraform apply -replace=<vm>`.

### Cloud-init template (`terraform/prd/cloud-init.yaml.tftpl`)

Strip the five explanatory blocks (`# Only create the ansible
automation user`, `# Pin the SSH host key`, `# qemu-guest-agent must
be present on first boot`, `# Static netplan, written over cloud-
init's auto-generated DHCP file`, `# The service unit is static`).
Resulting template carries only YAML keys + template directives.

### `decisions.md`

Add a short paragraph (under "MAC addressing for managed VMs" or as
a sibling subsection):

> Cloud-init is a first-boot artefact. Its scope: ansible user,
> ansible SSH pubkey, pinned ed25519 host key, qemu-guest-agent, and
> for static-IP hosts the initial netplan render. After first boot,
> Ansible owns drift detection and convergence on these surfaces.
> The `managed-vm` module pins `lifecycle.ignore_changes =
> [initialization]` on the VM resource so a template edit
> re-renders the snippet but does not recreate the VM. To pick up a
> template change on an existing host, rebuild it (`terraform apply
> -replace=<vm>`) or apply the change via Ansible.

## Verification

Plan-only:

1. Land the module change without touching the template. `terraform
   plan` is no-op.
2. Touch the template (add a comment, change a key). Plan shows
   `proxmox_virtual_environment_file.cloud_init[*]` destroy+create
   for each from-scratch VM and **no** changes to `module.vm[*]`.
   Confirms the cascade is broken.
3. Revert the test edit. Plan returns to no-op.
4. Strip comments + relocate. Plan shows snippet destroy+create for
   each from-scratch VM (one-time, picks up the trimmed content).
   VMs untouched. Apply.

Live: after a future deliberate rebuild (`terraform apply -replace
=<vm>`), confirm the latest snippet materialized on first boot —
`cat /var/lib/vz/snippets/<vm>-user-data.yaml` on the PVE host vs.
`/var/log/cloud-init.log` and the resulting
`/etc/netplan/50-cloud-init.yaml` on the rebuilt VM.

## Caveats

- **Drift goes silent.** Once `ignore_changes = [initialization]`
  is set, a template edit that should land on existing hosts won't.
  Two paths:
  - Apply the change via Ansible (the homelab's existing doctrine —
    most fields cloud-init writes are also enforceable by
    `bootstrap` / `baseline`).
  - Rebuild the VM via `-replace`.
  Both stay loud at the operator level.
- **Static netplan is the gap.** Cloud-init's netplan render for
  static-IP hosts is the one surface no Ansible role re-asserts
  today. If a static IP in `vms.tf` changes after first boot, the
  rendered snippet updates but the running netplan stays. Either:
  - Add a small role task that materializes
    `/etc/netplan/50-cloud-init.yaml` from inventory IP config,
    idempotent (likely fits in the `baseline` role or a dedicated
    `static_netplan` role; design at implementation time).
  - Document "static-IP changes require a deliberate VM rebuild"
    and live with the limitation.
  Recommend the role task — it removes the only remaining tripwire
  and is straightforward.
- **Surgical alternative (`initialization[0].user_data_file_id`)
  exists** if the broader ignore ever surprises us. Switch is one
  line.
- **bpg version sensitivity.** ForceNew on `source_raw.data` is the
  bpg behavior we're working around. If a future bpg version makes
  that field updatable in-place, the cascade goes away on its own;
  `ignore_changes` becomes redundant but harmless.

## Commits

1. This plan, here in `slices/cloud-init-first-boot-only.md`.
2. Bundle: `managed-vm/main.tf` ignore_changes addition +
   `cloud-init.yaml.tftpl` comment strip + comment relocation (one
   of the two homes) + `decisions.md` paragraph. Single commit
   because the strip only makes sense alongside the ignore_changes
   guard, and the rationale relocation is meaningless without the
   strip.
3. Optional follow-up: Ansible role task for netplan re-render on
   static-IP hosts. Independent; can land any time after the bundle.
