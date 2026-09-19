# ansible-jwk's name allow-list is inert — decisions.md documents it as a control

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Major

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Raised separately from KubeCoder card #666 (SSH transport), whose CA research found it. Estate-level, not KubeCoder's.

step-ca 0.30.2's per-provisioner name policy does not work in a file-based ca.json: AllowedNames/DeniedNames/AllowWildcardNames carry `json:"-"` (authority/provisioner/options.go:89-97), filled only via the remote-management API this estate does not use. `step ca policy provisioner --help`: "currently only supported in Certificate Manager". ansible-jwk's committed options.x509.allow.dns list is dead configuration.

Confirmed three ways: OpenBao's listener cert, issued through ansible-jwk, holds DNS:secrets.home and DNS:srvvault1.home, neither on the list; ca.home/provisioners advertises ansible-jwk as options {"x509":{},"ssh":{}}, so only the policy half is dropped — claims survive; and on a throwaway 0.30.2 CA, allow.dns plus deny.dns ["*"] still issued forbidden.example.com.

What does work: per-provisioner options.x509/ssh.template ({{ fail }} refused everything), authority.policy (enforced, but polices every provisioner at once), enableAdmin (migrates provisioners into the CA's badger DB).

KubeCoder slice 165 adds a kubecoder-jwk provisioner configured the same way — its policy block is inert too, by operator ruling.

Why it matters: AnsibleSpecs/decisions.md §Internal TLS presents the allow-list as a control, and it is not one. Fix the mechanism or correct the doctrine.

Full analysis: KubeCoderSpecs/slices/backlog/170_ssh_transport/ssh-host-certs-from-step-ca.md §4.2, §8 item 1; slice 165 close-out B1.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (5)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:48 AM
Filed at triage 2026-09-14: the documentation half goes to the straightforward-changes handover — AnsibleSpecs/handovers/triage_2026-09-14_straightforward_changes.md, item 1 — worked in one conversation with the operator and tracked on Operator Actions #994. Implementing the controls is #993 (Later).

### Jeeves (@jeevesginbov) - 9/14/2026, 7:17:55 AM
Triaged 2026-09-14: Major — "AnsibleSpecs/decisions.md §Internal TLS presents the allow-list as a control, and it is not one."

Operator ruling, verbatim: "I don't feel like fixing this. It's a known gap. I have bigger ones. I would like the following. Document that we should have these controls, but that they're not in place. Make the documentation honest. Then file a card in the Later list (a clean card) to implement the controls."

Split: implementing the controls is #993 (Later). This card keeps the documentation half — the docs say the controls are wanted and are not in place.

### Jeeves (@jeevesginbov) - 8/22/2026, 6:31:42 PM
The last loose end from the comment above is closed too — `step-ca-bootstrap.md` commit `fdf4d07`. Nothing in that runbook is left for this card.

It was worse than the one line I flagged. **Five `kubectl` invocations addressed namespace `step-ca`, which does not exist**, and the intermediate-rotation restart addressed `deployment step-ca`, which is a StatefulSet:

- `:249` and `:539` — both `step-ca-intermediate` Secret recipes (bootstrap and rotation).
- `:461` — the `kubectl exec ... cat` fallback in the Windows trust-store import.
- `:545-546` — the intermediate-rotation restart, wrong on both counts.

The Secret recipes fail loudly on a missing namespace, so they cost a minute. The restart is the dangerous one: it would report success against nothing, leaving the operator believing a freshly rotated intermediate is live while the CA keeps serving the old one — the same class of silent no-op as the provisioner-edit paragraph, in the same document.

Verified before writing: only `step-ca-prd` exists (prd cluster; the dev cluster has no step-ca namespace live), it holds `statefulset/step-ca`, and `configs/{dev,prd}/step-ca/prd/manifests.yaml` both declare that same namespace — a single stage, `prd`, on either cluster. Stated once in the runbook so the next `kubectl` added to it inherits the right address. `kc project test` green across all four components.

### Jeeves (@jeevesginbov) - 8/22/2026, 6:24:14 PM
**Follow-up to the comment above: the two riding-along items (3) are now fixed — don't redo them.** They stay documented here for context only.

- **S4** — `Ansible/docs/runbooks/step-ca-bootstrap.md` (commit `ad504d9`). The provisioner-claims procedure now states that the deploy is not what makes the edit live, explains why (upstream chart, no `checksum/config` on the pod template, `ca.json` read at process start only), carries the `rollout restart` / `rollout status` pair, and names the workload the release actually runs — `statefulset/step-ca` in `step-ca-prd`, confirmed against the cluster as the one stage deployed (there is no `step-ca-dev` namespace and no `configs/prd/step-ca/dev/`). Verification line added: `curl -sk https://ca.home/provisioners`.
- **S7** — `AnsibleSpecs/decisions.md` (commit `b1bf0d0`). The leaf is now written `kv/eso/prd/kubecoder/<stage>/step-ca-provisioner-password`.

**One thing left in that area, deliberately not touched:** the same runbook's intermediate-rotation section (`:526-531`) tells you to `kubectl -n step-ca rollout restart deployment step-ca`. By the same evidence that fixed S4, that is wrong for this release on both counts — the workload is a StatefulSet and the namespace is `step-ca-prd`. It was outside what the close-out entry asked for, so it is still there.

**Items 1 and 2 of the previous comment are untouched and are this card's work** — `decisions.md:141`'s mechanism sentence, and `kubecoder-jwk`'s under-declared `options.x509` block.

### Jeeves (@jeevesginbov) - 8/22/2026, 6:07:28 PM
**Slice 165's close-out is closed; everything from it that touches this card lands here.** Source: `KubeCoderSpecs/slices/completed/165_cross_repo_sidecar_and_ssh_prereqs/close-out.md` (B1, S2, S3, S4, S7).

**1. The decisions.md sentence names the wrong mechanism, not just an over-claimed one** (close-out S2). `AnsibleSpecs/decisions.md:141` reads: *"Scoping comes from the provisioner's `allowedSANs` regex (`*.home` plus the kube-apiserver internal names) rather than per-consumer credentials."* Independent of this card's inertness finding, that is not what is deployed. Decoding the `ca.json` in `HelmCharts/configs/prd/step-ca/prd/manifests.yaml:19`, `ansible-jwk` has no `allowedSANs` and no regex at all — it carries `options.x509.allow.dns` with 21 **exact** names (`pve`, `pve.home`, `pve1`, `pve2` and their `.home` forms, `srvceph1..3`, the `kubernetes*` and `kubernetes-api*` names) plus `allow.ip` with three addresses. That is the step-ca policy engine, not a SAN regex, and `*.home` is not among the names — so a `.home` name outside the list would be *refused* if policy worked at all, the opposite of what the decision implies. The sentence needs rewriting whichever way this card lands: correcting the doctrine means describing the policy block that exists, and fixing the mechanism means the regex claim is still wrong.

**2. `kubecoder-jwk`'s block is under-declared as well as inert — do not enable enforcement over it unchanged** (close-out S3). The committed block declares `options.x509.deny.dns: ["*"]` and no `allow` of any kind. The settled intent (slice 165 plan.md:410-412, acceptance criterion V14) was X.509 permitting **no name at all**. DNS is one of the five name types the policy form covers, so the declaration says nothing about IP, email, URI or common-name SANs. Harmless today — the block never loads, and the controller never asks this provisioner for an X.509 leaf. It stops being harmless the moment this card is closed by making per-provisioner policy actually enforce (templates or `enableAdmin`): the block would then be applied as written, which is not what V14 settled. Rewrite it in the same change.

**3. Two small corrections in the same area, riding along because they have no card of their own.** Neither is this card's defect; both are estate step-ca documentation and would otherwise be lost.

- (close-out S4) `Ansible/docs/runbooks/step-ca-bootstrap.md:384-385` closes its "edit the provisioner claims" procedure with *"Validate the JSON (`jq . <file>`), re-encode to base64, redeploy `step-ca`"*. **A redeploy of that release applies the Secret and rolls nothing**, and step-ca 0.30.2 reads `ca.json` only at process start — reproduced during slice 165 on a throwaway 0.30.2 CA, where the provisioner appeared only after `SIGHUP`, a signal a Secret update never sends. Slice 165 walked into exactly this. The same runbook already carries the missing sentence for other Secret-mounted CA material (`:526-531`, `rollout restart` after writing the intermediate). Two corrections belong in that paragraph: the restart, and the workload — prd runs `statefulset/step-ca` in namespace `step-ca-prd`, not the `deployment step-ca` in `step-ca` that `:526-531` names.
- (close-out S7) `AnsibleSpecs/decisions.md:142` writes the new OpenBao leaf as `eso/prd/kubecoder/<stage>/step-ca-provisioner-password`, without the `kv/` mount prefix that `:78` and `:90` both carry. Right for the surface it came from (an ESO `remoteRef` `path:`, where the `openbao-prd` ClusterSecretStore pins the mount), wrong for an operator reading a decision record — `bao kv put eso/prd/…` hits a mount that does not exist. Three characters.

**4. State of `AnsibleSpecs/decisions.md` after 165's close-out** (so a fixer knows what has already moved, commit `7bfd100`): a fifth secret-rotation pattern was added for the `kubecoder-jwk` password — it decrypts the provisioner's `encryptedKey` inside step-ca's own `ca.json`, so a KV-only `bao kv put` desynchronises the two sides, and the KubeCoder controller takes the value as a start-time env var with nothing hashing the Secret into the pod template. The `"sixth out-of-repo copy"` ordinal was dropped from the root-rotation bullet. §Internal TLS `:141` — item 1 above — was **not** touched; it is left for whoever fixes this card.

**5. `kubecoder-jwk` is now live, with the inert block as committed.** Verified 2026-08-22 after the step-ca roll: `https://ca.home/provisioners` lists it alongside `admin`, `acme` and `ansible-jwk`, `kid sihtizNMEttxQBnxP-zj3x5dTaptmdyR8VPmqq_wo80`, `enableSSHCA: true`, `defaultHostSSHCertDuration 168h`, `maxHostSSHCertDuration 336h`. A host certificate was issued through it end to end. So this card's blast radius now covers two provisioners rather than one.

## 📊 Statistics

- **Comments**: 5

## 🔗 Links
- **Card URL**: https://trello.com/c/WAB6RIwN/667-ansible-jwks-name-allow-list-is-inert-decisionsmd-documents-it-as-a-control
- **Short URL**: https://trello.com/c/WAB6RIwN

---
*Last Activity: 9/14/2026, 7:40:00 AM*
*Card ID: 6a884c6df22b9014128f910a*
