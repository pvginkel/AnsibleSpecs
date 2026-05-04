# AnsibleSpecs

Specs and design docs for the homelab Ansible + Terraform work in [/work/Ansible](../Ansible).
Sister repos: [/work/Ansible](../Ansible) (code), [/work/HelmCharts](../HelmCharts) (workloads).

## What's here

- [`decisions.md`](decisions.md) — homelab doctrine. Tool split, secrets, networking, MAC scheme, OS update policy. Read this first.
- [`phases/`](phases/) — the homelab build-out, executed sequentially. See [`phases/README.md`](phases/README.md) for current order and status.
- [`slices/`](slices/) — forward-looking design work that threads between phases. See [`slices/README.md`](slices/README.md) for the slice index. Pending slices live at the top of `slices/`; closed work in `completed/`, `deferred/`, `cancelled/`.

## Conventions

- Phases and slices are plain Markdown. No frontmatter, no per-doc templates.
- Lifecycle moves are file renames via `git mv`.
- Anything transitional lives here. Perpetual operational docs (runbooks) stay in [/work/Ansible/docs/runbooks/](../Ansible/docs/runbooks/).
