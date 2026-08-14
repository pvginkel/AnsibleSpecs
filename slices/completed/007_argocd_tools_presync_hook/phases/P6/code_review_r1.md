# Code review — slice 007, phase P6, round 1

Range: `eacb2d0c93b2d7eabdb7bc98bd18ff5fd0666a8c..dee1c87` on `phase/007-P6`
Gate: green (`kc project test --project ansible` — yamllint + ansible-lint), taken as an input.

## Readiness

**Ready to merge.** The phase does exactly what its section asks and no more: one mount-relative
entry, `iac/tf-backend`, appended to `openbao_eso_kv_paths`
(`ansible/inventories/prd/group_vars/openbao.yml:107`), plus a paragraph in the block comment
stating why ESO reaches into another consumer's namespace (`:92-100`). The mechanism holds without
touching the role: `approle.yml:166-171` renders the `eso` policy from that list through
`policy.hcl.j2:28-35`, so a plain path yields `read` on `kv/data/iac/tf-backend` and `read`+`list`
on `kv/metadata/iac/tf-backend` — the same shape the block's existing single leaves
(`shared/samba/users`, `shared/jenkins/admin-password`) already produce, with `openbao_kv_mount`
defaulting to `kv` (`roles/openbao/defaults/main.yml:121`), which is what makes the mount-relative
spelling correct rather than a `kv/`-prefixed one. The leaf's spelling is grounded twice
independently of the plan — `support/iac-agent/etc/iac/secrets.example.yaml:165` resolves
`!bao kv/iac/tf-backend#age_secret_key` and `docs/runbooks/iac-agent.md:175` names the same path —
so the grant and `iac`'s own read address one leaf, which is the whole point of the shared-leaf
ruling. The "nothing else needs a policy change" claim checks out: every other row of
`attachments/credential-inventory.md:34-42` sits under `shared/prd/*` or `eso/prd/*`, including the
not-yet-existing `eso/prd/argocd-hooks/git`, and a trailing `*` in an OpenBao ACL is a prefix match
across `/` — which the existing four-level `eso/prd/storage/prd/backup-server` row already relies
on. Blast radius: the grant does widen what ESO — and so any ExternalSecret author on prd — can
materialise, but that is the plan's named, deliberated trade-off (plan.md:646-649, weighed against
the rotation split-brain of a copied leaf), not a defect. No policy-enumerating surface drifts:
`roles/openbao/README.md:116-119` names the variable only, `docs/runbooks/openbao.md` enumerates no
per-consumer paths, and `docs/architecture/ansible-architecture.yaml:394` summarises the AppRole set
without listing grants. Nothing is blocking; one comment-precision finding rides along as advisory.

## Findings

### F1 — Minor · advisory · comment-prose · anchor `none` · confidence medium

**The new comment's opening claim is contradicted by the list it annotates.**
`ansible/inventories/prd/group_vars/openbao.yml:92` states that `kv/iac/tf-backend` "is the one
grant outside ESO's own subtrees", but four entries directly beneath it — `shared/prd/*`,
`shared/samba/users`, `shared/jenkins/admin-password`, `shared/wifi-iot` (`:102-105`) — are also
outside `kv/eso`, and the paragraph immediately above (`:81-84`) says so itself: "kv/shared is read
by three consumers (iac, jenkins, eso)". The claim is true of the property that actually matters —
this is the one grant reaching into *another consumer's own namespace* — and a reader recovers that
from the next clause ("rather than the `iac/*` prefix the iac-agent holds"), so nothing downstream
is misled into a wrong action; the imprecision only sits on the least-privilege boundary this block
exists to document.
