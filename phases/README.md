# Phases

The homelab build-out, executed top-down. New phases get inserted into the pending table; closed phases move to [`completed/`](completed/) and the closed table.

## Pending

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | (microceph) | planned | (was phase 5) |
| 2 | [openbao + secrets](openbao.md) | in progress | 3-node Raft cluster (`srvvault1/2/3`), static seal via ansible-vault, leader-tracking keepalived VIP, daily dump via `backup-server`. OpenBao listener certs issued by the `internal_tls` role. Includes the secrets resolver rewrite of `iac-impl` (Python + `!bao` refs via AppRole) between standing up the cluster and the runtime-consumer sweep. Cards #1–#7 done; next is #8 (the `openbao` role itself). Depends on slices [openbao-static-seal](../slices/openbao-static-seal.md), [iac-secrets-resolver](../slices/iac-secrets-resolver.md) |
| 3 | (helm + tf harness) | planned | depends on slice [helm-tf-deploy-harness](../slices/helm-tf-deploy-harness.md) |
| 4 | (storage CSIs + tf) | planned | (was phase 8) |
| 5 | (keycloak tf) | planned | (was phase 9) |

## Completed

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
| [internal-tls-step-ca](../slices/completed/internal-tls-step-ca.md) | phase 2 (new ordering) |
| [dns-reservation-provider](../slices/completed/dns-reservation-provider/plan.md) | phase 6 "dns automation" (delivered as a slice — the `homelab_dns_reservation` TF resource is in use; `srviac` uses it for its vmbr0 lease) |
| [iac-agent (drift stages)](completed/iac-agent.md) | phase 7 "drift assertions" (delivered as the `iac-scheduled-drift` Jenkins job — `terraform plan -detailed-exitcode` plus `check-ansible-drift.sh` over `site.yml` / `site-k8s.yml` / `site-openbao.yml`, with `check-protected-vms.sh` guarding destroys) |
