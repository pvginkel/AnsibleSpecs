# terraform/scratch lock file is missing hashicorp/local

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `yellow` Chore

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Found incidentally while verifying #446. Not fixed there — it is a CI-consumed file and unrelated to that card, so the change was reverted rather than folded in.

## What is wrong

`terraform/scratch/.terraform.lock.hcl` has no entry for `registry.terraform.io/hashicorp/local`, even though the scratch config uses the provider — `local_file.known_hosts_entries` is in the live state.

Running `terraform init` in `terraform/scratch` therefore always produces a dirty tree: it adds a `hashicorp/local` v2.9.0 block with the full set of `zh:` multi-platform hashes. Anyone who inits scratch gets the same diff.

## Why it matters

Low severity but real: the lock file is not doing its job for that provider, so the version is unpinned in practice and a fresh init can pick up whatever `local` resolves to at the time. It also means every init leaves a spurious modification for someone to notice and discard.

## The fix

Run `terraform init` in `terraform/scratch` and commit the resulting lock addition.

Worth checking at the same time: why CI never committed it. If the `IaC/*` pipeline inits scratch on every run, this entry should have been added long ago — so either the pipeline does not init scratch, or it runs somewhere the result is discarded. Whichever it is, the same gap could exist for other providers.

Separately, `init` warns that checksums for `pvginkel/homelab` are calculated locally and the lock only carries `linux_amd64` for it, because it comes from a local provider mirror rather than a registry. That is expected for a private provider and not part of this fix, but noting it so the warning is not mistaken for the same problem.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/16/2026, 5:58:58 PM
Done, but not the fix this card proposed — recording what it actually was.

The lock entry was not missing by accident. ee76ea4 (2026-07-27) removed it deliberately, on the premise that `terraform init` prunes it every time. That premise was wrong: init *adds* it back. Either way the tree went dirty.

Root cause was state, not the lock. `local_file.known_hosts_entries` was an orphan in scratch state — its config went away in 3584521 (ssh-host-ca: stop Terraform writing known_hosts.d) but nobody removed it from state. `terraform providers` listed hashicorp/local under "required by state" only, so init installed it and wrote the lock entry.

Fix was `terraform state rm local_file.known_hosts_entries` in terraform/scratch. Config and state now agree, the already-committed lock file is correct as-is, and init leaves a clean tree. No repo change.

Answering this card's own two questions: CI never committed the entry because it belongs to a state orphan, and no, the same gap does not exist elsewhere — prd's state is clean and there are only two roots.

Side note: with the orphan in state, every scratch plan was carrying a stray destroy line for that resource. That is gone too.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/EZxe8Oct/458-terraform-scratch-lock-file-is-missing-hashicorp-local
- **Short URL**: https://trello.com/c/EZxe8Oct

---
*Last Activity: 8/16/2026, 5:59:00 PM*
*Card ID: 6a74d9ba2a74d052dd8ed70e*
