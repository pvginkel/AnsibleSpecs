# SSH host-key handoff via a certificate authority

**Status**: pending. **Hard deadline: before the OpenBao VMs
(`srvvault1/2/3`) are provisioned.**

## Symptom

`terraform/prd/main.tf` generates an ed25519 host keypair per
from-scratch VM (in tfstate), embeds the private half in cloud-init,
and — via `local_file.known_hosts_prd` — **writes**
`ansible/files/known_hosts.d/prd` into the repo working tree. Ansible
reads that file for host-key verification.

Terraform now runs on the `srviac` IaC agent, which does not commit or
push. A `terraform apply` on `srviac` that adds a VM regenerates
`known_hosts.d/prd` only in the agent's ephemeral workspace — the change
is never committed. Any Ansible run not immediately preceded by
`terraform apply` in the same workspace (the daily `iac-scheduled-drift`
job, the weekly `iac-scheduled-update` job, the operator's workstation)
then uses a stale file.

This breaks the moment the first VM is provisioned via `srviac` — the
OpenBao cluster. Hence the deadline.

## Goal

Terraform stops writing the repo for host identity. Adding a VM requires
no per-VM change to any committed file.

## Direction (decided with the operator)

An **SSH certificate authority**. The operator chose this over the two
alternatives (commit the keys with TF reading them; or materialise
`known_hosts.d/` at run time from `terraform output`) because it deletes
the whole category of "Terraform writes per-VM data into the repo"
rather than this one instance.

- Extend the existing homelab **step-ca** (deployed; `ca.home` /
  `10.2.1.15`) to also act as an SSH **host** CA.
- Each from-scratch VM gets a host certificate signed by that CA at
  provision time.
- `known_hosts.d/` collapses to a single committed
  `@cert-authority *.home <CA SSH pubkey>` line — written once, never
  touched as VMs come and go.

`decisions.md` "SSH host keys for managed VMs" already names this as the
intended evolution; it assumed OpenBao would be the signer "once OpenBao
is up". Using step-ca instead makes it available *before* OpenBao,
resolving the chicken-and-egg (OpenBao's own VMs need host certs).

## Open questions for the design pass

- **Cert delivery at first boot.** Most likely: Terraform signs the host
  cert and embeds it in the cloud-init snippet next to the existing
  keypair — mirrors how the private key is embedded today and needs no
  boot-time CA reachability. Alternative: the VM requests a cert from
  step-ca on first boot (needs a provisioner token). Decide.
- **step-ca SSH-CA enablement** — the `ssh` config block + an SSH host
  provisioner. Whether this extends the existing `internal_tls` role or
  is a new step.
- **Host-cert lifetime / renewal** for long-lived VMs.
- **Cutover for already-provisioned VMs** — re-sign them, or let the
  current per-host `known_hosts.d/` lines coexist with the
  `@cert-authority` line during the transition.

## Touchpoints

- `terraform/prd/main.tf` — delete `local_file.known_hosts_prd`; add
  cert signing; embed the cert via `cloud-init.yaml.tftpl`.
- `ansible/files/known_hosts.d/` — replace the per-config files with the
  single `@cert-authority` line.
- `ansible/ansible.cfg` — `ssh_args` `UserKnownHostsFile`; fix the now
  stale "each terraform config writes its own" comment.
- `decisions.md` "SSH host keys for managed VMs" — rewrite to match.

## Related

Shares its root cause (Terraform on `srviac` cannot write the repo) with
[network-devices-host-vars-sot](network-devices-host-vars-sot.md), which
handles the network-config side.
