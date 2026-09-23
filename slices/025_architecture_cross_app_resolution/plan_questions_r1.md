# Slice 025 — planning questions, round 1

## Q1 — Should an interface link a pod's init containers?

**The decision.** Ruling D1 says each interface is linked directly to "the workload instances
behind its Service", and adds in brackets: "(the same backing set the generator's in-memory
provider index computes today)". That index includes every container of the pods the Service
selects, init containers too (aac-tools `gen_architecture.py:614-616`, `w["all"]`). The
generators never pick an init container as a provider: every resolver drops them in memory
(`:1393`, `:1464`, `:1567`). The published set can't tell an init container from any other
container. An instance element carries release, workload, container and image, and nothing more.

This matters in one place today. Jenkins' `install-homelab-ca` init container realizes
`cap:continuous-integration`, the same as the `jenkins` container (published set, 2026-09-23).
Suppose both are linked and a consumer resolves Jenkins' host through the interface. It gets a
second, spurious edge, from the init container to the consumer. HelmCharts has never drawn that
edge.

**The options.**

- **A — Link only the containers that serve.** An interface links the containers behind its
  Service minus the init containers. The published set needs nothing else to make resolution
  exact. The viewer shows an interface's links as the containers that actually answer on it.
  The bracketed "same backing set" in D1 then reads as "without the init containers".
- **B — Link the whole backing set, as the bracket says.** Init containers are linked too, and each
  init-container instance element gets a new marker in `stats`, emitted the same way by both
  generators, so a resolver can drop it. The viewer shows init containers linked to the interfaces
  of their pod.

**Recommendation: A.** An init container has exited before the Service answers, so linking it to
the interface puts something in the model that isn't true. A needs no new field on existing
instance elements, and every field added to a kept id is one more that both generators must match
at every handover. The plan is written for A. P1 names this question in its first constraint, and
the P1 text is the only thing that changes if you choose B.
