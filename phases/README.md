# Phases

The homelab build-out, executed top-down. New phases get inserted into the pending table; closed phases move to [`completed/`](completed/) and the closed table.

## Pending

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | [iac-agent](iac-agent.md) | planned | Stand up `srviac`; route TF + Ansible through Jenkins; absorbs the CI-scheduling half of old phase 11 |
| 2 | (microceph) | planned | (was phase 5) |
| 3 | (openbao + secrets) | planned | depends on slice [openbao-static-seal](../slices/openbao-static-seal.md) |
| 4 | (helm + tf harness) | planned | depends on slice [helm-tf-deploy-harness](../slices/helm-tf-deploy-harness.md) |
| 5 | (storage CSIs + tf) | planned | (was phase 8) |
| 6 | (keycloak tf) | planned | (was phase 9) |
| 7 | (dns automation) | planned | (was phase 10) |
| 8 | (drift assertions) | planned | (was phase 11 "CI + drift"; scope reduced — iac-agent absorbs scheduling, this is what remains for sophisticated drift checks) |

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
