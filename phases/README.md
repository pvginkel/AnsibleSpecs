# Phases

The homelab build-out, executed top-down. New phases get inserted into the pending table; closed phases move to [`completed/`](completed/) and the closed table.

## Pending

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | (microceph) | planned | (was phase 5) |
| 2 | (internal TLS / step-ca) | planned | Homelab CA + `internal_tls` Ansible role. Two issuance paths: ACME (in-cluster, cert-manager + ClusterIssuer) and JWK (VMs, role-driven). v1 consumers: PVE + microk8s API (VMs), DNS management API + `backup-server` (in-cluster). OpenBao listener certs come in the next phase via the same role. Depends on slice [internal-tls-step-ca](../slices/internal-tls-step-ca.md) |
| 3 | (openbao + secrets) | planned | 3-node Raft cluster (`srvvault1/2/3`), static seal via ansible-vault, leader-tracking keepalived VIP, daily dump via `backup-server`. OpenBao listener certs issued by the `internal_tls` role from Phase 2. Includes the secrets resolver rewrite of `iac-impl` (Python + `!bao` refs via AppRole) between standing up the cluster and the runtime-consumer sweep. Depends on slices [openbao-static-seal](../slices/openbao-static-seal.md), [iac-secrets-resolver](../slices/iac-secrets-resolver.md) |
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
| [iac-agent](completed/iac-agent.md) | phase 1 (new ordering; absorbed phase 11's CI-scheduling half) |
