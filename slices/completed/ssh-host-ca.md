# SSH host-key handoff via an SSH host CA

**Status: complete (2026-05-20).** The homelab step-ca is now also an
SSH host CA; every managed host serves a step-ca-signed SSH host
certificate, and host-key verification rides on a single committed
`@cert-authority` line in `ansible/files/known_hosts.d/homelab`.
Ceremony, rotation, and operational procedure are authoritative in
`docs/runbooks/step-ca-bootstrap.md` "Enabling the SSH host CA"; the
design decision lives in `decisions.md` "SSH host keys for managed
VMs".

## Goal

Terraform stops writing the repo for host identity. Adding a VM
requires no per-VM change to any committed file.

## Decisions (recap)

- **Direction**: extend the existing step-ca as an SSH host CA. One CA,
  two cert types; the same `ansible-jwk` provisioner signs both X.509
  leaves and SSH host certs.
- **First-boot bootstrap**: Ansible signs (no new Terraform credential
  needed; the JWK password stays ansible-vault-only). Terraform emits
  from-scratch VM host pubkeys as a `host_pubkeys` output; the
  bootstrap playbook materialises a transient known_hosts under `tmp/`
  for the one pre-certificate connection. The decisive constraint
  against TF embedding the cert wasn't credentials — it was that
  Terraform has no clean way to hold time-varying signed material
  without a perpetually-dirty plan.
- **Lifetime**: 47-day SSH host certs, re-signed at a 14-day threshold
  on each `iac-scheduled-drift` cycle. Same shape as the X.509 leaves.
- **Scope**: every managed host (TF-provisioned VMs, bare-metal PVE,
  the operator workstation). The four old per-config `known_hosts.d/`
  files collapsed into one `known_hosts.d/homelab`.
- **Cutover**: issue in place to every existing host first, then drop
  the per-config files in one commit.
- **No SSH host principal policy.** The `@cert-authority` line is
  loaded only by Ansible's `UserKnownHostsFile`, Ansible only connects
  to homelab hostnames, so ssh's own principal-vs-connect-target
  check is what actually scopes a forged cert.

## As-built

**`ssh_host_cert` role.** Top-level role added as the last role in
`site.yml`, `site-k8s.yml`, and `rebuild-k8s.yml` — composes via play
ordering (after baseline on every host, after microk8s on k8s nodes so
the `ca.home` /etc/hosts pin is in place). Mirrors `internal_tls`'s
split issuance: the JWK SSH-host token is minted on the iac controller
(where the fleet provisioner password lives); `step ssh certificate
--host --sign` runs on the target against the existing
`/etc/ssh/ssh_host_ed25519_key.pub`. Installs the cert next to the key
(`<key>-cert.pub`), drops `/etc/ssh/sshd_config.d/10-homelab-host-cert.conf`
with `HostKey` + `HostCertificate`, and reloads sshd (non-disruptive —
the running Ansible connection survives, safe under k8s `serial: 1`).

**Terraform.** `terraform/{prd,scratch}` no longer write the repo for
host identity. `local_file.known_hosts_*` is gone; the per-VM host
pubkeys are surfaced as the `host_pubkeys` output. The `tls` provider
stays (per-VM keypair, persisted in tfstate, embedded via cloud-init).
The `hashicorp/local` provider is gone.

**Bootstrap handoff.** `rebuild-k8s.yml` gains a localhost Play 0 that
reads `terraform output -json host_pubkeys`, writes a transient
known_hosts under repo-root `tmp/`, and the bootstrap play uses it via
`ansible_ssh_args`. Zero TOFU: the pinned key is the exact one
Terraform generated and embedded into cloud-init. Phase 2's OpenBao
provisioning play will reuse the pattern.

**`ansible.cfg`.** `UserKnownHostsFile` collapsed to a single file
(`files/known_hosts.d/homelab`) carrying one `@cert-authority *` line
with the SSH host CA public key. `HostKeyAlgorithms` accepts
`ssh-ed25519-cert-v01@openssh.com` (steady state) and `ssh-ed25519`
(the pre-cert bootstrap window).

**Ceremony additions.** A new section in
`docs/runbooks/step-ca-bootstrap.md` covers generating the SSH host CA
keypair, handing it to the chart via the upstream
`existingSecrets.sshHostCa` mechanism, and editing `ca.json` to add
the top-level `ssh` block plus SSH host claims on the `ansible-jwk`
provisioner. The provisioner's `enableSSHCA: true` and empty
`options.ssh: {}` were already in place from the existing config, so
the JWK side needed no new password and no new policy.

## Caveats

- **Pod restart is required when `ca.json` changes.** step-ca reads
  `ca.json` only at startup, so editing the Secret without a
  `kubectl rollout restart` leaves SSH flows disabled with a 501
  "ssh certificate flows are not enabled". Documented in the runbook.
- **JWK provisioner password compromise.** A leak now lets an attacker
  forge any X.509 cert the X.509 SAN policy allows AND any SSH host
  cert. Mitigations: 47-day leaves bound the blast radius; rotation
  follows the existing JWK-provisioner-password procedure in the
  runbook.
- **Cold-boot envelope ~33 days.** A step-ca outage shorter than 47 −
  14 days is invisible (certs in the field keep working). Beyond that,
  renewals fail and certs eventually expire; verification breaks until
  step-ca returns or a cert is replaced manually.
- **SSH user CA is still deferred.** This slice covers host certs
  only. Replacing `~/.ssh/authorized_keys` with user certificates is a
  separate, lower-priority sweep.

## Related

- [`completed/internal-tls-step-ca.md`](internal-tls-step-ca.md) — the
  X.509 side of the same CA.
- [`../network-devices-host-vars-sot.md`](../network-devices-host-vars-sot.md)
  — closed the other "Terraform on srviac cannot write the repo" bug,
  on the network-config side.
