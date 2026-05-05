# Slices

Forward-looking design work that threads between phases. Pending slices are at the top of `slices/`; closed work in [`completed/`](completed/), [`deferred/`](deferred/), [`cancelled/`](cancelled/).

The dependency column lists prerequisite slices and (where relevant) the phase that consumes the slice's output.

## Pending

| Slice | Status | Depends on | Consumed by |
|---|---|---|---|
| [data-disks](data-disks.md) | pending | — | microk8s-rebuild-completion (blocker for re-rebuilding srvk8s2 + remaining rebuilds) |
| [openbao-static-seal](openbao-static-seal.md) | pending | — | phase: openbao + secrets |
| [backup-collector](backup-collector.md) | pending | openbao-static-seal | phase: openbao + secrets |
| [pre-drain-readiness-check](pre-drain-readiness-check.md) | pending | (refines pre-drain-handoff) | microk8s-rebuild-completion (opportunistic), microceph |
| [tf-provider-resource-extensions](tf-provider-resource-extensions.md) | pending | — | phase: helm + tf harness, phase: storage CSIs |
| [helm-tf-deploy-harness](helm-tf-deploy-harness.md) | pending | tf-provider-resource-extensions | phase: helm + tf harness |

## Completed

| Slice | Was | Depends on | Consumed by |
|---|---|---|---|
| [pam-credentials](completed/pam-credentials.md) | plan 01 | — | dns-reservation-provider, embed-homelab-provider, tf-provider-resource-extensions |
| [dns-reservation-provider](completed/dns-reservation-provider/plan.md) | plan 02 | pam-credentials | phase: dns automation (folder also holds the api + terraform specs) |
| [pre-drain-handoff](completed/pre-drain-handoff.md) | plan 03 | — | landed partially during phase 4c |
| [embed-homelab-provider](completed/embed-homelab-provider.md) | plan 04 | tf-provider-resource-extensions (verify direction) | Jenkins agent image |

## Deferred / Cancelled

(empty)
