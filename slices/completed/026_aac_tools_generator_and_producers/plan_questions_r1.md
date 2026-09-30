# Slice 026 — plan questions, round 1

The plan is complete apart from these two points (P1–P11 and `verification.json`). Both are
written as my recommendation, so a "yes" to each needs no replanning.

## Q1 — Architecture's changes (P7) cannot pass their gate in this environment

**At stake.** Three binding Settled items land in the Architecture repo:

- the producer manual stops telling producers to copy the script;
- the update-architecture agent learns to read the contract from `gen-architecture --help`;
- Architecture's environment config gains the aac-tools toolchain.

The run loop merges a phase only on a green gate, and Architecture's gates cannot run here.
Every component's `test` goes through `cexec modern-app`, and this environment deliberately does
not carry that tool (Ansible `ec4fbc3`: "a sidecar this environment does not carry"). I ran
`kc project test --project root` in `/work/Architecture`:
`cexec: tool "modern-app" is not available in this environment` on both statements, exit 1. So
P7, as `Target: ../Architecture`, cannot merge, and the loop-tail gate sweep would be red on
Architecture as well.

**Options.**

- **A. Before the run, add `modern-app` to this environment's `tools:` and restart it.** P7 then
  gates like any phase: its executor runs Architecture's `kc project setup` for the Poetry and
  npm environments the gates borrow. This is one config line plus a restart, at a moment you
  pick; slice 027 is running here now. It also refreshes the aac-tools sidecar, which today runs
  an image older than the published generator: for PrometheusDeploy it writes an artifact with
  0 elements and exits 0. It costs one more sidecar in this pod.
- **B. Take P7 out of this slice and hand it to the Architecture environment,** as its own change
  there, where the gates run. This slice keeps P1–P6 and P8–P11. V08 and V14 become owed after
  that work, and the Settled items above move with it. This reverses part of the binding Settled
  list.

**Recommendation: A.** The repo's own CLAUDE.md makes a coordinated change like this one
Ansible-led even where the code lands elsewhere. The Architecture edits are small (prose and one
config line), and splitting them out leaves this slice's pointer work and the manual out of step.
The restart is the only cost, and it also fixes the stale sidecar, which otherwise makes every
deploy repo's local generation gate meaningless during the run. The plan is written for A. Under
B, P7 is deleted and V08 and V14 gain an `owed_after`.

## Q2 — R2: the redis edge does not fall out of the existing wiring as the Settled item says

**At stake.** The Settled mechanism reads: "the judgment layer gains a per-container realizes, and
the generator resolves an env value sourced from a ConfigMap … so the redis edge falls out of the
existing boundBy/upstream wiring". Read against the code, neither wire draws the edge with only
those two changes:

- **boundBy** reads recipes that consumer producers publish against their own product. All 31 in
  the live dataset are on `app:` products, none on `ss:argo-cd`, and a judgment layer has no key
  to author one.
- **upstream** is declared on an image entry and applies to every non-init container of that
  image. It hard-fails on any container that does not set its var (`gen_architecture.py:1609-1614`).
  The `argocd` image also runs containers that do not read `REDIS_SERVER` (ANS-90 names only the
  server, repo-server and application-controller). An image-level `upstream: REDIS_SERVER` would
  therefore fail the whole generation.

**Options.**

- **A. The per-container scoping covers the `upstream` wire as well as `realizes`.** ArgoCDDeploy
  declares the redis wire only on the containers that read `REDIS_SERVER`. The existing upstream
  resolver then draws the edge, reading the value P2 now resolves from the ConfigMap. This is one
  new judgment-layer concept, documented in `--help`.
- **B. An image-level `upstream` skips containers that do not set the var.** No scoping of the
  wire is needed, but this softens a deliberately documented hard fail for every producer. Today
  a mistyped var fails loudly; under B it would pass silently.
- **C. Let a judgment layer author a boundBy recipe on a product it owns** (`ss:argo-cd →
  cap:cache`, `boundBy: env:REDIS_SERVER`). That is a new relation-authoring capability, and the
  recipe is read from the published dataset, so its first publish would not yet see itself.

**Recommendation: A.** It is the smallest change that keeps the ruling's shape: scoping to
containers, the existing upstream resolver, and ConfigMap resolution. It keeps the hard-fail
guarantee, and the only new idea is the scoping the ruling already introduces. P2 and P5 are
written for A.
