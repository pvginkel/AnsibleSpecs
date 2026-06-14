# Phases — retired (archive)

The phased build-out is **complete and retired**. All ongoing and future work is
tracked as slices in [`../slices/`](../slices/) — there is no pending phase
table any more. This folder is a read-only historical record of how the homelab
was built out; the completed phase docs below are still linked from slices and
remain useful context.

The two phases that were still open when phases were retired became slices:

- phase 1 "(microceph)" → [`../slices/microceph-prod.md`](../slices/microceph-prod.md)
- phase 5 "(keycloak tf)" → [`../slices/keycloak-tf.md`](../slices/keycloak-tf.md)

Phases 3 "(helm + tf harness)" and 4 "(storage CSIs + tf)" were delivered via
slices ([helm-tf-deploy-harness](../slices/completed/helm-tf-deploy-harness.md),
[tf-provider-resource-extensions](../slices/completed/tf-provider-resource-extensions.md))
and the prd cutover — both live.

## Completed (archive)

| Phase | Was |
|---|---|
| [bootstrap-baseline](completed/bootstrap-baseline.md) | phase 1 |
| [proxmox-hosts](completed/proxmox-hosts.md) | phase 2 |
| [vm-fleet](completed/vm-fleet.md) | phase 3 |
| [vm-fleet-import](completed/vm-fleet-import.md) | phase 3a |
| [microk8s](completed/microk8s.md) | phase 4 |
| [microk8s-alignment](completed/microk8s-alignment.md) | phase 4a |
| [microk8s-rebuild](completed/microk8s-rebuild.md) | phase 4b |
| [rebuild-prerequisites](completed/rebuild-prerequisites.md) | phase 4b1 |
| [microk8s-rebuild-execution](completed/microk8s-rebuild-execution.md) | phase 4c |
| [microk8s-rebuild-completion](completed/microk8s-rebuild-completion.md) | phase 4d |
| [iac-agent](completed/iac-agent.md) | phase 1 (new ordering; absorbed phase 11's CI-scheduling half) |
| [openbao + secrets](completed/openbao.md) | phase 2 (consumer migration sweep continues in [`slices/runtime-secrets-sweep`](../slices/runtime-secrets-sweep.md)) |
| [internal-tls-step-ca](../slices/completed/internal-tls-step-ca.md) | phase 2 (new ordering) |
| [dns-reservation-provider](../slices/completed/dns-reservation-provider/plan.md) | phase 6 "dns automation" (delivered as a slice — the `homelab_dns_reservation` TF resource is in use; `srviac` uses it for its vmbr0 lease) |
| [iac-agent (drift stages)](completed/iac-agent.md) | phase 7 "drift assertions" (delivered as the `iac-scheduled-drift` Jenkins job — `terraform plan -detailed-exitcode` plus `check-ansible-drift.sh` over `site.yml` / `site-k8s.yml` / `site-openbao.yml`, with `check-protected-vms.sh` guarding destroys) |
