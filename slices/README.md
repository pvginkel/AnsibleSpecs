# Slices

Forward-looking design work that threads between phases. Pending slices are at the top of `slices/`; closed work in [`completed/`](completed/), [`deferred/`](deferred/), [`cancelled/`](cancelled/).

The dependency column lists prerequisite slices and (where relevant) the phase that consumes the slice's output.

## Pending

| Slice | Status | Depends on | Consumed by |
|---|---|---|---|
| [openbao-static-seal](openbao-static-seal.md) | pending | — | phase: openbao + secrets |
| [backup-collector](backup-collector.md) | pending | openbao-static-seal | phase: openbao + secrets |
| [pre-drain-readiness-check](pre-drain-readiness-check.md) | pending | (refines pre-drain-handoff) | microk8s-rebuild-completion (opportunistic), microceph |
| [tf-provider-resource-extensions](tf-provider-resource-extensions.md) | pending | — | phase: helm + tf harness, phase: storage CSIs |
| [helm-tf-deploy-harness](helm-tf-deploy-harness.md) | pending | tf-provider-resource-extensions | phase: helm + tf harness |
| [postgres-cluster-substrate](postgres-cluster-substrate.md) | pending | helm-tf-deploy-harness, backup-collector | phase: helm + tf harness |
| [managed-vm-mac-derivation](managed-vm-mac-derivation.md) | pending | — | (cleanup; reduces vms.tf boilerplate) |
| [cloud-init-first-boot-only](cloud-init-first-boot-only.md) | pending | — | (correctness; stops snippet edits cascading to VM rebuilds) |
| [site-yml-layout](site-yml-layout.md) | pending | iac-agent (for the friction it creates) | (TBD; restructures the playbook layout) |
| [network-devices-host-vars-sot](network-devices-host-vars-sot.md) | pending | — | (correctness; eliminates the vms.tf↔host_vars network-config dual-edit) |

## Completed

| Slice | Was | Depends on | Consumed by |
|---|---|---|---|
| [pam-credentials](completed/pam-credentials.md) | plan 01 | — | dns-reservation-provider, embed-homelab-provider, tf-provider-resource-extensions |
| [dns-reservation-provider](completed/dns-reservation-provider/plan.md) | plan 02 | pam-credentials | phase: dns automation (folder also holds the api + terraform specs) |
| [pre-drain-handoff](completed/pre-drain-handoff.md) | plan 03 | — | landed partially during phase 4c |
| [embed-homelab-provider](completed/embed-homelab-provider.md) | plan 04 | tf-provider-resource-extensions (verify direction) | Jenkins agent image |
| [data-disks](completed/data-disks.md) | merged into managed_filesystems | — | unblocks re-rebuild of srvk8s2 + remaining rebuilds |
| [internal-tls-step-ca](completed/internal-tls-step-ca.md) | spec 07 | — | phase: internal TLS; openbao reuses the `internal_tls` role |
| [ssh-host-ca](completed/ssh-host-ca.md) | — | internal-tls-step-ca | phase: openbao + secrets (the hard prerequisite — landed before OpenBao provisioning) |

## Deferred / Cancelled

| Slice | Status | Notes |
|---|---|---|
| [internal-tls-monitoring](deferred/internal-tls-monitoring.md) | deferred | §J cert-expiry alert rule + in-cluster metric. The VM-side metric already shipped; alerting is parked — observability is not a current priority. |
